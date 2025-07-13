"""
LangGraph workflow for newsletter generation.

This module defines the complete workflow for generating AI news newsletters
using LangGraph state management and node-based processing.
"""

import asyncio
import time
from datetime import datetime

from langgraph.graph import END, StateGraph

from src.config.settings import get_settings
from src.deduplication.duplicate_checker import BasicDuplicateChecker, consolidate_similar_articles
from src.llm.llm_router import LLMRouter
from src.models.schemas import (
    ProcessedArticle,
    ProcessingLog,
    SummarizedArticle,
)
from src.utils.ai_semantic_filter import AISemanticFilter
from src.utils.content_fetcher import fetch_content_from_sources
from src.utils.content_validator import validate_article_content
from src.utils.context_analyzer import ContextAnalyzer
from src.utils.embedding_manager import EmbeddingManager
from src.utils.image_processor import ImageProcessor
from src.utils.logger import setup_logging
from src.utils.supabase_client import save_newsletter_to_supabase
from src.utils.topic_clustering import (
    cluster_articles_with_multi_source_priority,
)

logger = setup_logging()


class NewsletterWorkflow:
    """LangGraph workflow for newsletter generation."""

    def __init__(self):
        """Initialize workflow components."""
        self.llm_router = LLMRouter()
        self.duplicate_checker = BasicDuplicateChecker()
        self.embedding_manager = None  # Initialized lazily
        self.context_analyzer = None   # Initialized lazily
        self.semantic_filter = None    # Initialized lazily
        self.image_processor = None    # Initialized lazily
        self.quaily_client = None

    async def initialize_with_past_articles(self, days_back: int = 7):
        """
        Initialize workflow with past articles from Supabase.

        Args:
            days_back: Number of days of past articles to load
        """
        try:
            # Initialize embedding manager if not already done
            if self.embedding_manager is None:
                self.embedding_manager = EmbeddingManager()

            # Sync with Supabase to load past articles
            logger.info(f"Syncing past {days_back} days of articles from Supabase")
            synced_count = await self.embedding_manager.sync_with_supabase(days_back)

            # Also load past articles into duplicate checker's cache
            from src.utils.supabase_client import get_recent_contextual_articles
            past_articles = await get_recent_contextual_articles(
                days_back=days_back,
                limit=1000
            )

            # Convert to format expected by duplicate checker
            # This is a simplified conversion - in production, you'd reconstruct full objects
            if past_articles:
                logger.info(f"Loading {len(past_articles)} past articles into duplicate checker cache")
                # Note: BasicDuplicateChecker expects SummarizedArticle objects
                # For now, we'll just log this - full implementation would reconstruct objects

            logger.info(
                f"Workflow initialized with {synced_count} articles in embedding index"
            )

        except Exception as e:
            logger.error(f"Failed to initialize with past articles: {e}")
            # Continue without past articles rather than failing completely

    async def fetch_sources_node(self, state: dict) -> dict:
        """Fetch articles from RSS and YouTube sources."""

        logger.info("Starting fetch sources node")
        start_time = time.time()

        try:
            config = state["config"]

            # Calculate dynamic hours_lookback based on target_date
            hours_lookback = 24  # Default
            if getattr(config, 'target_date', None):
                today = datetime.now().date()
                delta_days = (today - config.target_date).days
                if delta_days > 0:
                    # For past dates, expand lookback to ensure we capture content
                    hours_lookback = max(24, (delta_days + 1) * 24)
                    logger.info(f"Target date is {delta_days} days ago, using hours_lookback={hours_lookback}")

            # Fetch from all sources
            raw_articles = await fetch_content_from_sources(
                sources=config.sources,
                max_items_per_source=max(3, config.max_items // len(config.sources)),
                hours_lookback=hours_lookback
            )

            # If target_date is specified, keep only articles published on that date (local timezone assumed)
            if getattr(config, 'target_date', None):
                target = config.target_date
                raw_articles = [
                    art for art in raw_articles
                    if getattr(art, 'published_date', None) and art.published_date.date() == target
                ]

            # Sort articles by source priority (higher priority sources first)
            raw_articles = self._sort_articles_by_priority(raw_articles)

            # Limit total articles
            raw_articles = raw_articles[:config.max_items]

            processing_time = time.time() - start_time

            # Log processing
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="fetch_sources",
                event_type="info",
                message=f"Fetched {len(raw_articles)} articles from {len(config.sources)} sources",
                data={
                    "articles_count": len(raw_articles),
                    "sources_count": len(config.sources)
                },
                duration_seconds=processing_time
            )

            return {
                **state,
                "raw_articles": raw_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "sources_fetched"
            }

        except Exception as e:
            logger.error("Fetch sources node failed", error=str(e))

            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="fetch_sources",
                event_type="error",
                message=f"Failed to fetch sources: {str(e)}",
                duration_seconds=time.time() - start_time
            )

            return {
                **state,
                "raw_articles": [],
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "fetch_failed"
            }

    async def filter_ai_content_node(self, state: dict) -> dict:
        """Filter articles for AI relevance."""

        logger.info("Starting AI content filter node")
        start_time = time.time()

        try:
            config = state["config"]
            raw_articles = state["raw_articles"]

            if not raw_articles:
                logger.warning("No raw articles to filter")
                return {
                    **state,
                    "filtered_articles": [],
                    "status": "no_articles_to_filter"
                }

            # Filter articles with enhanced semantic analysis
            try:
                # Initialize semantic filter if not already done
                if self.semantic_filter is None:
                    # Use configured thresholds from settings
                    base_threshold = config.ai_relevance_threshold  # Use configured threshold directly
                    high_threshold = base_threshold + 0.3  # High threshold = base + 0.3
                    self.semantic_filter = AISemanticFilter(
                        base_threshold=base_threshold,
                        high_threshold=high_threshold
                    )
                    await self.semantic_filter.initialize()

                # PRD準拠: 高品質記事確保のため適切な閾値使用
                base_threshold = config.ai_relevance_threshold  # Use configured threshold directly
                min_threshold = max(0.05, config.ai_relevance_threshold - 0.05)  # 大幅に緩和: 15% → 5%

                filtered_articles = await self.semantic_filter.filter_articles_with_semantic(
                    articles=raw_articles,
                    base_threshold=base_threshold,
                    min_threshold=min_threshold
                )

                logger.info(f"Enhanced semantic filtering: {len(raw_articles)} → {len(filtered_articles)} articles passed")

            except Exception as e:
                logger.warning(f"Semantic filtering failed, falling back to keyword-only: {e}")
                # Fallback to original filter
                from src.utils.ai_filter import filter_ai_content
                filtered_articles = filter_ai_content(
                    articles=raw_articles,
                    relevance_threshold=config.ai_relevance_threshold,
                    min_articles_target=getattr(config, 'min_articles_target', 5),
                    dynamic_threshold=getattr(config, 'dynamic_threshold', True)
                )

            processing_time = time.time() - start_time

            # Log processing
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="filter_ai_content",
                event_type="info",
                message=f"Filtered {len(filtered_articles)} relevant articles from {len(raw_articles)}",
                data={
                    "input_articles": len(raw_articles),
                    "output_articles": len(filtered_articles),
                    "filter_rate": len(filtered_articles) / len(raw_articles) if raw_articles else 0
                },
                duration_seconds=processing_time
            )

            return {
                **state,
                "filtered_articles": filtered_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "content_filtered"
            }

        except Exception as e:
            logger.error("Filter AI content node failed", error=str(e))

            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="filter_ai_content",
                event_type="error",
                message=f"Failed to filter AI content: {str(e)}",
                duration_seconds=time.time() - start_time
            )

            return {
                **state,
                "filtered_articles": [],
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "filter_failed"
            }

    async def generate_summaries_node(self, state: dict) -> dict:
        """Generate LLM summaries for filtered articles."""

        logger.info("Starting generate summaries node")
        start_time = time.time()

        try:
            config = state["config"]
            filtered_articles = state["filtered_articles"]

            if not filtered_articles:
                logger.warning("No filtered articles to summarize")
                return {
                    **state,
                    "summarized_articles": [],
                    "status": "no_articles_to_summarize"
                }

            # Process articles concurrently with semaphore
            semaphore = asyncio.Semaphore(5)  # Increased from 3 to 5 for better performance
            summarized_articles = []

            async def summarize_single_article(filtered_article):
                async with semaphore:
                    try:
                        article_start_time = time.time()

                        raw_article = filtered_article.raw_article

                        # Generate summary using LLM router
                        summary = await self.llm_router.generate_summary(
                            article_title=raw_article.title,
                            article_content=raw_article.content,
                            article_url=str(raw_article.url),
                            source_name=raw_article.source_id
                        )

                        processing_time = time.time() - article_start_time

                        # Create summarized article
                        summarized_article = SummarizedArticle(
                            filtered_article=filtered_article,
                            summary=summary,
                            processing_time_seconds=processing_time,
                            retry_count=0,  # Router handles retries internally
                            fallback_used=summary.model_used == "fallback"
                        )

                        # Perform immediate quality validation on generated summary
                        try:
                            from src.utils.content_validator import validate_article_content
                            validation_result = validate_article_content(summary.summary_points)

                            # Check for critical quality issues in summary
                            has_critical_errors = any(
                                (hasattr(violation, 'severity') and
                                 hasattr(violation.severity, 'value') and
                                 violation.severity.value == "ERROR") or
                                (hasattr(violation, 'severity') and
                                 isinstance(violation.severity, str) and
                                 violation.severity == "ERROR")
                                for violation in validation_result.violations
                            )

                            # If summary quality is very poor, attempt one retry
                            if has_critical_errors or validation_result.quality_score < 0.4:
                                logger.warning(
                                    "Poor quality summary detected, attempting retry",
                                    article_id=filtered_article.raw_article.id,
                                    quality_score=validation_result.quality_score,
                                    violations=[getattr(v, 'rule_id', str(v)) for v in validation_result.violations]
                                )

                                # Retry summary generation once
                                retry_summary = await self.llm_router.generate_summary(
                                    article_title=raw_article.title,
                                    article_content=raw_article.content,
                                    article_url=str(raw_article.url),
                                    source_name=raw_article.source_id
                                )

                                # Validate retry result
                                retry_validation = validate_article_content(retry_summary.summary_points)

                                # Use retry if it's better
                                if retry_validation.quality_score > validation_result.quality_score:
                                    logger.info(
                                        "Retry summary quality improved",
                                        article_id=filtered_article.raw_article.id,
                                        original_score=validation_result.quality_score,
                                        retry_score=retry_validation.quality_score
                                    )
                                    summarized_article.summary = retry_summary
                                    summarized_article.retry_count = 1

                        except Exception as validation_error:
                            logger.warning(
                                "Summary validation failed during generation",
                                article_id=filtered_article.raw_article.id,
                                error=str(validation_error)
                            )

                        return summarized_article

                    except Exception as e:
                        logger.error(
                            "Failed to summarize article",
                            article_id=filtered_article.raw_article.id,
                            error=str(e)
                        )
                        return None

            # Process articles concurrently
            tasks = [
                summarize_single_article(article)
                for article in filtered_articles
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect successful results
            for result in results:
                if isinstance(result, SummarizedArticle):
                    summarized_articles.append(result)
                elif isinstance(result, Exception):
                    logger.error("Summarization task failed", error=str(result))

            processing_time = time.time() - start_time

            # Log processing
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="generate_summaries",
                event_type="info",
                message=f"Generated {len(summarized_articles)} summaries from {len(filtered_articles)} articles",
                data={
                    "input_articles": len(filtered_articles),
                    "output_articles": len(summarized_articles),
                    "success_rate": len(summarized_articles) / len(filtered_articles) if filtered_articles else 0,
                    "llm_calls": len(filtered_articles)
                },
                duration_seconds=processing_time
            )

            return {
                **state,
                "summarized_articles": summarized_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "summaries_generated"
            }

        except Exception as e:
            logger.error("Generate summaries node failed", error=str(e))

            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="generate_summaries",
                event_type="error",
                message=f"Failed to generate summaries: {str(e)}",
                duration_seconds=time.time() - start_time
            )

            return {
                **state,
                "summarized_articles": [],
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "summarization_failed"
            }

    async def check_duplicates_node(self, state: dict) -> dict:
        """Intelligent duplicate consolidation and context analysis (Enhanced Phase 2)."""

        logger.info("Starting intelligent duplicate consolidation and context analysis")
        start_time = time.time()

        try:
            config = state["config"]
            summarized_articles = state["summarized_articles"]

            if not summarized_articles:
                logger.warning("No summarized articles to consolidate")
                return {
                    **state,
                    "deduplicated_articles": [],
                    "status": "no_articles_to_consolidate"
                }

            # Phase 1: Intelligent duplicate consolidation (using refactored method)
            consolidated_articles = await self._consolidate_duplicates(summarized_articles)

            # Phase 2: Context analysis and article processing (using refactored method)
            deduplicated_articles, duplicate_count, update_count = await self._process_articles_with_context(
                consolidated_articles
            )

            # Phase 3: Log results (using refactored method)
            processing_time = time.time() - start_time
            log_entry = self._log_duplicate_processing_results(
                config, summarized_articles, deduplicated_articles,
                duplicate_count, update_count, processing_time
            )

            return {
                **state,
                "deduplicated_articles": deduplicated_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "duplicates_and_context_checked"
            }

        except Exception as e:
            logger.error("Check duplicates and context node failed", error=str(e))

            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="check_duplicates_context",
                event_type="error",
                message=f"Failed to check duplicates and context: {str(e)}",
                duration_seconds=time.time() - start_time
            )

            return {
                **state,
                "deduplicated_articles": [],
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "deduplication_context_failed"
            }

    async def process_single_article_parallel(self, article: SummarizedArticle, past_articles: list[SummarizedArticle]) -> dict:
        """
        Process a single article with parallel LLM operations.

        Args:
            article: Article to process
            past_articles: Previously processed articles for duplicate checking

        Returns:
            Dict with processing results and article data
        """
        try:
            # Sequential duplicate check (fast, no LLM)
            duplicate_result = self.duplicate_checker.check_duplicate(
                current_article=article,
                past_articles=past_articles
            )

            # Prepare parallel LLM tasks
            context_task = None
            title_task = None

            # Only run expensive LLM operations if not a duplicate
            if not duplicate_result.is_duplicate:
                # Context analysis task
                if self.context_analyzer:
                    from src.config.settings import get_settings
                    settings = get_settings()
                    context_task = self.context_analyzer.analyze_context(
                        current_article=article,
                        max_similar_articles=5,
                        similarity_threshold=settings.embedding.context_similarity_threshold
                    )

                # Japanese title generation task
                temp_article = type('obj', (object,), {
                    'summarized_article': article,
                    'id': article.filtered_article.raw_article.id
                })()
                title_task = self.llm_router.generate_japanese_title(temp_article)

            # Execute LLM tasks in parallel
            if context_task and title_task:
                context_analysis, japanese_title = await asyncio.gather(
                    context_task, title_task, return_exceptions=True
                )
            elif context_task:
                context_analysis = await context_task
                japanese_title = None
            elif title_task:
                context_analysis = None
                japanese_title = await title_task
            else:
                context_analysis = None
                japanese_title = None

            # Handle exceptions from parallel execution
            if isinstance(context_analysis, Exception):
                logger.warning(f"Context analysis failed: {context_analysis}")
                context_analysis = None

            if isinstance(japanese_title, Exception):
                logger.warning(f"Japanese title generation failed: {japanese_title}")
                japanese_title = None

            return {
                'article': article,
                'duplicate_result': duplicate_result,
                'context_analysis': context_analysis,
                'japanese_title': japanese_title,
                'success': True
            }

        except Exception as e:
            logger.error(f"Article processing failed for {article.filtered_article.raw_article.id}: {e}")
            return {
                'article': article,
                'duplicate_result': None,
                'context_analysis': None,
                'japanese_title': None,
                'success': False,
                'error': str(e)
            }


    async def cluster_topics_node(self, state: dict) -> dict:
        """Cluster articles by topic with Phase 3 advanced clustering."""

        logger.info("Starting advanced topic clustering node")
        start_time = time.time()

        try:
            config = state["config"]
            deduplicated_articles = state["deduplicated_articles"]

            if not deduplicated_articles:
                logger.warning("No deduplicated articles to cluster")
                return {
                    **state,
                    "clustered_articles": [],
                    "status": "no_articles_to_cluster"
                }

            # Phase 3: Multi-source topic prioritization with clustering
            clustered_articles = await cluster_articles_with_multi_source_priority(
                articles=deduplicated_articles,
                max_articles_target=12,  # Increased from 10 to 12 for better coverage
            )

            # Generate proper citations for all clustered articles
            logger.info("Generating citations for clustered articles")
            citation_start_time = time.time()

            # Import citation generation function
            from src.utils.citation_generator import (
                CitationGenerator,
            )

            # Reset URL tracking for newsletter-wide citation deduplication
            citation_deduplicator = CitationGenerator()
            citation_deduplicator.reset_url_tracking()
            logger.info("Citation URL tracking reset for new newsletter generation")

            # PRD F-15準拠: クラスタ情報を活用した引用生成
            from src.utils.citation_generator import CitationGenerator
            citation_generator = CitationGenerator()

            # 各記事にクラスタ内の関連記事情報を渡して引用生成
            for i, article in enumerate(clustered_articles):
                try:
                    # 同じクラスタの他の記事を関連記事として使用
                    cluster_articles = [other for j, other in enumerate(clustered_articles) if i != j]

                    # PRD F-15: 実際のクラスタ記事を使用した引用生成
                    citations = await citation_generator.generate_citations(
                        article=article,
                        cluster_articles=cluster_articles[:4],  # 最大4記事をクラスタソースとして使用
                        max_citations=3
                    )

                    # 引用を記事に設定
                    article.citations = citations

                    logger.info(
                        f"Generated {len(citations)} cluster-based citations for article",
                        article_id=article.summarized_article.filtered_article.raw_article.id,
                        cluster_size=len(cluster_articles),
                        citation_details=[{
                            'source': c.source_name,
                            'title': c.title[:50] + "..." if len(c.title) > 50 else c.title
                        } for c in citations] if citations else []
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to generate cluster citations for article {i}: {e}",
                        article_id=getattr(article.summarized_article.filtered_article.raw_article, 'id', 'unknown')
                    )
                    # Assign empty citations on failure
                    article.citations = []

            citation_time = time.time() - citation_start_time
            logger.info(f"Citation generation completed in {citation_time:.2f}s")

            # Validate article count and apply PRD compliance if needed
            max_newsletter_articles = min(config.max_items, 10)  # PRD F-5: 最大10件

            if len(clustered_articles) > max_newsletter_articles:
                # Sort by relevance and take top articles
                def sort_key(article):
                    relevance = article.summarized_article.filtered_article.ai_relevance_score
                    confidence = article.summarized_article.summary.confidence_score
                    citation_count = len(getattr(article, 'citations', []))
                    return (relevance * 0.4 + confidence * 0.4 + citation_count * 0.1, -len(article.summarized_article.summary.summary_points))

                clustered_articles.sort(key=sort_key, reverse=True)
                clustered_articles = clustered_articles[:max_newsletter_articles]

                logger.info(
                    "Trimmed articles to meet PRD limit",
                    final_count=len(clustered_articles),
                    max_allowed=max_newsletter_articles
                )

            # PRD F-5: 7-10記事の確保（不足時は追加）
            if len(clustered_articles) < 7 and len(deduplicated_articles) > len(clustered_articles):
                logger.warning("Article count below PRD minimum (7), adding additional articles")

                # Get articles not in clustered_articles
                clustered_ids = {a.summarized_article.filtered_article.raw_article.id for a in clustered_articles}
                remaining_articles = [
                    a for a in deduplicated_articles
                    if a.summarized_article.filtered_article.raw_article.id not in clustered_ids
                ]

                if remaining_articles:
                    additional_needed = min(7 - len(clustered_articles), len(remaining_articles))
                    logger.info(
                        f"Adding {additional_needed} articles to meet PRD requirement",
                        current_count=len(clustered_articles),
                        target_count=7
                    )

                    additional_articles = remaining_articles[:additional_needed]
                    clustered_articles.extend(additional_articles)

                    logger.info(
                        f"Added {len(additional_articles)} articles to meet PRD requirement",
                        final_count=len(clustered_articles),
                        prd_compliance=len(clustered_articles) >= 7
                    )

            # PRD準拠: 最終コンプライアンスチェック
            compliance_result = self._validate_prd_compliance(clustered_articles)

            processing_time = time.time() - start_time

            # Log processing
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="cluster_topics_advanced",
                event_type="info",
                message=f"Advanced clustering completed with {len(clustered_articles)} articles",
                data={
                    "input_articles": len(deduplicated_articles),
                    "output_articles": len(clustered_articles),
                    "max_newsletter_articles": max_newsletter_articles,
                    "citations_generated": sum(len(a.citations) for a in clustered_articles),
                    "validation_enabled": True
                },
                duration_seconds=processing_time
            )

            return {
                **state,
                "clustered_articles": clustered_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "topics_clustered_advanced"
            }

        except Exception as e:
            logger.error("Advanced topic clustering failed", error=str(e))

            # Fallback to simple clustering
            try:
                logger.info("Falling back to simple clustering")

                def sort_key(article):
                    relevance = article.summarized_article.filtered_article.ai_relevance_score
                    confidence = article.summarized_article.summary.confidence_score
                    return (relevance * 0.6 + confidence * 0.4)

                sorted_articles = sorted(deduplicated_articles, key=sort_key, reverse=True)
                max_articles = min(len(sorted_articles), config.max_items, 10)
                fallback_articles = sorted_articles[:max_articles]

                # Add empty citations for fallback
                for article in fallback_articles:
                    if not hasattr(article, 'citations') or not article.citations:
                        article.citations = []

                logger.info(f"Fallback clustering produced {len(fallback_articles)} articles")

                fallback_log = ProcessingLog(
                    processing_id=config.processing_id,
                    timestamp=time.time(),
                    stage="cluster_topics_fallback",
                    event_type="warning",
                    message=f"Fallback clustering completed with {len(fallback_articles)} articles",
                    data={
                        "input_articles": len(deduplicated_articles),
                        "output_articles": len(fallback_articles),
                        "fallback_reason": str(e)
                    },
                    duration_seconds=time.time() - start_time
                )

                return {
                    **state,
                    "clustered_articles": fallback_articles,
                    "processing_logs": state["processing_logs"] + [fallback_log],
                    "status": "topics_clustered_fallback"
                }

            except Exception as fallback_error:
                logger.error("Fallback clustering also failed", error=str(fallback_error))

                error_log = ProcessingLog(
                    processing_id=config.processing_id,
                    timestamp=time.time(),
                    stage="cluster_topics",
                    event_type="error",
                    message=f"Both advanced and fallback clustering failed: {str(fallback_error)}",
                    duration_seconds=time.time() - start_time
                )

                return {
                    **state,
                    "clustered_articles": [],
                    "processing_logs": state["processing_logs"] + [error_log],
                    "status": "cluster_topics_failed"
                }

        try:
            config = state["config"]
            deduplicated_articles = state["deduplicated_articles"]

            if not deduplicated_articles:
                logger.warning("No deduplicated articles to cluster")
                return {
                    **state,
                    "clustered_articles": [],
                    "status": "no_articles_to_cluster"
                }

            # Phase 3: Multi-source topic prioritization with clustering
            clustered_articles = await cluster_articles_with_multi_source_priority(
                articles=deduplicated_articles,
                max_articles_target=12,  # Increased from 10 to 12 for better coverage
            )

            # Generate proper citations for all clustered articles
            logger.info("Generating citations for clustered articles")
            citation_start_time = time.time()

            # Import citation generation function
            from src.utils.citation_generator import (
                CitationGenerator,
            )

            # Reset URL tracking for newsletter-wide citation deduplication
            citation_deduplicator = CitationGenerator()
            citation_deduplicator.reset_url_tracking()
            logger.info("Citation URL tracking reset for new newsletter generation")

            # PRD F-15準拠: クラスタ情報を活用した引用生成
            from src.utils.citation_generator import CitationGenerator
            citation_generator = CitationGenerator()

            # 各記事にクラスタ内の関連記事情報を渡して引用生成
            for i, article in enumerate(clustered_articles):
                try:
                    # 同じクラスタの他の記事を関連記事として使用
                    cluster_articles = [other for j, other in enumerate(clustered_articles) if i != j]

                    # PRD F-15: 実際のクラスタ記事を使用した引用生成
                    citations = await citation_generator.generate_citations(
                        article=article,
                        cluster_articles=cluster_articles[:4],  # 最大4記事をクラスタソースとして使用
                        max_citations=3
                    )

                    # 引用を記事に設定
                    article.citations = citations

                    logger.info(
                        f"Generated {len(citations)} cluster-based citations for article",
                        article_id=article.summarized_article.filtered_article.raw_article.id,
                        cluster_size=len(cluster_articles)
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to generate cluster citations for article {i}: {e}",
                        article_id=article.summarized_article.filtered_article.raw_article.id
                    )
                    # フォールバック: 空の引用リスト
                    article.citations = []

            # Apply advanced deduplication across all articles

            all_citations = []
            article_citation_map = {}

            # Collect all citations and track which belong to which article
            for i, article in enumerate(clustered_articles):
                if hasattr(article, 'citations') and article.citations:
                    article_citation_map[i] = len(all_citations)
                    all_citations.extend(article.citations)
                else:
                    article_citation_map[i] = None

            # Perform global deduplication
            if all_citations:
                unique_citations = citation_deduplicator.deduplicate_citations(all_citations)

                # PRD準拠: 全記事に最低1つの引用を保証する改良アルゴリズム
                total_articles = len(clustered_articles)
                citations_per_article = max(1, len(unique_citations) // total_articles)
                remaining_citations = len(unique_citations) % total_articles

                citation_index = 0
                for i, article in enumerate(clustered_articles):
                    # 各記事に最低1つ、可能であれば均等に配分
                    base_count = citations_per_article
                    if i < remaining_citations:
                        base_count += 1

                    # 元の記事に引用があった場合は最低2つ
                    if article_citation_map[i] is not None:
                        target_count = max(base_count, 2)
                    else:
                        target_count = base_count

                    # 利用可能な引用から配分
                    article_citations = []
                    for _j in range(target_count):
                        if citation_index < len(unique_citations):
                            article_citations.append(unique_citations[citation_index])
                            citation_index += 1
                        else:
                            break

                    # 引用がない場合は最低保証引用を生成
                    if not article_citations:
                        from src.constants.mappings import format_source_name
                        from src.models.schemas import Citation

                        raw_article = article.summarized_article.filtered_article.raw_article
                        fallback_citation = Citation(
                            source_name=format_source_name(raw_article.source_id),
                            url=str(raw_article.url),
                            title=raw_article.title,
                            japanese_summary=f"{raw_article.title[:50]}...に関する詳細分析"
                        )
                        article_citations = [fallback_citation]

                    article.citations = article_citations

                    logger.debug(
                        f"Article {i+1} assigned {len(article_citations)} citations",
                        article_id=article.summarized_article.filtered_article.raw_article.id
                    )

                logger.info(f"Citation deduplication: {len(all_citations)} → {len(unique_citations)} citations")

            citation_time = time.time() - citation_start_time
            logger.info(f"Citation generation and deduplication completed in {citation_time:.2f}s")

            # Validate article content and filter out low-quality articles
            validated_articles = []
            quality_failures = 0

            for article in clustered_articles:
                try:
                    validation_result = validate_article_content(
                        article.summarized_article.summary.summary_points
                    )

                    # Check if article meets quality standards - balanced for quality and quantity
                    quality_threshold = 0.55  # Reduced from 0.6 to 0.55 for better article count balance
                    has_critical_errors = any(
                        (hasattr(violation, 'severity') and
                         hasattr(violation.severity, 'value') and
                         violation.severity.value == "ERROR") or
                        (hasattr(violation, 'severity') and
                         isinstance(violation.severity, str) and
                         violation.severity == "ERROR")
                        for violation in validation_result.violations
                    )

                    # Reject articles with critical errors or very low scores
                    if has_critical_errors or validation_result.quality_score < quality_threshold:
                        quality_failures += 1
                        logger.warning(
                            "Article rejected due to quality issues",
                            article_id=article.summarized_article.filtered_article.raw_article.id,
                            quality_score=validation_result.quality_score,
                            has_critical_errors=has_critical_errors,
                            violations=[getattr(v, 'rule_id', str(v)) for v in validation_result.violations]
                        )
                        continue

                    # Add validation metadata for passed articles
                    if hasattr(article, 'metadata'):
                        article.metadata = article.metadata or {}
                        article.metadata.update({
                            'validation_score': validation_result.quality_score,
                            'validation_level': validation_result.quality_level.value,
                            'validation_violations': len(validation_result.violations)
                        })

                    validated_articles.append(article)

                except Exception as validation_error:
                    logger.warning(
                        "Article validation failed, keeping article",
                        article_id=article.summarized_article.filtered_article.raw_article.id,
                        error=str(validation_error)
                    )
                    # Keep article if validation fails to avoid empty newsletters
                    validated_articles.append(article)

            # Update clustered_articles with validated ones
            clustered_articles = validated_articles

            logger.info(
                "Quality validation completed",
                total_articles_before=len(clustered_articles) + quality_failures,
                quality_failures=quality_failures,
                articles_after_validation=len(clustered_articles)
            )

            # F-17: Save cluster relationships to database before finalizing
            await self._save_cluster_relationships(clustered_articles)

            # PRD準拠: F-5「上位10件までをニュースレター本文に整形」
            max_newsletter_articles = min(10, len(clustered_articles))
            clustered_articles = clustered_articles[:max_newsletter_articles]

            # PRD要件チェック: 最低7記事確保
            if len(clustered_articles) < 7:
                logger.warning(
                    f"Article count below PRD requirement: {len(clustered_articles)}/7 minimum",
                    recommendation="Consider lowering quality thresholds or expanding sources"
                )

                # PRD準拠: F-5 要件を満たすため、閾値を更に緩和して記事を追加取得
                if len(deduplicated_articles) > len(clustered_articles):
                    logger.info("Attempting to add more articles to meet PRD F-5 requirement (7-10 articles)")

                    # 品質閾値を更に下げて記事を追加
                    remaining_articles = [
                        article for article in deduplicated_articles
                        if article not in clustered_articles
                    ]

                    # 最低品質をクリアした記事から追加選出
                    additional_needed = 7 - len(clustered_articles)
                    if remaining_articles and additional_needed > 0:
                        # AI関連性スコアでソート
                        remaining_articles.sort(
                            key=lambda x: x.summarized_article.filtered_article.ai_relevance_score,
                            reverse=True
                        )

                        additional_articles = remaining_articles[:additional_needed]
                        clustered_articles.extend(additional_articles)

                        logger.info(
                            f"Added {len(additional_articles)} articles to meet PRD requirement",
                            final_count=len(clustered_articles),
                            prd_compliance=len(clustered_articles) >= 7
                        )

            # PRD準拠: 最終コンプライアンスチェック
            compliance_result = self._validate_prd_compliance(clustered_articles)

            processing_time = time.time() - start_time

            # Log processing
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="cluster_topics_advanced",
                event_type="info",
                message=f"Advanced clustering completed with {len(clustered_articles)} articles",
                data={
                    "input_articles": len(deduplicated_articles),
                    "output_articles": len(clustered_articles),
                    "max_newsletter_articles": max_newsletter_articles,
                    "citations_generated": sum(len(a.citations) for a in clustered_articles),
                    "validation_enabled": True
                },
                duration_seconds=processing_time
            )

            return {
                **state,
                "clustered_articles": clustered_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "topics_clustered_advanced"
            }

        except Exception as e:
            logger.error("Advanced topic clustering failed", error=str(e))

            # Fallback to simple clustering
            try:
                logger.info("Falling back to simple clustering")

                def sort_key(article):
                    relevance = article.summarized_article.filtered_article.ai_relevance_score
                    confidence = article.summarized_article.summary.confidence_score
                    return relevance + confidence

                clustered_articles = sorted(deduplicated_articles, key=sort_key, reverse=True)
                max_newsletter_articles = min(12, len(clustered_articles))  # Increased from 10 to 12
                clustered_articles = clustered_articles[:max_newsletter_articles]

                # Add basic citations as Citation objects
                for article in clustered_articles:
                    if not article.citations:
                        raw_article = article.summarized_article.filtered_article.raw_article
                        basic_citation = Citation(
                            source_name=raw_article.source_id.title(),
                            url=str(raw_article.url),
                            title=raw_article.title,
                            japanese_summary=f"{raw_article.title[:80]}に関する記事"
                        )
                        article.citations = [basic_citation]

                fallback_log = ProcessingLog(
                    processing_id=config.processing_id,
                    timestamp=time.time(),
                    stage="cluster_topics_fallback",
                    event_type="warning",
                    message=f"Used fallback clustering, selected {len(clustered_articles)} articles",
                    data={
                        "input_articles": len(deduplicated_articles),
                        "output_articles": len(clustered_articles),
                        "fallback_reason": str(e)
                    },
                    duration_seconds=time.time() - start_time
                )

                return {
                    **state,
                    "clustered_articles": clustered_articles,
                    "processing_logs": state["processing_logs"] + [fallback_log],
                    "status": "topics_clustered_fallback"
                }

            except Exception as fallback_error:
                logger.error("Fallback clustering also failed", error=str(fallback_error))

                error_log = ProcessingLog(
                    processing_id=state["config"].processing_id,
                    timestamp=time.time(),
                    stage="cluster_topics",
                    event_type="error",
                    message=f"Both advanced and fallback clustering failed: {str(e)}",
                    duration_seconds=time.time() - start_time
                )

                return {
                    **state,
                    "clustered_articles": [],
                    "processing_logs": state["processing_logs"] + [error_log],
                    "status": "clustering_failed"
                }

    async def process_images_node(self, state: dict) -> dict:
        """Process images for articles (Phase 3: Image Integration)."""

        logger.info("Starting image processing node")
        start_time = time.time()

        try:
            config = state["config"]
            clustered_articles = state["clustered_articles"]

            if not clustered_articles:
                logger.warning("No clustered articles to process images for")
                return {
                    **state,
                    "image_processed_articles": [],
                    "status": "no_articles_for_images"
                }

            # Initialize image processor lazily
            if self.image_processor is None:
                try:
                    self.image_processor = ImageProcessor()
                    logger.info("ImageProcessor initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize ImageProcessor: {e}")
                    # Continue without image processing
                    return {
                        **state,
                        "image_processed_articles": clustered_articles,
                        "status": "image_processor_disabled"
                    }

            # Process images for articles
            logger.info(f"Processing images for {len(clustered_articles)} articles")

            # Use concurrent processing for better performance
            processed_articles = []
            max_concurrent = min(5, len(clustered_articles))  # Limit concurrency

            # Process articles in batches to avoid overwhelming the system
            import asyncio
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_single_article(article: ProcessedArticle) -> ProcessedArticle:
                """Process image for a single article."""
                async with semaphore:
                    try:
                        # Get article URL
                        article_url = article.summarized_article.filtered_article.raw_article.url
                        article_id = article.summarized_article.filtered_article.raw_article.id

                        logger.debug(f"Processing image for article: {article_id}")

                        # Process image (this is synchronous but wrapped in executor)
                        loop = asyncio.get_event_loop()
                        image_result = await loop.run_in_executor(
                            None,
                            self.image_processor.process_article_image,
                            article_url,
                            article_id
                        )

                        if image_result:
                            # Update article with image information
                            article.image_url = image_result['image_url']
                            article.image_metadata = {
                                'source_type': image_result['source_type'],
                                'dimensions': image_result['dimensions'],
                                'file_size': image_result['file_size'],
                                'original_url': image_result['original_url']
                            }

                            logger.info(
                                f"Successfully processed image for article {article_id}",
                                image_url=image_result['image_url'],
                                source_type=image_result['source_type']
                            )
                        else:
                            logger.debug(f"No image found for article: {article_id}")
                            # Keep article without image

                        return article

                    except Exception as e:
                        logger.warning(f"Failed to process image for article {getattr(article.summarized_article.filtered_article.raw_article, 'id', 'unknown')}: {e}")
                        # Return article without image on error
                        return article

            # Process all articles concurrently
            tasks = [process_single_article(article) for article in clustered_articles]
            processed_articles = await asyncio.gather(*tasks, return_exceptions=False)

            # Count successful image processing
            articles_with_images = sum(1 for article in processed_articles if getattr(article, 'image_url', None))

            processing_time = time.time() - start_time

            logger.info(
                "Image processing completed",
                total_articles=len(processed_articles),
                articles_with_images=articles_with_images,
                processing_time=f"{processing_time:.2f}s"
            )

            # Log processing summary
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="process_images",
                event_type="info",
                message=f"Processed images for {len(processed_articles)} articles ({articles_with_images} with images)",
                duration_seconds=processing_time,
                metadata={
                    "total_articles": len(processed_articles),
                    "articles_with_images": articles_with_images,
                    "image_success_rate": f"{(articles_with_images/len(processed_articles)*100):.1f}%" if processed_articles else "0%"
                }
            )

            return {
                **state,
                "image_processed_articles": processed_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "images_processed"
            }

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Image processing node failed: {e}")

            # Return original articles without images on failure
            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="process_images",
                event_type="error",
                message=f"Image processing failed: {str(e)}",
                duration_seconds=processing_time
            )

            return {
                **state,
                "image_processed_articles": state["clustered_articles"],
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "image_processing_failed"
            }

    async def generate_newsletter_node(self, state: dict) -> dict:
        """Generate final Markdown newsletter."""

        logger.info("Starting newsletter generation node")
        start_time = time.time()

        try:
            config = state["config"]
            # Use image_processed_articles if available, fall back to clustered_articles
            articles = state.get("image_processed_articles", state.get("clustered_articles", []))

            if not articles:
                logger.warning("No clustered articles to generate newsletter")

                # Create empty newsletter
                empty_newsletter = "# AI NEWS TLDR\n\n本日は注目すべきAI関連ニュースがございませんでした。\n"

                return {
                    **state,
                    "final_newsletter": empty_newsletter,
                    "status": "empty_newsletter_generated"
                }

            # Prepare processing summary
            processing_summary = {
                "articles_processed": len(state.get("summarized_articles", [])),
                "articles_final": len(articles),
                "processing_time_seconds": sum(
                    log.duration_seconds or 0
                    for log in state["processing_logs"]
                ),
                "success_rate": (
                    len(articles) / len(state.get("raw_articles", [1])) * 100
                )
            }

            # Generate newsletter using NewsletterGenerator class directly
            # This ensures all processing including multi-source consolidation is executed
            from src.utils.newsletter_generator import NewsletterGenerator

            generator = NewsletterGenerator(templates_dir="src/templates")
            newsletter_output = await generator.generate_newsletter(
                articles=articles,
                edition=config.edition,
                processing_summary=processing_summary,
                output_dir=config.output_dir
            )

            processing_time = time.time() - start_time

            # Log processing
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="generate_newsletter",
                event_type="info",
                message=f"Generated newsletter with {len(articles)} articles",
                data={
                    "articles_count": len(articles),
                    "word_count": newsletter_output.word_count,
                    "output_file": newsletter_output.metadata.get("output_file")
                },
                duration_seconds=processing_time
            )

            # Run comprehensive quality check on generated newsletter
            try:
                from src.utils.newsletter_quality_checker import NewsletterQualityChecker

                quality_checker = NewsletterQualityChecker()
                quality_report = await quality_checker.check_newsletter_quality(
                    content=newsletter_output.content,
                    metadata=newsletter_output.metadata
                )

                # Log quality results
                logger.info(
                    "Newsletter quality check completed",
                    overall_score=quality_report.overall_score,
                    requires_regeneration=quality_report.requires_regeneration,
                    issues_count=len(quality_report.issues),
                    critical_issues=len([i for i in quality_report.issues if i.severity == 'critical'])
                )

                # Add quality data to processing logs
                quality_log = ProcessingLog(
                    processing_id=config.processing_id,
                    timestamp=time.time(),
                    stage="quality_check",
                    event_type="info",
                    message=f"Quality score: {quality_report.overall_score:.2f}, Issues: {len(quality_report.issues)}",
                    data={
                        "quality_score": quality_report.overall_score,
                        "requires_regeneration": quality_report.requires_regeneration,
                        "critical_issues": len([i for i in quality_report.issues if i.severity == 'critical']),
                        "major_issues": len([i for i in quality_report.issues if i.severity == 'major']),
                        "minor_issues": len([i for i in quality_report.issues if i.severity == 'minor']),
                        "total_issues": len(quality_report.issues),
                        "section_scores": quality_report.section_scores
                    },
                    duration_seconds=time.time() - processing_time
                )

                # Add quality report to state
                state["quality_report"] = quality_report
                state["processing_logs"] = state["processing_logs"] + [log_entry, quality_log]

            except Exception as e:
                logger.warning(f"Quality check failed: {e}")
                # Continue without quality check rather than failing
                state["processing_logs"] = state["processing_logs"] + [log_entry]

            # Save to Supabase if not dry run
            if not config.dry_run:
                try:
                    await save_newsletter_to_supabase(
                        processing_id=config.processing_id,
                        articles=articles,
                        newsletter_content=newsletter_output.metadata.get("output_file", ""),
                        processing_logs=state["processing_logs"] + [log_entry],
                        metadata=newsletter_output.metadata,
                        edition=config.edition
                    )
                except Exception as e:
                    logger.warning("Failed to save to Supabase", error=str(e))

            # Cleanup resources to prevent memory leaks
            self._cleanup_workflow_resources()

            return {
                **state,
                "final_newsletter": newsletter_output.metadata.get("output_file", ""),
                "output_file": newsletter_output.metadata.get("output_file"),
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "newsletter_generated"
            }

        except Exception as e:
            logger.error("Generate newsletter node failed", error=str(e))

            # Cleanup resources even on failure
            self._cleanup_workflow_resources()

            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="generate_newsletter",
                event_type="error",
                message=f"Failed to generate newsletter: {str(e)}",
                duration_seconds=time.time() - start_time
            )

            return {
                **state,
                "final_newsletter": "",
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "newsletter_generation_failed"
            }

    # ------------------------------------------------------------------
    # Phase-4: Publish to Quaily
    # ------------------------------------------------------------------
    async def publish_to_quaily_node(self, state: dict) -> dict:
        """Publish the generated newsletter Markdown file to Quaily platform."""

        logger.info("Starting Quaily publish node")
        start_time = time.time()

        try:
            from src.utils.quaily_client import publish_newsletter

            config = state["config"]
            output_file: str | None = state.get("output_file")

            if not output_file:
                logger.warning("No output file produced – skipping Quaily publish step")
                return {**state, "status": "no_output_to_publish"}

            # Skip if publishing is disabled
            if not config.publish_enabled:
                logger.info("Quaily publish disabled via configuration – skipping")
                skip_log = ProcessingLog(
                    processing_id=config.processing_id,
                    timestamp=time.time(),
                    stage="publish_to_quaily",
                    event_type="info",
                    message="Publishing disabled (publish_enabled=False)",
                    duration_seconds=time.time() - start_time,
                )
                return {
                    **state,
                    "processing_logs": state["processing_logs"] + [skip_log],
                    "status": "quaily_publish_disabled",
                }

            # Perform publish – respect dry_run flag
            publish_result = publish_newsletter(
                file_path=output_file,
                edition=config.edition,
                dry_run=config.dry_run,
            )

            processing_time = time.time() - start_time

            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="publish_to_quaily",
                event_type="info" if publish_result.get("status") == "success" else "warning",
                message=f"Quaily publish status: {publish_result.get('status')}",
                data=publish_result,
                duration_seconds=processing_time,
            )

            # Record history for monitoring
            try:
                from src.utils.history_logger import record_publish
                record_publish(config.processing_id, publish_result)
            except Exception as hist_err:  # pylint: disable=broad-except
                logger.warning("Failed to record publish history", error=str(hist_err))

            # Compute recent success rate and attach to logs
            try:
                from src.utils.history_logger import compute_success_rate
                success_rate = compute_success_rate(100)
                logger.info("Current publish success rate (last 100)", rate=f"{success_rate:.1f}%")
            except Exception:
                pass

            return {
                **state,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "quaily_published" if publish_result.get("status") == "success" else "quaily_publish_skipped",
            }

        except Exception as e:
            logger.error("Publish to Quaily node failed", error=str(e))

            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="publish_to_quaily",
                event_type="error",
                message=f"Failed to publish to Quaily: {str(e)}",
                duration_seconds=time.time() - start_time,
            )

            return {
                **state,
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "quaily_publish_failed",
            }

    def _sort_articles_by_priority(self, articles: list) -> list:
        """
        Sort articles by source priority.

        優先順位:
        1. 公式リリース系 (priority: 1) - 最上位
        2. ニュースレター系 (priority: 2) - 次点
        3. メディア・YouTube系 (priority: 3) - 同列
        4. 日本語系ソース (priority: 4) - 最下位

        Args:
            articles: 記事リスト

        Returns:
            優先順位順にソートされた記事リスト
        """
        from src.constants.source_priorities import get_priority_description

        def get_sort_key(article):
            """Get sorting key for article (priority, then published_date desc)"""
            # Ensure source_priority is set
            if not hasattr(article, 'source_priority') or article.source_priority is None:
                article.set_source_priority()

            # Sort by priority (ascending = higher priority first), then by date (descending = newest first)
            return (article.source_priority, -article.published_date.timestamp())

        sorted_articles = sorted(articles, key=get_sort_key)

        # Log priority distribution for monitoring
        priority_counts = {}
        for article in sorted_articles:
            priority = getattr(article, 'source_priority', 3)
            priority_desc = get_priority_description(priority)
            priority_counts[priority_desc] = priority_counts.get(priority_desc, 0) + 1

        logger.info(
            "Article priority distribution after sorting",
            total_articles=len(sorted_articles),
            priority_distribution=priority_counts,
            top_sources=[{
                "source_id": article.source_id,
                "priority": getattr(article, 'source_priority', 3),
                "title": article.title[:50] + "..." if len(article.title) > 50 else article.title
            } for article in sorted_articles[:5]]  # Log top 5 articles
        )

        return sorted_articles

    async def _generate_contextual_update_summary(
        self,
        article: SummarizedArticle,
        context_analysis: 'ContextAnalysisResult'
    ) -> list[str] | None:
        """
        Generate enhanced summary for UPDATE articles incorporating past context.

        Args:
            article: Current article marked as UPDATE
            context_analysis: Context analysis result with references

        Returns:
            Enhanced summary points with past context or None if generation fails
        """

        try:
            # Prepare current article info
            current_title = article.filtered_article.raw_article.title
            current_points = article.summary.summary_points

            # Format references (past articles)
            references_text = ""
            past_links_text = ""
            if context_analysis.references:
                references_text = "\n".join([
                    f"- {ref}" for ref in context_analysis.references[:3]  # Limit to 3 references
                ])

                # PRD準拠: F-17 過去記事へのリンク機能
                # Generate past article links for contextual reference
                past_links_text = "\n\n**関連する過去記事:**\n"
                for i, ref in enumerate(context_analysis.references[:2], 1):  # Limit to 2 past links
                    # Extract title from reference (assuming format "Title - Source")
                    ref_title = ref.split(' - ')[0] if ' - ' in ref else ref[:50]
                    past_links_text += f"- [{ref_title}](#past-article-{i})\n"

            # Create context-aware prompt
            prompt = f"""以下の続報記事について、過去の関連記事の文脈を踏まえた包括的な日本語要約を生成してください。

【今回の記事】
タイトル: {current_title}
要点: {' / '.join(current_points)}

【過去の関連記事】
{references_text}

【文脈分析】
{context_analysis.reasoning}

【要件】
- 必ず4項目の箇条書きで作成
- 各項目150-200文字程度
- 過去の経緯を自然に織り込む
- 今回の新しい展開を明確に示す
- 「続報」「UPDATE」等の文言は使わない
- 具体的な変化や進展を強調

【出力形式】
- 過去の経緯を踏まえた現在の状況
- 今回発表された新しい要素や変化
- これまでとの比較や違い
- 今後への影響や展望{past_links_text}"""

            # Generate enhanced summary using LLM
            response = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )

            if not response:
                return None

            # Parse response into bullet points
            lines = response.strip().split('\n')
            summary_points = []

            for line in lines:
                line = line.strip()
                if line.startswith('- ') or line.startswith('• '):
                    point = line[2:].strip()
                    if 100 <= len(point) <= 250:
                        summary_points.append(point)

            # Validate output
            if len(summary_points) >= 3:
                # PRD準拠: F-17 過去記事リンクを最終ポイントに追加
                final_points = summary_points[:4]  # Take max 4 points
                if past_links_text and final_points:
                    final_points[-1] += past_links_text.replace('\n\n', ' ')  # Append past links to last point

                logger.info(
                    "Generated contextual update summary with past links",
                    article_id=article.filtered_article.raw_article.id,
                    enhanced_points=len(final_points),
                    references_used=len(context_analysis.references),
                    past_links_added=bool(past_links_text)
                )
                return final_points

            return None

        except Exception as e:
            logger.warning(
                "Failed to generate contextual update summary",
                article_id=article.filtered_article.raw_article.id,
                error=str(e)
            )
            return None

    def _validate_prd_compliance(self, articles: list[ProcessedArticle]) -> dict[str, any]:
        """
        Validate PRD compliance across multiple requirements.

        Args:
            articles: List of processed articles for the newsletter

        Returns:
            Compliance validation results
        """

        compliance_result = {
            "total_articles": len(articles),
            "prd_compliant": True,
            "violations": [],
            "warnings": []
        }

        # F-5: 上位10件までをニュースレター本文に整形 (7-10記事の範囲)
        if len(articles) < 7:
            compliance_result["prd_compliant"] = False
            compliance_result["violations"].append({
                "requirement": "F-5",
                "description": "記事数が最低要件を下回る",
                "expected": "7-10記事",
                "actual": f"{len(articles)}記事"
            })
        elif len(articles) > 10:
            compliance_result["warnings"].append({
                "requirement": "F-5",
                "description": "記事数が推奨上限を超過",
                "expected": "7-10記事",
                "actual": f"{len(articles)}記事"
            })

        # F-3: 3〜4個の箇条書きサマリー生成
        for i, article in enumerate(articles):
            summary_points = article.summarized_article.summary.summary_points
            if len(summary_points) < 3:
                compliance_result["warnings"].append({
                    "requirement": "F-3",
                    "description": f"記事{i+1}の箇条書きが不足",
                    "expected": "3-4個",
                    "actual": f"{len(summary_points)}個"
                })
            elif len(summary_points) > 4:
                compliance_result["warnings"].append({
                    "requirement": "F-3",
                    "description": f"記事{i+1}の箇条書きが過多",
                    "expected": "3-4個",
                    "actual": f"{len(summary_points)}個"
                })

        # Citations requirement: 3 citations per article
        for i, article in enumerate(articles):
            citation_count = len(article.citations) if article.citations else 0
            if citation_count < 1:
                compliance_result["violations"].append({
                    "requirement": "Citations",
                    "description": f"記事{i+1}に引用が不足",
                    "expected": "最低1個",
                    "actual": f"{citation_count}個"
                })
            elif citation_count < 3:
                compliance_result["warnings"].append({
                    "requirement": "Citations",
                    "description": f"記事{i+1}の引用が推奨数を下回る",
                    "expected": "3個推奨",
                    "actual": f"{citation_count}個"
                })

        # F-16: 続報記事の🆙可視化
        update_articles = [a for a in articles if a.is_update]
        update_with_emoji = [a for a in update_articles
                           if a.japanese_title and a.japanese_title.startswith('🆙')]

        if update_articles and len(update_with_emoji) < len(update_articles):
            missing_emoji = len(update_articles) - len(update_with_emoji)
            compliance_result["warnings"].append({
                "requirement": "F-16",
                "description": f"{missing_emoji}件の続報記事に🆙絵文字が不足",
                "expected": "全続報記事に🆙",
                "actual": f"{len(update_with_emoji)}/{len(update_articles)}記事"
            })

        # Log compliance results
        if compliance_result["prd_compliant"]:
            logger.info(
                "PRD compliance validation PASSED",
                article_count=len(articles),
                violations=len(compliance_result["violations"]),
                warnings=len(compliance_result["warnings"])
            )
        else:
            logger.error(
                "PRD compliance validation FAILED",
                article_count=len(articles),
                violations=len(compliance_result["violations"]),
                warnings=len(compliance_result["warnings"]),
                violation_details=compliance_result["violations"]
            )

        return compliance_result

    # Refactored methods for check_duplicates_node
    async def _consolidate_duplicates(self, summarized_articles: list) -> list:
        """Phase 1: Intelligent duplicate consolidation."""
        logger.info("Phase 1: Intelligent duplicate consolidation")

        # Use enhanced consolidation with lowered thresholds
        settings = get_settings()
        consolidation_threshold = settings.embedding.duplicate_similarity_threshold
        # Lower the threshold for consolidation to catch more related articles
        adjusted_threshold = max(
            settings.embedding.minimum_consolidation_threshold,
            consolidation_threshold - settings.embedding.consolidation_threshold_adjustment
        )

        # consolidate_similar_articles は同期関数なので await 不要
        consolidated_articles = consolidate_similar_articles(
            articles=summarized_articles,
            jaccard_threshold=adjusted_threshold,
            sequence_threshold=adjusted_threshold,
            consolidation_mode=True
        )

        consolidation_stats = {
            "input_articles": len(summarized_articles),
            "output_articles": len(consolidated_articles),
            "articles_consolidated": len(summarized_articles) - len(consolidated_articles)
        }

        logger.info("Duplicate consolidation completed", **consolidation_stats)
        return consolidated_articles

    async def _process_articles_with_context(self, consolidated_articles: list) -> tuple:
        """Phase 2: Context analysis and article processing."""
        logger.info("Phase 2: Context analysis and article processing")

        # Initialize context analyzer if needed
        if self.context_analyzer is None:
            if self.embedding_manager is None:
                self.embedding_manager = EmbeddingManager()

            self.context_analyzer = ContextAnalyzer(
                embedding_manager=self.embedding_manager,
                llm_router=self.llm_router
            )

        deduplicated_articles = []
        duplicate_count = 0
        update_count = 0

        for article in consolidated_articles:
            try:
                processed_article, is_duplicate, is_update = await self._process_single_article_for_duplicates(
                    article, deduplicated_articles
                )

                if processed_article:
                    deduplicated_articles.append(processed_article)
                    if is_update:
                        update_count += 1
                elif is_duplicate:
                    duplicate_count += 1

            except Exception as e:
                logger.error(
                    "Error processing article for duplicates/context",
                    article_id=article.filtered_article.raw_article.id,
                    error=str(e)
                )
                continue

        return deduplicated_articles, duplicate_count, update_count

    async def _process_single_article_for_duplicates(self, article, existing_articles: list) -> tuple:
        """Process a single article for duplicates and context analysis."""
        # Check for duplicates using BasicDuplicateChecker as primary method
        duplicate_result = self.duplicate_checker.check_duplicate(
            current_article=article,
            past_articles=[p.summarized_article for p in existing_articles]
        )

        if duplicate_result.is_duplicate:
            logger.info(
                "Duplicate article filtered out by basic checker",
                article_id=article.filtered_article.raw_article.id,
                similarity_score=duplicate_result.similarity_score
            )
            return None, True, False

        # Context analysis for UPDATE detection and relationship building (not for SKIP decisions)
        context_analysis = await self._analyze_context_for_article(article)
        is_update = False

        # Apply context analysis results - ONLY for UPDATE detection, not SKIP
        if context_analysis:
            # CRITICAL: Remove SKIP logic to prevent double elimination
            # Only process UPDATE decisions from context analysis
            if context_analysis.decision == "UPDATE" and context_analysis.references:
                is_update = await self._apply_context_analysis_to_article(article, context_analysis)
                logger.info(
                    "Article marked as UPDATE by context analysis",
                    article_id=article.filtered_article.raw_article.id,
                    references_count=len(context_analysis.references)
                )

        # Create processed article
        processed_article = ProcessedArticle(
            summarized_article=article,
            duplicate_check=duplicate_result,
            context_analysis=context_analysis,
            final_summary=' '.join(article.summary.summary_points),  # Join summary points into string
            japanese_title=None,  # Will be generated later in NewsletterGenerator
            citations=[],  # Citations will be generated later
            is_update=is_update
        )

        # Add to embedding index and save to Supabase
        await self._save_article_data_to_storage(article, processed_article, is_update, context_analysis)

        return processed_article, False, is_update

    async def _analyze_context_for_article(self, article):
        """Analyze context for a single article."""
        if not self.context_analyzer:
            return None

        try:
            settings = get_settings()

            # Debug: Check if embedding manager has data
            if self.embedding_manager:
                total_vectors = getattr(self.embedding_manager, 'total_vectors', 0)
                logger.info(f"EmbeddingManager has {total_vectors} past articles for context analysis")

            context_analysis = await self.context_analyzer.analyze_context(
                current_article=article,
                max_similar_articles=5,
                similarity_threshold=settings.embedding.context_similarity_threshold
            )

            # Debug: Log context analysis results
            if context_analysis:
                logger.info(
                    f"Context analysis completed for article {article.filtered_article.raw_article.id}: "
                    f"decision={context_analysis.decision}, "
                    f"references={len(context_analysis.references) if context_analysis.references else 0}"
                )
            else:
                logger.warning(f"Context analysis returned None for article {article.filtered_article.raw_article.id}")

            return context_analysis
        except Exception as e:
            logger.warning(
                "Context analysis failed, proceeding with standard processing",
                article_id=article.filtered_article.raw_article.id,
                error=str(e)
            )
            return None

    async def _apply_context_analysis_to_article(self, article, context_analysis) -> bool:
        """Apply context analysis results to an article."""
        is_update = False

        if context_analysis.decision == "UPDATE":
            is_update = True

            # 🔥 ULTRA THINK: 🆙絵文字はnewsletter_generatorで統合処理
            # 重複防止のためworkflowでの付与を削除
            logger.info(
                "Marked article as UPDATE in workflow - emoji handling delegated to title generation",
                article_id=article.filtered_article.raw_article.id
            )

            # Generate context-aware summary if available
            if context_analysis.contextual_summary:
                enhanced_summary_points = await self._generate_contextual_update_summary(
                    article, context_analysis
                )

                if enhanced_summary_points:
                    # Update the article's summary
                    from src.models.schemas import SummaryOutput
                    original_summary = article.summary

                    enhanced_summary = SummaryOutput(
                        summary_points=enhanced_summary_points,
                        confidence_score=min(original_summary.confidence_score + 0.15, 1.0),
                        source_reliability=original_summary.source_reliability,
                        model_used=original_summary.model_used + "_contextual",
                        fallback_used=original_summary.fallback_used,
                        total_tokens=original_summary.total_tokens,
                        processing_time_seconds=original_summary.processing_time_seconds
                    )

                    article.summary = enhanced_summary

                    logger.info(
                        "Enhanced UPDATE article with past context",
                        article_id=article.filtered_article.raw_article.id,
                        context_refs=len(context_analysis.references)
                    )

        elif context_analysis.decision == "KEEP" and context_analysis.references:
            # メタデータとして文脈情報を保存
            if not hasattr(article, 'context_metadata'):
                article.context_metadata = {}

            article.context_metadata.update({
                'related_articles': context_analysis.references[:3],
                'context_reasoning': context_analysis.reasoning,
                'similarity_score': context_analysis.similarity_score
            })

            logger.info(
                "Added context metadata to KEEP article",
                article_id=article.filtered_article.raw_article.id,
                related_count=len(context_analysis.references)
            )

        return is_update

    async def _save_article_data_to_storage(self, article, processed_article, is_update: bool, context_analysis):
        """Save article data to embedding index and Supabase."""
        # Add to embedding index for future context analysis
        try:
            await self.embedding_manager.add_article(article, save_immediately=False)
        except Exception as embedding_error:
            logger.warning(
                "Failed to add article to embedding index",
                article_id=article.filtered_article.raw_article.id,
                error=str(embedding_error)
            )

        # Save to Supabase contextual_articles
        await self._save_article_to_supabase(article, processed_article, is_update, context_analysis)

    async def _save_article_to_supabase(self, article, processed_article, is_update: bool, context_analysis):
        """Save article and relationships to Supabase."""
        try:
            from src.utils.supabase_client import save_contextual_article

            # Generate embedding for Supabase
            embedding_text = f"{article.filtered_article.raw_article.title}\n{article.filtered_article.raw_article.content}\n" + "\n".join(article.summary.summary_points)
            embedding_vector = await self.embedding_manager.generate_embedding(embedding_text)

            # Save contextual article
            article_uuid = await save_contextual_article(
                article=processed_article,
                embedding=embedding_vector.tolist() if embedding_vector is not None else None,
                topic_cluster=None  # Will be set in clustering phase
            )

            # Save relationships if this is an update
            if is_update and context_analysis and context_analysis.references and article_uuid:
                await self._save_supabase_relationships(article_uuid, context_analysis)

            logger.info(
                "Saved article to Supabase",
                article_id=article.filtered_article.raw_article.id,
                article_uuid=article_uuid,
                is_update=is_update
            )

        except Exception as supabase_error:
            logger.warning(
                "Failed to save article to Supabase",
                article_id=article.filtered_article.raw_article.id,
                error=str(supabase_error)
            )

    async def _save_supabase_relationships(self, article_uuid: str, context_analysis):
        """Save article relationships to Supabase (F-17 implementation)."""
        for ref_article_id in context_analysis.references[:3]:  # Limit to 3 relationships
            try:
                from src.utils.supabase_client import get_supabase_client, save_article_relationship
                client = await get_supabase_client()
                if client.is_available():
                    ref_result = client.client.table("contextual_articles").select("id").eq(
                        "article_id", ref_article_id
                    ).execute()

                    if ref_result.data:
                        ref_uuid = ref_result.data[0]["id"]

                        # F-17: Determine relationship type based on context analysis decision
                        relationship_type = "related"  # Default
                        if context_analysis.decision == "UPDATE":
                            relationship_type = "update"
                        elif context_analysis.similarity_score > 0.8:
                            relationship_type = "sequel"

                        await save_article_relationship(
                            parent_article_uuid=ref_uuid,
                            child_article_uuid=article_uuid,
                            relationship_type=relationship_type,
                            similarity_score=context_analysis.similarity_score,
                            reasoning=f"Context analysis: {context_analysis.reasoning}"
                        )

                        logger.info(
                            "F-17: Saved article relationship",
                            parent_article_id=ref_article_id,
                            child_article_uuid=article_uuid,
                            relationship_type=relationship_type,
                            similarity_score=context_analysis.similarity_score
                        )
            except Exception as e:
                logger.warning(f"Failed to save relationship for {ref_article_id}: {e}")

    async def _save_cluster_relationships(self, clustered_articles: list):
        """Save topic cluster relationships to Supabase (F-17 enhancement)."""
        try:
            from src.utils.supabase_client import get_supabase_client, save_article_relationship
            client = await get_supabase_client()

            if not client.is_available():
                return

            # Group articles by cluster_id
            clusters = {}
            for article in clustered_articles:
                cluster_id = getattr(article, 'cluster_id', None)
                if cluster_id is not None:
                    if cluster_id not in clusters:
                        clusters[cluster_id] = []
                    clusters[cluster_id].append(article)

            relationship_count = 0

            # For each cluster with multiple articles, record relationships
            for cluster_id, articles in clusters.items():
                if len(articles) < 2:
                    continue

                # Get article UUIDs from Supabase
                article_uuids = {}
                for article in articles:
                    article_id = article.summarized_article.filtered_article.raw_article.id
                    try:
                        result = client.client.table("contextual_articles").select("id").eq(
                            "article_id", article_id
                        ).execute()

                        if result.data:
                            article_uuids[article_id] = result.data[0]["id"]
                    except Exception as e:
                        logger.warning(f"Failed to get UUID for article {article_id}: {e}")

                # Record relationships between articles in the same cluster
                article_list = list(article_uuids.items())
                for i, (_article_id_1, uuid_1) in enumerate(article_list):
                    for _j, (_article_id_2, uuid_2) in enumerate(article_list[i+1:], i+1):
                        try:
                            # Calculate similarity score based on cluster confidence
                            # For now, use a default value since we don't have precise scores
                            similarity_score = 0.75  # Default cluster similarity

                            await save_article_relationship(
                                parent_article_uuid=uuid_1,
                                child_article_uuid=uuid_2,
                                relationship_type="related",
                                similarity_score=similarity_score,
                                reasoning=f"Topic cluster {cluster_id}: Articles grouped together by semantic similarity"
                            )
                            relationship_count += 1

                        except Exception as e:
                            logger.warning(f"Failed to save cluster relationship: {e}")

            if relationship_count > 0:
                logger.info(
                    "F-17: Saved topic cluster relationships",
                    clusters_processed=len(clusters),
                    relationships_created=relationship_count
                )

        except Exception as e:
            logger.warning(f"Failed to save cluster relationships: {e}")

    def _log_duplicate_processing_results(self, config, input_articles: list, output_articles: list,
                             duplicate_count: int, update_count: int, processing_time: float) -> ProcessingLog:
        """Create processing log for duplicate checking results."""
        return ProcessingLog(
            processing_id=config.processing_id,
            timestamp=time.time(),
            stage="check_duplicates_context",
            event_type="info",
            message=f"Processed {len(output_articles)} articles, removed {duplicate_count} duplicates, found {update_count} updates",
            data={
                "input_articles": len(input_articles),
                "output_articles": len(output_articles),
                "duplicates_removed": duplicate_count,
                "updates_found": update_count,
                "duplicate_rate": duplicate_count / len(input_articles) if input_articles else 0
            },
            duration_seconds=processing_time
        )

    def _cleanup_workflow_resources(self) -> None:
        """
        Clean up workflow resources to prevent memory leaks.

        This method should be called at the end of newsletter generation
        to free up memory used by various components.
        """
        try:
            # Get memory stats before cleanup
            memory_stats_before = {}

            # Cleanup EmbeddingManager
            if hasattr(self, 'embedding_manager') and self.embedding_manager:
                memory_stats_before = self.embedding_manager.get_memory_usage_stats()
                self.embedding_manager.cleanup_resources()
                logger.info("EmbeddingManager resources cleaned up")

            # Cleanup ContextAnalyzer if it exists
            if hasattr(self, 'context_analyzer') and self.context_analyzer:
                # Reset context analyzer state
                self.context_analyzer = None
                logger.info("ContextAnalyzer resources cleaned up")

            # Cleanup LLM Router clients cache
            if hasattr(self, 'llm_router') and self.llm_router:
                if hasattr(self.llm_router, '_clients'):
                    client_count = len(self.llm_router._clients)
                    self.llm_router._clients.clear()
                    logger.info(f"Cleared {client_count} LLM client cache entries")

            # Cleanup DuplicateChecker cache
            if hasattr(self, 'duplicate_checker') and self.duplicate_checker:
                # If there's any internal cache, clear it
                if hasattr(self.duplicate_checker, '_article_cache'):
                    self.duplicate_checker._article_cache.clear()
                logger.info("DuplicateChecker cache cleaned up")

            # Log memory savings
            if memory_stats_before:
                logger.info(
                    "Workflow cleanup completed",
                    metadata_entries_cleared=memory_stats_before.get("metadata_count", 0),
                    vectors_cleared=memory_stats_before.get("index_total_vectors", 0),
                    estimated_memory_freed_mb=memory_stats_before.get("estimated_index_memory_bytes", 0) / (1024 * 1024)
                )
            else:
                logger.info("Workflow cleanup completed")

        except Exception as e:
            logger.warning(f"Error during workflow cleanup: {e}")


