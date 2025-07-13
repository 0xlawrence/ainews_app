"""
Integrated image processor that combines fetching and uploading functionality.

This module provides a high-level interface for getting images from URLs
and uploading them to Supabase storage for newsletter embedding.
"""

import logging
from pathlib import Path
from typing import Any

from src.utils.image_fetcher import ImageFetcher, is_youtube_url
from src.utils.image_uploader import ImageUploader

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Integrated image processing pipeline for newsletter generation."""

    def __init__(self):
        """Initialize the image processor with fetcher and uploader."""
        try:
            self.fetcher = ImageFetcher()
            self.uploader = ImageUploader()
            logger.info("ImageProcessor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ImageProcessor: {e}")
            raise

    def process_article_image(
        self,
        url: str,
        article_id: str,
        max_width: int = 600,
        max_size_kb: int = 500,
        cleanup_temp: bool = True
    ) -> dict[str, Any] | None:
        """
        Complete pipeline: fetch image from URL and upload to Supabase.

        Args:
            url: Article or video URL
            article_id: Unique article identifier
            max_width: Maximum image width in pixels
            max_size_kb: Maximum file size in KB
            cleanup_temp: Whether to clean up temporary files

        Returns:
            Dict with image info if successful:
            {
                'image_url': 'https://supabase.../image.jpg',
                'source_type': 'youtube'|'ogp'|'content',
                'original_url': 'original_image_url',
                'dimensions': {'width': 600, 'height': 400},
                'file_size': 125000  # bytes
            }
            Or None if failed
        """
        temp_image_path = None

        try:
            logger.info(f"Processing image for article {article_id}: {url[:100]}...")

            # Step 1: Fetch image from URL
            temp_image_path = self.fetcher.get_image_from_url(url, article_id)

            if not temp_image_path:
                logger.warning(f"No image could be fetched for article {article_id}")
                return None

            if not temp_image_path.exists():
                logger.error(f"Fetched image file does not exist: {temp_image_path}")
                return None

            # Step 2: Upload optimized image to Supabase
            public_url = self.uploader.upload_image(
                image_path=temp_image_path,
                article_id=article_id,
                max_size_kb=max_size_kb,
                max_width=max_width
            )

            if not public_url:
                logger.error(f"Failed to upload image for article {article_id}")
                return None

            # Step 3: Get image metadata
            metadata = self._get_image_metadata(temp_image_path, url)

            result = {
                'image_url': public_url,
                'source_type': metadata['source_type'],
                'original_url': url,
                'dimensions': metadata['dimensions'],
                'file_size': metadata['file_size']
            }

            logger.info(f"Successfully processed image for article {article_id}: {public_url}")
            return result

        except Exception as e:
            logger.error(f"Image processing failed for article {article_id}: {e}")
            return None

        finally:
            # Step 4: Cleanup temporary file
            if cleanup_temp and temp_image_path and temp_image_path.exists():
                try:
                    temp_image_path.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_image_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_image_path}: {e}")

    def _get_image_metadata(self, image_path: Path, source_url: str) -> dict[str, Any]:
        """Extract metadata from the processed image."""
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                # Determine source type
                source_type = 'unknown'
                if is_youtube_url(source_url):
                    source_type = 'youtube'
                elif 'og:image' in str(image_path) or 'ogp' in str(image_path):
                    source_type = 'ogp'
                elif 'content' in str(image_path):
                    source_type = 'content'

                return {
                    'dimensions': {
                        'width': img.width,
                        'height': img.height
                    },
                    'file_size': image_path.stat().st_size,
                    'source_type': source_type,
                    'format': img.format or 'UNKNOWN'
                }

        except Exception as e:
            logger.warning(f"Failed to extract image metadata: {e}")
            return {
                'dimensions': {'width': 0, 'height': 0},
                'file_size': 0,
                'source_type': 'unknown',
                'format': 'UNKNOWN'
            }

    def process_multiple_articles(
        self,
        articles: list,
        max_concurrent: int = 5,
        timeout_per_article: int = 30
    ) -> dict[str, dict[str, Any] | None]:
        """
        Process images for multiple articles (for workflow integration).

        Args:
            articles: List of article objects with 'url' and 'id' attributes
            max_concurrent: Maximum concurrent downloads
            timeout_per_article: Timeout per article in seconds

        Returns:
            Dict mapping article_id to image info or None
        """
        import concurrent.futures
        import time

        results = {}

        def process_single_article(article) -> tuple:
            """Process a single article and return (article_id, result)."""
            try:
                article_id = getattr(article, 'id', str(hash(article)))
                article_url = getattr(article, 'url', '')

                if not article_url:
                    logger.warning(f"No URL found for article {article_id}")
                    return (article_id, None)

                start_time = time.time()
                result = self.process_article_image(article_url, article_id)

                processing_time = time.time() - start_time
                logger.debug(f"Article {article_id} processed in {processing_time:.2f}s")

                return (article_id, result)

            except Exception as e:
                logger.error(f"Failed to process article {getattr(article, 'id', 'unknown')}: {e}")
                return (getattr(article, 'id', 'unknown'), None)

        # Process articles concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all tasks
            future_to_article = {
                executor.submit(process_single_article, article): article
                for article in articles
            }

            # Collect results with timeout
            for future in concurrent.futures.as_completed(future_to_article, timeout=timeout_per_article * len(articles)):
                try:
                    article_id, result = future.result(timeout=timeout_per_article)
                    results[article_id] = result
                except concurrent.futures.TimeoutError:
                    article = future_to_article[future]
                    article_id = getattr(article, 'id', 'unknown')
                    logger.warning(f"Timeout processing article {article_id}")
                    results[article_id] = None
                except Exception as e:
                    article = future_to_article[future]
                    article_id = getattr(article, 'id', 'unknown')
                    logger.error(f"Error processing article {article_id}: {e}")
                    results[article_id] = None

        success_count = sum(1 for r in results.values() if r is not None)
        logger.info(f"Processed images for {success_count}/{len(articles)} articles")

        return results

    def test_integration(self) -> bool:
        """
        Test the complete integration (fetch + upload pipeline).

        Returns:
            True if test successful, False otherwise
        """
        try:
            # Test with a reliable test URL (YouTube)
            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - reliable test video
            test_article_id = "test_integration"

            logger.info("Running integration test...")

            # Test the complete pipeline
            result = self.process_article_image(test_url, test_article_id)

            if result and result.get('image_url'):
                logger.info(f"Integration test PASSED: {result['image_url']}")
                logger.info(f"Image details: {result['dimensions']}, {result['file_size']} bytes")
                return True
            else:
                logger.error("Integration test FAILED: No image result")
                return False

        except Exception as e:
            logger.error(f"Integration test FAILED with exception: {e}")
            return False

    def cleanup_temp_files(self):
        """Clean up temporary files from both fetcher and any local temp files."""
        try:
            self.fetcher.cleanup_temp_files()
        except Exception as e:
            logger.warning(f"Failed to cleanup fetcher temp files: {e}")


# Convenience functions for easy integration
def process_article_image(url: str, article_id: str) -> dict[str, Any] | None:
    """
    Convenience function for processing a single article image.

    Args:
        url: Article or video URL
        article_id: Unique article identifier

    Returns:
        Image info dict if successful, None if failed
    """
    try:
        processor = ImageProcessor()
        return processor.process_article_image(url, article_id)
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        return None


def test_image_processing() -> bool:
    """
    Test the complete image processing pipeline.

    Returns:
        True if test successful, False otherwise
    """
    try:
        processor = ImageProcessor()
        return processor.test_integration()
    except Exception as e:
        logger.error(f"Image processing test failed: {e}")
        return False
