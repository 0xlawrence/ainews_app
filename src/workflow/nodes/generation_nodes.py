"""
Generation workflow nodes for image processing and newsletter creation.

This module contains the generation phase nodes of the newsletter workflow:
- Image processing and optimization
- Newsletter content generation
- Quality checking and validation
"""

import asyncio
import time
from typing import List, Optional

from src.models.schemas import ProcessedArticle, ProcessingLog
from src.utils.image_processor import ImageProcessor
from src.utils.logger import setup_logging
from src.utils.newsletter_generator import NewsletterGenerator
from src.utils.supabase_client import save_newsletter_to_supabase

logger = setup_logging()


class GenerationNodes:
    """Generation workflow nodes for image processing and newsletter creation."""
    
    def __init__(self):
        """Initialize generation nodes."""
        from src.config.settings import get_settings
        self.settings = get_settings()
        self.image_processor = None  # Initialized lazily
    
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
            max_concurrent = min(self.settings.workflow.max_concurrent_images, len(clustered_articles))  # Limit concurrency
            
            # Process articles in batches to avoid overwhelming the system
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
                logger.warning("No articles to generate newsletter")
                
                # Create empty newsletter
                empty_newsletter = "# AI NEWS TLDR\n\n本日は注目すべきAI関連ニュースがございませんでした。\n"
                
                return {
                    **state,
                    "final_newsletter": empty_newsletter,
                    "status": "empty_newsletter_generated"
                }
            
            # Prepare processing summary
            processing_summary = self._prepare_processing_summary(state, articles)
            
            # Generate newsletter using NewsletterGenerator class
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
            quality_logs = await self._run_quality_check(config, newsletter_output)
            
            # Save to Supabase if not dry run
            if not config.dry_run:
                await self._save_to_supabase(config, articles, newsletter_output, state["processing_logs"] + [log_entry] + quality_logs)
            
            # Cleanup resources to prevent memory leaks
            self._cleanup_generation_resources()
            
            return {
                **state,
                "final_newsletter": newsletter_output.metadata.get("output_file", ""),
                "output_file": newsletter_output.metadata.get("output_file"),
                "processing_logs": state["processing_logs"] + [log_entry] + quality_logs,
                "status": "newsletter_generated"
            }
            
        except Exception as e:
            logger.error("Generate newsletter node failed", error=str(e))
            
            # Cleanup resources even on failure
            self._cleanup_generation_resources()
            
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
    
    # Private helper methods
    
    def _prepare_processing_summary(self, state: dict, articles: List[ProcessedArticle]) -> dict:
        """Prepare processing summary for newsletter generation."""
        return {
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
    
    async def _run_quality_check(self, config, newsletter_output) -> List[ProcessingLog]:
        """Run comprehensive quality check on generated newsletter."""
        quality_logs = []
        
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
            
            # Create quality log entry
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
                duration_seconds=0.1  # Quality check is usually fast
            )
            
            quality_logs.append(quality_log)
            
        except Exception as e:
            logger.warning(f"Quality check failed: {e}")
            # Create warning log for failed quality check
            warning_log = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="quality_check",
                event_type="warning",
                message=f"Quality check failed: {str(e)}",
                duration_seconds=0.1
            )
            quality_logs.append(warning_log)
        
        return quality_logs
    
    async def _save_to_supabase(self, config, articles: List[ProcessedArticle], newsletter_output, processing_logs: List[ProcessingLog]):
        """Save newsletter to Supabase."""
        try:
            await save_newsletter_to_supabase(
                processing_id=config.processing_id,
                articles=articles,
                newsletter_content=newsletter_output.metadata.get("output_file", ""),
                processing_logs=processing_logs,
                metadata=newsletter_output.metadata,
                edition=config.edition
            )
            logger.info("Successfully saved newsletter to Supabase")
        except Exception as e:
            logger.warning("Failed to save to Supabase", error=str(e))
    
    def _cleanup_generation_resources(self):
        """Clean up generation resources to prevent memory leaks."""
        try:
            # Cleanup ImageProcessor if it exists
            if hasattr(self, 'image_processor') and self.image_processor:
                # Reset image processor state if it has any
                if hasattr(self.image_processor, '_cache'):
                    self.image_processor._cache.clear()
                logger.info("ImageProcessor resources cleaned up")
            
            logger.info("Generation resources cleanup completed")
            
        except Exception as e:
            logger.warning(f"Error during generation cleanup: {e}")