def create_newsletter_workflow() -> StateGraph:
    """Create and compile the newsletter generation workflow."""

    workflow_instance = NewsletterWorkflow()

    # Create state graph
    workflow = StateGraph(dict)  # Use dict instead of NewsletterState for LangGraph compatibility

    # Add nodes (using parallel version for performance)
    workflow.add_node("fetch_sources", workflow_instance.fetch_sources_node)
    workflow.add_node("filter_ai_content", workflow_instance.filter_ai_content_node)
    workflow.add_node("generate_summaries", workflow_instance.generate_summaries_node)
    workflow.add_node("check_duplicates", workflow_instance.check_duplicates_node)
    workflow.add_node("cluster_topics", workflow_instance.cluster_topics_node)
    workflow.add_node("process_images", workflow_instance.process_images_node)
    workflow.add_node("generate_newsletter", workflow_instance.generate_newsletter_node)
    workflow.add_node("publish_to_quaily", workflow_instance.publish_to_quaily_node)

    # Add edges (sequential flow)
    workflow.add_edge("fetch_sources", "filter_ai_content")
    workflow.add_edge("filter_ai_content", "generate_summaries")
    workflow.add_edge("generate_summaries", "check_duplicates")
    workflow.add_edge("check_duplicates", "cluster_topics")
    workflow.add_edge("cluster_topics", "process_images")
    workflow.add_edge("process_images", "generate_newsletter")
    workflow.add_edge("generate_newsletter", "publish_to_quaily")
    workflow.add_edge("publish_to_quaily", END)

    # Set entry point
    workflow.set_entry_point("fetch_sources")

    return workflow.compile()
