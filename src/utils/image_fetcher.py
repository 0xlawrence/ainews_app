"""
Image fetcher utility for OGP and YouTube thumbnail extraction.

This module handles fetching images from article URLs and YouTube videos,
with intelligent fallback mechanisms and optimization for newsletter embedding.
"""

import logging
import re
import tempfile
import time
from pathlib import Path

# HTTP requests
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# HTML parsing for OGP extraction
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# Image processing
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ImageFetcher:
    """Fetches and processes images from article URLs and YouTube videos."""

    def __init__(self):
        """Initialize the image fetcher with configuration."""
        if not HAS_REQUESTS:
            raise ImportError("requests package is required for image fetching")

        if not HAS_BS4:
            raise ImportError("beautifulsoup4 package is required for OGP parsing")

        if not HAS_PIL:
            raise ImportError("Pillow package is required for image processing")

        self.settings = get_settings()
        self.session = self._create_session()

        # Image processing settings
        self.max_image_size_mb = 10  # Maximum download size
        self.timeout = 30  # Request timeout in seconds
        self.max_redirects = 5  # Maximum redirects to follow

        logger.info("ImageFetcher initialized")

    def _create_session(self) -> requests.Session:
        """Create a configured requests session."""
        session = requests.Session()

        # Set headers to appear as a real browser
        session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        return session

    def get_image_from_url(
        self,
        url: str,
        article_id: str | None = None
    ) -> Path | None:
        """
        Get the best image for a given URL.

        Tries multiple strategies:
        1. YouTube thumbnail (if YouTube URL)
        2. OGP image extraction
        3. First suitable image on page

        Args:
            url: The article/video URL
            article_id: Optional article identifier for caching

        Returns:
            Path to downloaded and optimized image file, or None if failed
        """
        try:
            logger.info(f"Fetching image for URL: {url[:100]}...")

            # Strategy 1: YouTube thumbnail
            if self._is_youtube_url(url):
                image_path = self._get_youtube_thumbnail(url, article_id)
                if image_path:
                    logger.info(f"Successfully fetched YouTube thumbnail: {image_path}")
                    return image_path
                else:
                    logger.warning(f"YouTube thumbnail fetch failed for: {url}")

            # Strategy 2: OGP image extraction
            image_path = self._get_ogp_image(url, article_id)
            if image_path:
                logger.info(f"Successfully fetched OGP image: {image_path}")
                return image_path

            # Strategy 3: First suitable image on page
            image_path = self._get_first_image_from_page(url, article_id)
            if image_path:
                logger.info(f"Successfully fetched first page image: {image_path}")
                return image_path

            logger.warning(f"No suitable image found for URL: {url}")
            return None

        except Exception as e:
            logger.error(f"Image fetching failed for {url}: {e}")
            return None

    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video."""
        youtube_patterns = [
            r'youtube\.com/watch',
            r'youtu\.be/',
            r'youtube\.com/embed/',
            r'youtube\.com/v/',
        ]

        return any(re.search(pattern, url, re.IGNORECASE) for pattern in youtube_patterns)

    def _extract_youtube_video_id(self, url: str) -> str | None:
        """Extract YouTube video ID from various URL formats."""
        patterns = [
            r'youtube\.com/watch\?v=([^&]+)',
            r'youtu\.be/([^?]+)',
            r'youtube\.com/embed/([^?]+)',
            r'youtube\.com/v/([^?]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _get_youtube_thumbnail(
        self,
        url: str,
        article_id: str | None = None
    ) -> Path | None:
        """
        Get YouTube video thumbnail.

        Tries multiple quality levels:
        1. maxresdefault.jpg (1280x720)
        2. sddefault.jpg (640x480)
        3. hqdefault.jpg (480x360)
        4. mqdefault.jpg (320x180)
        """
        video_id = self._extract_youtube_video_id(url)
        if not video_id:
            logger.warning(f"Could not extract video ID from YouTube URL: {url}")
            return None

        # YouTube thumbnail URL patterns (highest to lowest quality)
        thumbnail_qualities = [
            'maxresdefault',  # 1280x720
            'sddefault',      # 640x480
            'hqdefault',      # 480x360
            'mqdefault',      # 320x180
        ]

        for quality in thumbnail_qualities:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"

            try:
                logger.debug(f"Trying YouTube thumbnail: {thumbnail_url}")

                # Download the thumbnail
                response = self.session.get(
                    thumbnail_url,
                    timeout=self.timeout,
                    stream=True
                )

                if response.status_code == 200 and len(response.content) > 1000:  # Ensure it's not a placeholder
                    # Save to temporary file
                    temp_file = self._save_to_temp_file(
                        response.content,
                        f"youtube_{video_id}_{quality}",
                        article_id
                    )

                    if temp_file and self._validate_image(temp_file):
                        logger.info(f"YouTube thumbnail downloaded: {quality} quality")
                        return temp_file

            except Exception as e:
                logger.debug(f"Failed to download {quality} thumbnail: {e}")
                continue

        logger.warning(f"All YouTube thumbnail qualities failed for video: {video_id}")
        return None

    def _get_ogp_image(
        self,
        url: str,
        article_id: str | None = None
    ) -> Path | None:
        """Extract and download OGP (Open Graph Protocol) image from URL."""
        try:
            # Fetch the webpage
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for OGP image tags in order of preference
            ogp_selectors = [
                'meta[property="og:image"]',
                'meta[property="og:image:url"]',
                'meta[name="og:image"]',
                'meta[property="twitter:image"]',
                'meta[name="twitter:image"]',
                'meta[property="twitter:image:src"]',
            ]

            image_url = None
            for selector in ogp_selectors:
                tag = soup.select_one(selector)
                if tag:
                    image_url = tag.get('content') or tag.get('value')
                    if image_url:
                        logger.debug(f"Found OGP image with selector: {selector}")
                        break

            if not image_url:
                logger.debug(f"No OGP image found for: {url}")
                return None

            # Resolve relative URLs
            image_url = self._resolve_url(image_url, url)

            # Download the image
            return self._download_image(image_url, f"ogp_{hash(url)}", article_id)

        except Exception as e:
            logger.debug(f"OGP image extraction failed for {url}: {e}")
            return None

    def _get_first_image_from_page(
        self,
        url: str,
        article_id: str | None = None
    ) -> Path | None:
        """Find and download the first suitable image from the webpage."""
        try:
            # Fetch the webpage
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for images, prioritizing those likely to be content images
            img_selectors = [
                'article img',  # Images within article content
                '.content img',  # Images within content sections
                '.post img',     # Images within post content
                'main img',      # Images within main content
                'img[src]',      # Any image with src
            ]

            for selector in img_selectors:
                images = soup.select(selector)

                for img in images:
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy')
                    if not src:
                        continue

                    # Skip small images, icons, and common non-content images
                    if self._is_suitable_content_image(img, src):
                        # Resolve relative URLs
                        image_url = self._resolve_url(src, url)

                        # Try to download
                        image_path = self._download_image(
                            image_url,
                            f"content_{hash(url)}",
                            article_id
                        )

                        if image_path:
                            logger.info("Downloaded first suitable page image")
                            return image_path

            logger.debug(f"No suitable content images found on page: {url}")
            return None

        except Exception as e:
            logger.debug(f"Page image extraction failed for {url}: {e}")
            return None

    def _is_suitable_content_image(self, img_tag, src: str) -> bool:
        """Check if an image is suitable for use as content image."""
        # Skip obviously small images based on attributes
        width = img_tag.get('width')
        height = img_tag.get('height')

        if width and height:
            try:
                w, h = int(width), int(height)
                if w < 200 or h < 150:  # Too small
                    return False
            except (ValueError, TypeError):
                pass

        # Skip common icon and UI elements by URL patterns
        skip_patterns = [
            r'icon',
            r'logo',
            r'avatar',
            r'profile',
            r'thumb',
            r'small',
            r'badge',
            r'button',
            r'arrow',
            r'star',
            r'social',
            r'share',
            r'ads?/',
            r'advertisement',
            r'tracking',
            r'analytics',
            r'pixel',
            r'1x1',
            r'spacer',
        ]

        src_lower = src.lower()
        if any(re.search(pattern, src_lower) for pattern in skip_patterns):
            return False

        # Prefer images with content-related patterns
        prefer_patterns = [
            r'article',
            r'content',
            r'post',
            r'feature',
            r'hero',
            r'banner',
            r'cover',
        ]

        # Check alt text and class for content hints
        alt_text = (img_tag.get('alt') or '').lower()
        class_names = ' '.join(img_tag.get('class', [])).lower()

        context = f"{src_lower} {alt_text} {class_names}"

        # Boost score for content-related terms
        has_content_hint = any(re.search(pattern, context) for pattern in prefer_patterns)

        return True  # Default to suitable, let download validation filter out unsuitable images

    def _resolve_url(self, image_url: str, base_url: str) -> str:
        """Resolve relative URLs to absolute URLs."""
        if image_url.startswith(('http://', 'https://')):
            return image_url

        from urllib.parse import urljoin
        return urljoin(base_url, image_url)

    def _download_image(
        self,
        image_url: str,
        filename_prefix: str,
        article_id: str | None = None
    ) -> Path | None:
        """Download an image from URL to temporary file."""
        try:
            logger.debug(f"Downloading image: {image_url}")

            # Stream download with size limit
            response = self.session.get(
                image_url,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
                logger.debug(f"Invalid content type: {content_type}")
                return None

            # Download with size limit
            max_size = self.max_image_size_mb * 1024 * 1024
            content = b''

            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > max_size:
                    logger.warning(f"Image too large (>{self.max_image_size_mb}MB): {image_url}")
                    return None

            if len(content) < 1000:  # Too small, likely a placeholder
                logger.debug(f"Image too small ({len(content)} bytes): {image_url}")
                return None

            # Save to temporary file
            temp_file = self._save_to_temp_file(content, filename_prefix, article_id)

            if temp_file and self._validate_image(temp_file):
                return temp_file

            return None

        except Exception as e:
            logger.debug(f"Image download failed: {image_url} - {e}")
            return None

    def _save_to_temp_file(
        self,
        content: bytes,
        filename_prefix: str,
        article_id: str | None = None
    ) -> Path | None:
        """Save content to a temporary file."""
        try:
            # Create filename
            timestamp = int(time.time())
            if article_id:
                clean_id = "".join(c for c in article_id if c.isalnum() or c in '-_')[:20]
                filename = f"{filename_prefix}_{timestamp}_{clean_id}.tmp"
            else:
                filename = f"{filename_prefix}_{timestamp}.tmp"

            # Save to temp directory
            temp_dir = Path(tempfile.gettempdir()) / "ainews_images"
            temp_dir.mkdir(exist_ok=True)

            temp_file = temp_dir / filename

            with open(temp_file, 'wb') as f:
                f.write(content)

            logger.debug(f"Saved to temp file: {temp_file}")
            return temp_file

        except Exception as e:
            logger.error(f"Failed to save temp file: {e}")
            return None

    def _validate_image(self, image_path: Path) -> bool:
        """Validate that the file is a proper image."""
        try:
            with Image.open(image_path) as img:
                # Check minimum dimensions
                if img.width < 100 or img.height < 100:
                    logger.debug(f"Image too small: {img.width}x{img.height}")
                    return False

                # Check reasonable aspect ratio (not too narrow/wide)
                aspect_ratio = img.width / img.height
                if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                    logger.debug(f"Unusual aspect ratio: {aspect_ratio}")
                    return False

                # Verify it can be processed
                img.verify()
                return True

        except Exception as e:
            logger.debug(f"Image validation failed: {e}")
            return False

    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up old temporary image files."""
        try:
            temp_dir = Path(tempfile.gettempdir()) / "ainews_images"
            if not temp_dir.exists():
                return

            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            cleaned_count = 0
            for temp_file in temp_dir.glob("*.tmp"):
                try:
                    file_age = current_time - temp_file.stat().st_mtime
                    if file_age > max_age_seconds:
                        temp_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.debug(f"Failed to clean temp file {temp_file}: {e}")

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old temp image files")

        except Exception as e:
            logger.warning(f"Temp file cleanup failed: {e}")


# Convenience functions
def get_image_for_article(url: str, article_id: str | None = None) -> Path | None:
    """
    Convenience function to get the best image for an article URL.

    Args:
        url: Article or video URL
        article_id: Optional article identifier

    Returns:
        Path to downloaded image file, or None if failed
    """
    try:
        fetcher = ImageFetcher()
        return fetcher.get_image_from_url(url, article_id)
    except Exception as e:
        logger.error(f"Image fetching failed: {e}")
        return None


def is_youtube_url(url: str) -> bool:
    """
    Check if a URL is a YouTube video.

    Args:
        url: URL to check

    Returns:
        True if YouTube URL, False otherwise
    """
    try:
        fetcher = ImageFetcher()
        return fetcher._is_youtube_url(url)
    except Exception:
        return False
