"""
LangGraph workflow for newsletter generation.

This module defines the complete workflow for generating AI news newsletters
using LangGraph state management and node-based processing.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda

from src.models.schemas import (
    NewsletterState, 
    ProcessedArticle,
    SummarizedArticle,
    ProcessingLog,
    Citation
)
from src.utils.content_fetcher import fetch_content_from_sources
from src.utils.ai_filter import filter_ai_content
from src.utils.ai_semantic_filter import AISemanticFilter
from src.llm.llm_router import LLMRouter
from src.deduplication.duplicate_checker import BasicDuplicateChecker, consolidate_similar_articles
from src.utils.supabase_client import save_newsletter_to_supabase
from src.utils.embedding_manager import EmbeddingManager, add_articles_to_index
from src.utils.context_analyzer import ContextAnalyzer
from src.utils.topic_clustering import cluster_articles_for_newsletter, cluster_articles_with_multi_source_priority
from src.utils.citation_generator import enhance_articles_with_citations
from src.utils.content_validator import validate_article_content
from src.utils.error_handler import with_retry, get_error_summary
from src.utils.langsmith_tracer import get_tracer, trace_newsletter_generation, finalize_newsletter_tracing
from src.utils.logger import setup_logging
from src.constants.settings import PERFORMANCE, SIMILARITY_THRESHOLDS, NEWSLETTER
from src.constants.mappings import COMPANY_MAPPINGS
from src.constants.messages import DEFAULT_CONTENT

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
    
    async def fetch_sources_node(self, state: Dict) -> Dict:
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
    
    async def filter_ai_content_node(self, state: Dict) -> Dict:
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
                    self.semantic_filter = AISemanticFilter()
                    await self.semantic_filter.initialize()
                
                # PRD準拠: 7-10記事確保のため閾値を大幅緩和
                base_threshold = max(0.15, config.ai_relevance_threshold - 0.25)  # PRD要件のため大幅緩和
                min_threshold = max(0.08, config.ai_relevance_threshold - 0.35)  # 最低限のAI関連性のみ確保
                
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
    
    async def generate_summaries_node(self, state: Dict) -> Dict:
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
    
    async def check_duplicates_node(self, state: Dict) -> Dict:
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
            
            # Phase 1: Intelligent duplicate consolidation
            logger.info("Phase 1: Intelligent duplicate consolidation")
            
            # Use enhanced consolidation with lowered thresholds
            consolidation_threshold = getattr(config, 'duplicate_similarity_threshold', 0.85)
            # Lower the threshold for consolidation to catch more related articles
            adjusted_threshold = max(0.55, consolidation_threshold - 0.25)  # Further lowered
            
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
            
            logger.info(
                "Duplicate consolidation completed",
                **consolidation_stats
            )
            
            # Phase 2: Context analysis and article processing
            logger.info("Phase 2: Context analysis and article processing")
            
            # Initialize context analyzer if needed
            if self.context_analyzer is None:
                # Initialize embedding manager first if needed
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
                    # Pass only the already *summarized* articles of previously accepted items
                    # to the duplicate checker.  Otherwise `ProcessedArticle` objects (which do not
                    # expose `filtered_article` at the top-level) cause attribute errors and the
                    # article is skipped.  This bug results inほぼ1件しか記事が残らない問題の原因でした。
                    duplicate_result = self.duplicate_checker.check_duplicate(
                        current_article=article,
                        past_articles=[p.summarized_article for p in deduplicated_articles]  # use compatible objects
                    )
                    
                    # Enhanced context analysis for ALL articles (PRD F-16, F-17改善)
                    if self.context_analyzer:
                        try:
                            context_analysis = await self.context_analyzer.analyze_context(
                                current_article=article,
                                max_similar_articles=5,
                                similarity_threshold=0.65  # 閾値を下げて関連性検出を改善
                            )
                            
                            # すべての記事に文脈情報を適用
                            if context_analysis and context_analysis.references:
                                # UPDATEの場合は特別処理
                                if context_analysis.decision == "UPDATE":
                                    is_update = True
                                    
                                    # Generate context-aware summary if available
                                    if context_analysis.contextual_summary:
                                        # Create enhanced summary incorporating past context
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
                                
                                # KEEPの場合も関連記事情報を記録（PRD F-17準拠）
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
                        
                        except Exception as e:
                            logger.warning(
                                "Context analysis failed, proceeding with standard processing",
                                article_id=article.filtered_article.raw_article.id,
                                error=str(e)
                            )
                            context_analysis = None
                    else:
                        context_analysis = None
                    
                    # Create processed article if not duplicate/skipped
                    if not duplicate_result.is_duplicate:
                        # Skip title generation in workflow, let NewsletterGenerator handle it
                        japanese_title = None  # Will be generated later in NewsletterGenerator
                        
                        processed_article = ProcessedArticle(
                            summarized_article=article,
                            duplicate_check=duplicate_result,
                            context_analysis=context_analysis,
                            final_summary=article.summary.summary_points,
                            japanese_title=japanese_title,
                            citations=[],  # Citations will be generated later
                            is_update=is_update
                        )
                        
                        deduplicated_articles.append(processed_article)
                        
                        # Add to embedding index for future context analysis
                        try:
                            await self.embedding_manager.add_article(
                                article, save_immediately=False
                            )
                        except Exception as embedding_error:
                            logger.warning(
                                "Failed to add article to embedding index",
                                article_id=article.filtered_article.raw_article.id,
                                error=str(embedding_error)
                            )
                        
                        # Save to Supabase contextual_articles
                        try:
                            from src.utils.supabase_client import save_contextual_article, save_article_relationship
                            
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
                                for ref_article_id in context_analysis.references[:3]:  # Limit to 3 relationships
                                    # Get UUID of referenced article
                                    from src.utils.supabase_client import get_supabase_client
                                    client = await get_supabase_client()
                                    if client.is_available():
                                        ref_result = client.client.table("contextual_articles").select("id").eq(
                                            "article_id", ref_article_id
                                        ).execute()
                                        
                                        if ref_result.data:
                                            ref_uuid = ref_result.data[0]["id"]
                                            await save_article_relationship(
                                                parent_article_uuid=ref_uuid,
                                                child_article_uuid=article_uuid,
                                                relationship_type="update",
                                                similarity_score=context_analysis.similarity_score,
                                                reasoning=context_analysis.reasoning
                                            )
                            
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
                    
                    else:
                        duplicate_count += 1
                        logger.info(
                            "Duplicate article filtered out",
                            article_id=article.filtered_article.raw_article.id,
                            similarity_score=duplicate_result.similarity_score
                        )
                
                except Exception as e:
                    logger.error(
                        "Error processing article for duplicates/context",
                        article_id=article.filtered_article.raw_article.id,
                        error=str(e)
                    )
                    continue
            
            processing_time = time.time() - start_time
            
            # Log processing
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="check_duplicates_context",
                event_type="info",
                message=f"Processed {len(deduplicated_articles)} articles, removed {duplicate_count} duplicates, found {update_count} updates",
                data={
                    "input_articles": len(summarized_articles),
                    "output_articles": len(deduplicated_articles),
                    "duplicates_removed": duplicate_count,
                    "updates_found": update_count,
                    "duplicate_rate": duplicate_count / len(summarized_articles) if summarized_articles else 0
                },
                duration_seconds=processing_time
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
    
    async def process_single_article_parallel(self, article: SummarizedArticle, past_articles: List[SummarizedArticle]) -> Dict:
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
                    context_task = self.context_analyzer.analyze_context(
                        current_article=article,
                        max_similar_articles=5,
                        similarity_threshold=0.7
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
    
    async def check_duplicates_node_parallel(self, state: Dict) -> Dict:
        """
        Parallel version of check_duplicates_node with significant performance improvements.
        Processes articles in parallel batches with concurrent LLM operations.
        """
        logger.info("Starting parallel duplicate checking and context analysis")
        start_time = time.time()
        
        try:
            config = state["config"]
            summarized_articles = state["summarized_articles"]
            
            if not summarized_articles:
                logger.warning("No summarized articles to check for duplicates")
                return {
                    **state,
                    "deduplicated_articles": [],
                    "status": "no_articles_to_deduplicate"
                }
            
            # Initialize context analyzer if needed
            if self.context_analyzer is None:
                # Initialize embedding manager first if needed
                if self.embedding_manager is None:
                    self.embedding_manager = EmbeddingManager()
                
                self.context_analyzer = ContextAnalyzer(
                    embedding_manager=self.embedding_manager,
                    llm_router=self.llm_router
                )
            
            # Multi-source consolidation (unchanged - already optimized)
            logger.info(f"Performing multi-source consolidation on {len(summarized_articles)} articles")
            # consolidate_similar_articles は同期関数なので await 不要
            consolidated_articles = consolidate_similar_articles(
                summarized_articles,
                similarity_threshold=config.duplicate_similarity_threshold,
            )
            logger.info(f"After consolidation: {len(consolidated_articles)} articles remain")
            
            # Parallel processing setup
            deduplicated_articles = []
            duplicate_count = 0
            update_count = 0
            
            # Adaptive batch sizing based on article count for optimal performance
            article_count = len(consolidated_articles)
            if article_count <= 5:
                batch_size = min(PERFORMANCE['max_concurrent_llm'], article_count)
            elif article_count <= 15:
                batch_size = max(4, min(PERFORMANCE['max_concurrent_llm'] - 2, article_count // 2))
            else:
                batch_size = max(2, min(PERFORMANCE['max_concurrent_llm'] - 4, article_count // 4))
            
            logger.info(f"Using adaptive batch size: {batch_size} for {article_count} articles")
            semaphore = asyncio.Semaphore(batch_size)
            
            async def process_with_semaphore(article):
                async with semaphore:
                    return await self.process_single_article_parallel(
                        article, [p.summarized_article for p in deduplicated_articles]
                    )
            
            # Create tasks for all articles
            tasks = [process_with_semaphore(article) for article in consolidated_articles]
            
            # Execute in parallel with progress tracking
            logger.info(f"Processing {len(tasks)} articles in parallel (max {batch_size} concurrent)")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and build final articles list
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Parallel processing exception: {result}")
                    continue
                
                if not result.get('success', False):
                    logger.warning(f"Article processing failed: {result.get('error', 'Unknown error')}")
                    continue
                
                article = result['article']
                duplicate_result = result['duplicate_result']
                context_analysis = result['context_analysis']
                japanese_title = result['japanese_title']
                
                # Handle duplicate check results
                if duplicate_result and duplicate_result.is_duplicate:
                    duplicate_count += 1
                    logger.info(f"Article skipped as duplicate: {article.filtered_article.raw_article.id}")
                    continue
                
                # Enhanced context analysis with multi-source summary generation
                is_update = False
                final_summary = ' '.join(article.summary.summary_points)
                
                if context_analysis:
                    if context_analysis.decision == "SKIP":
                        duplicate_count += 1
                        logger.info(f"Article skipped by context analysis: {article.filtered_article.raw_article.id}")
                        continue
                    elif context_analysis.decision == "UPDATE":
                        is_update = True
                        update_count += 1
                        
                        # PRD準拠: 続報記事に🆙絵文字を追加 (F-16: 続報記事の可視化)
                        current_title = article.filtered_article.raw_article.title
                        if not current_title.startswith('🆙'):
                            article.filtered_article.raw_article.title = f"🆙 {current_title}"
                            logger.info(
                                "Added 🆙 emoji to UPDATE article title",
                                article_id=article.filtered_article.raw_article.id,
                                updated_title=article.filtered_article.raw_article.title
                            )
                        
                        # Generate enhanced contextual update summary
                        try:
                            enhanced_summary_points = await self._generate_contextual_update_summary(
                                article, context_analysis
                            )
                            
                            if enhanced_summary_points:
                                # Update the article's summary with enhanced context
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
                                final_summary = ' '.join(enhanced_summary_points)
                                
                                logger.info(
                                    "Enhanced UPDATE article with past context",
                                    article_id=article.filtered_article.raw_article.id,
                                    context_refs=len(context_analysis.references)
                                )
                            elif context_analysis.contextual_summary:
                                # Fallback to context analyzer's summary
                                final_summary = [context_analysis.contextual_summary]
                                
                        except Exception as context_error:
                            logger.warning(
                                "Failed to generate enhanced contextual summary, using fallback",
                                article_id=article.filtered_article.raw_article.id,
                                error=str(context_error)
                            )
                            if context_analysis.contextual_summary:
                                final_summary = [context_analysis.contextual_summary]
                        
                        logger.info(f"Article marked as update: {article.filtered_article.raw_article.id}")
                
                # Handle Japanese title with fallback
                if not japanese_title:
                    # Skip title generation in workflow, let NewsletterGenerator handle it
                    japanese_title = None  # Will be generated later in NewsletterGenerator
                
                # Create ProcessedArticle
                processed_article = ProcessedArticle(
                    summarized_article=article,
                    duplicate_check=duplicate_result,
                    context_analysis=context_analysis,
                    final_summary=final_summary,
                    japanese_title=japanese_title,
                    is_update=is_update,
                    citations=[]  # Will be filled later
                )
                
                deduplicated_articles.append(processed_article)
            
            processing_time = time.time() - start_time
            
            # Log processing results
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="check_duplicates_context_parallel",
                event_type="info",
                message=f"Parallel processed {len(deduplicated_articles)} articles, removed {duplicate_count} duplicates, found {update_count} updates",
                data={
                    "input_articles": len(summarized_articles),
                    "output_articles": len(deduplicated_articles),
                    "duplicates_removed": duplicate_count,
                    "updates_found": update_count,
                    "duplicate_rate": duplicate_count / len(summarized_articles) if summarized_articles else 0,
                    "parallel_processing_time": processing_time,
                    "articles_per_second": len(consolidated_articles) / processing_time if processing_time > 0 else 0
                },
                duration_seconds=processing_time
            )
            
            logger.info(
                f"Parallel processing completed in {processing_time:.2f}s "
                f"({len(consolidated_articles) / processing_time:.1f} articles/sec)"
            )
            
            return {
                **state,
                "deduplicated_articles": deduplicated_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "duplicates_and_context_checked_parallel"
            }
            
        except Exception as e:
            logger.error("Parallel check duplicates and context node failed", error=str(e))
            
            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="check_duplicates_context_parallel",
                event_type="error",
                message=f"Failed to check duplicates and context in parallel: {str(e)}",
                duration_seconds=time.time() - start_time
            )
            
            return {
                **state,
                "deduplicated_articles": [],
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "deduplication_context_parallel_failed"
            }
    
    async def cluster_topics_node(self, state: Dict) -> Dict:
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
            from src.utils.citation_generator import enhance_articles_with_citations_parallel, CitationGenerator
            
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
                    for j in range(target_count):
                        if citation_index < len(unique_citations):
                            article_citations.append(unique_citations[citation_index])
                            citation_index += 1
                        else:
                            break
                    
                    # 引用がない場合は最低保証引用を生成
                    if not article_citations:
                        from src.models.schemas import Citation
                        from src.constants.mappings import format_source_name
                        
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
    
    async def generate_newsletter_node(self, state: Dict) -> Dict:
        """Generate final Markdown newsletter."""
        
        logger.info("Starting newsletter generation node")
        start_time = time.time()
        
        try:
            config = state["config"]
            clustered_articles = state["clustered_articles"]
            
            if not clustered_articles:
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
                "articles_final": len(clustered_articles),
                "processing_time_seconds": sum(
                    log.duration_seconds or 0 
                    for log in state["processing_logs"]
                ),
                "success_rate": (
                    len(clustered_articles) / len(state.get("raw_articles", [1])) * 100
                )
            }
            
            # Generate newsletter using NewsletterGenerator class directly
            # This ensures all processing including multi-source consolidation is executed
            from src.utils.newsletter_generator import NewsletterGenerator
            
            generator = NewsletterGenerator(templates_dir="src/templates")
            newsletter_output = await generator.generate_newsletter(
                articles=clustered_articles,
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
                message=f"Generated newsletter with {len(clustered_articles)} articles",
                data={
                    "articles_count": len(clustered_articles),
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
                        articles=clustered_articles,
                        newsletter_content=newsletter_output.metadata.get("output_file", ""),
                        processing_logs=state["processing_logs"] + [log_entry],
                        metadata=newsletter_output.metadata,
                        edition=config.edition
                    )
                except Exception as e:
                    logger.warning("Failed to save to Supabase", error=str(e))
            
            return {
                **state,
                "final_newsletter": newsletter_output.metadata.get("output_file", ""),
                "output_file": newsletter_output.metadata.get("output_file"),
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "newsletter_generated"
            }
            
        except Exception as e:
            logger.error("Generate newsletter node failed", error=str(e))
            
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
    async def publish_to_quaily_node(self, state: Dict) -> Dict:
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

    async def _generate_contextual_update_summary(
        self,
        article: SummarizedArticle,
        context_analysis: 'ContextAnalysisResult'
    ) -> Optional[List[str]]:
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
    
    def _validate_prd_compliance(self, articles: List[ProcessedArticle]) -> Dict[str, any]:
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


def create_newsletter_workflow() -> StateGraph:
    """Create and compile the newsletter generation workflow."""
    
    workflow_instance = NewsletterWorkflow()
    
    # Create state graph
    workflow = StateGraph(dict)  # Use dict instead of NewsletterState for LangGraph compatibility
    
    # Add nodes (using parallel version for performance)
    workflow.add_node("fetch_sources", workflow_instance.fetch_sources_node)
    workflow.add_node("filter_ai_content", workflow_instance.filter_ai_content_node)
    workflow.add_node("generate_summaries", workflow_instance.generate_summaries_node)
    workflow.add_node("check_duplicates", workflow_instance.check_duplicates_node_parallel)
    workflow.add_node("cluster_topics", workflow_instance.cluster_topics_node)
    workflow.add_node("generate_newsletter", workflow_instance.generate_newsletter_node)
    workflow.add_node("publish_to_quaily", workflow_instance.publish_to_quaily_node)
    
    # Add edges (sequential flow)
    workflow.add_edge("fetch_sources", "filter_ai_content")
    workflow.add_edge("filter_ai_content", "generate_summaries")
    workflow.add_edge("generate_summaries", "check_duplicates")
    workflow.add_edge("check_duplicates", "cluster_topics")
    workflow.add_edge("cluster_topics", "generate_newsletter")
    workflow.add_edge("generate_newsletter", "publish_to_quaily")
    workflow.add_edge("publish_to_quaily", END)
    
    # Set entry point
    workflow.set_entry_point("fetch_sources")
    
    return workflow.compile()