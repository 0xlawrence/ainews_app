"""
Content processing nodes for newsletter workflow.

This module contains nodes responsible for content fetching, filtering, and summarization.
"""

import asyncio
import time
from datetime import datetime
from typing import Union

from src.config.settings import get_settings
from src.llm.llm_router import LLMRouter
from src.models.schemas import (
    ProcessedArticle,
    ProcessingLog,
    SummarizedArticle,
)
from src.utils.content_fetcher import fetch_content_from_sources
from src.utils.content_validator import validate_article_content
from src.utils.text_processing import clean_llm_response
from src.utils.logger import setup_logging

logger = setup_logging()


class ContentProcessingNodes:
    """Content processing workflow nodes."""

    def __init__(self):
        """Initialize content processing nodes."""
        self.settings = get_settings()
        self.llm_router = LLMRouter()

    def _sort_articles_by_priority(self, articles):
        """Sort articles by source priority and publication date."""
        def get_priority(article):
            source_priority = getattr(article, 'source_priority', self.settings.workflow.default_source_priority)
            return (source_priority, -article.published_date.timestamp() if article.published_date else 0)
        
        return sorted(articles, key=get_priority)

    async def fetch_sources_node(self, state: dict) -> dict:
        """Fetch articles from RSS and YouTube sources."""

        logger.info("Starting fetch sources node")
        start_time = time.time()

        try:
            config = state["config"]

            # Calculate dynamic hours_lookback based on target_date
            hours_lookback = self.settings.workflow.default_hours_lookback
            if getattr(config, 'target_date', None):
                today = datetime.now().date()
                delta_days = (today - config.target_date).days
                if delta_days > 0:
                    # For past dates, expand lookback to ensure we capture content
                    hours_lookback = max(self.settings.workflow.default_hours_lookback, (delta_days + 1) * self.settings.workflow.default_hours_lookback)
                    logger.info(f"Target date is {delta_days} days ago, using hours_lookback={hours_lookback}")

            # Fetch from all sources
            raw_articles = await fetch_content_from_sources(
                sources=config.sources,
                max_items_per_source=max(self.settings.workflow.min_items_per_source, config.max_items // len(config.sources)),
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

            # Filter articles with simple keyword-based filtering (PRD F-2 compliance)
            # Simplified back to basic filtering as per original requirements
            from src.utils.ai_filter import filter_ai_content
            filtered_articles = filter_ai_content(
                articles=raw_articles,
                relevance_threshold=config.ai_relevance_threshold,
                min_articles_target=getattr(config, 'min_articles_target', self.settings.processing.min_articles_target),
                dynamic_threshold=False  # Disable dynamic adjustment for consistency
            )

            logger.info(f"Simple keyword filtering: {len(raw_articles)} → {len(filtered_articles)} articles passed")
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

            # Check if batch processing is enabled
            if self.settings.processing.enable_llm_batch_processing:
                logger.info("Using LLM batch processing for summary generation")
                
                # Prepare articles for batch processing
                batch_articles = []
                for article in filtered_articles:
                    raw_article = article.raw_article
                    if validate_article_content(raw_article.content):
                        batch_articles.append({
                            'title': raw_article.title,
                            'content': raw_article.content,
                            'url': str(raw_article.url),
                            'source_name': raw_article.source_id,
                            'original_article': article  # Keep reference to original
                        })
                    else:
                        logger.warning(f"Skipping article with invalid content: {raw_article.title[:50]}")
                
                # Process articles in batches
                batch_results = await self.llm_router.generate_summaries_batch(
                    articles=batch_articles,
                    batch_size=self.settings.processing.llm_batch_size,
                    max_concurrent_batches=self.settings.processing.max_concurrent_llm_batches
                )
                
                # Convert batch results to SummarizedArticle objects
                summarized_articles = []
                failed_summaries = 0
                
                for i, (batch_article, summary_result) in enumerate(zip(batch_articles, batch_results)):
                    if summary_result:
                        try:
                            # Validate and optionally regenerate on failure
                            validated = await self._validate_or_regenerate_summary(
                                raw_article=batch_article,
                                summary=summary_result
                            )
                            if validated:
                                summarized_article = SummarizedArticle(
                                    filtered_article=batch_article['original_article'],
                                    summary=validated,
                                    processing_time_seconds=validated.processing_time_seconds or 0.5,
                                    retry_count=validated.retry_count or 0,
                                    fallback_used=bool(validated.fallback_used)
                                )
                                summarized_articles.append(summarized_article)
                            else:
                                failed_summaries += 1
                                logger.warning(f"Validation/regeneration failed for article: {batch_article['title'][:50]}")
                        except Exception as e:
                            logger.error(f"Failed to create SummarizedArticle for batch result {i}: {e}")
                            failed_summaries += 1
                    else:
                        failed_summaries += 1
                        logger.warning(f"Batch processing failed for article: {batch_article['title'][:50]}")
                
            else:
                logger.info("Using individual processing for summary generation")
                
                # Generate summaries for all articles (original individual processing)
                summarized_articles = []
                failed_summaries = 0

                # Create semaphore for concurrent processing
                semaphore = asyncio.Semaphore(self.settings.processing.async_concurrency_limit)

                async def process_article_with_semaphore(article):
                    async with semaphore:
                        try:
                            # Get content from raw_article
                            raw_article = article.raw_article
                            
                            # Validate article content
                            if not validate_article_content(raw_article.content):
                                logger.warning(f"Skipping article with invalid content: {raw_article.title[:50]}")
                                return None

                            # Generate summary using LLM Router
                            summary_result = await self.llm_router.generate_summary(
                                article_title=raw_article.title,
                                article_content=raw_article.content,
                                article_url=raw_article.url,
                                source_name=raw_article.source_id
                            )

                            if summary_result and summary_result.summary:
                                validated = await self._validate_or_regenerate_summary(
                                    raw_article={
                                        'title': raw_article.title,
                                        'content': raw_article.content,
                                        'url': str(raw_article.url),
                                        'source_name': raw_article.source_id,
                                    },
                                    summary=summary_result.summary
                                )
                                if validated:
                                    return SummarizedArticle(
                                        filtered_article=article,
                                        summary=validated,
                                        processing_time_seconds=validated.processing_time_seconds or 0.5,
                                        retry_count=validated.retry_count or 0,
                                        fallback_used=bool(validated.fallback_used)
                                    )
                                else:
                                    logger.warning(f"Validation/regeneration failed for: {raw_article.title[:50]}")
                                    return None
                            else:
                                logger.warning(f"Failed to generate summary for: {raw_article.title[:50]}")
                                return None

                        except Exception as e:
                            logger.error(f"Error processing article {raw_article.title[:50]}: {e}")
                            return None

                # Process articles concurrently
                tasks = [process_article_with_semaphore(article) for article in filtered_articles]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Collect successful summaries
                for result in results:
                    if isinstance(result, SummarizedArticle):
                        summarized_articles.append(result)
                    elif result is None:
                        failed_summaries += 1
                    else:
                        logger.error(f"Unexpected result type: {type(result)}")
                        failed_summaries += 1

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

    async def _validate_or_regenerate_summary(
        self,
        raw_article: dict,
        summary: "SummaryOutput"
    ) -> "SummaryOutput | None":
        """Validate summary; clean meta; regenerate once if invalid.

        Args:
            raw_article: {title, content, url, source_name}
            summary: SummaryOutput

        Returns:
            Valid SummaryOutput or None if irrecoverable
        """
        try:
            from src.models.schemas import SummaryOutput

            # 1) Validate current summary
            result = validate_article_content(summary.summary_points, title=raw_article.get('title'), production_mode=True)
            if result.is_valid:
                return summary

            # 2) Clean meta artifacts then re-validate
            cleaned_points = [clean_llm_response(p) for p in summary.summary_points]
            cleaned_summary = SummaryOutput(
                summary_points=cleaned_points,
                confidence_score=summary.confidence_score,
                source_reliability=summary.source_reliability,
                model_used=summary.model_used,
                token_count=summary.token_count,
                processing_time_seconds=summary.processing_time_seconds,
                retry_count=summary.retry_count,
                fallback_used=summary.fallback_used,
                total_tokens=getattr(summary, 'total_tokens', None)
            )
            result2 = validate_article_content(cleaned_summary.summary_points, title=raw_article.get('title'), production_mode=True)
            if result2.is_valid:
                return cleaned_summary

            # 3) Regenerate once with individual summary API
            regenerated = await self.llm_router.generate_summary(
                article_title=raw_article['title'],
                article_content=raw_article['content'],
                article_url=raw_article['url'],
                source_name=raw_article['source_name'],
                max_retries=2
            )
            # Revalidate regenerated
            result3 = validate_article_content(regenerated.summary_points, title=raw_article.get('title'), production_mode=True)
            if result3.is_valid:
                return regenerated

            return None
        except Exception as e:
            logger.warning(f"Validation/regeneration failed with exception: {e}")
            return None