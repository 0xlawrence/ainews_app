"""
Unit tests for image fetcher functionality.

Tests OGP extraction, YouTube thumbnails, and image downloading.
"""

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

# Import the modules under test
from src.utils.image_fetcher import ImageFetcher, get_image_for_article, is_youtube_url
from src.utils.image_processor import ImageProcessor, process_article_image, test_image_processing


class TestImageFetcher:
    """Test cases for the ImageFetcher class."""

    @pytest.fixture
    def image_fetcher(self):
        """Create an ImageFetcher instance for testing."""
        with patch('src.utils.image_fetcher.get_settings'):
            return ImageFetcher()

    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = Mock()
        response.status_code = 200
        response.headers = {'content-type': 'image/jpeg'}
        response.content = self._create_test_image_bytes()
        response.iter_content = Mock(return_value=[response.content])
        response.raise_for_status = Mock()
        return response

    @pytest.fixture
    def mock_html_response(self):
        """Create a mock HTML response with OGP tags."""
        html_content = """
        <html>
        <head>
            <meta property="og:image" content="https://example.com/image.jpg" />
            <meta property="og:title" content="Test Article" />
        </head>
        <body>
            <article>
                <img src="https://example.com/content-image.jpg" width="800" height="600" alt="Content image" />
                <img src="https://example.com/icon.png" width="16" height="16" alt="Icon" />
            </article>
        </body>
        </html>
        """

        response = Mock()
        response.status_code = 200
        response.content = html_content.encode('utf-8')
        response.raise_for_status = Mock()
        return response

    def _create_test_image_bytes(self, width=800, height=600, format='JPEG'):
        """Create test image bytes."""
        img = Image.new('RGB', (width, height), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return buffer.getvalue()

    def test_is_youtube_url(self, image_fetcher):
        """Test YouTube URL detection."""
        youtube_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/v/dQw4w9WgXcQ",
        ]

        non_youtube_urls = [
            "https://example.com/article",
            "https://vimeo.com/123456",
            "https://twitter.com/user/status/123",
        ]

        for url in youtube_urls:
            assert image_fetcher._is_youtube_url(url), f"Should detect YouTube URL: {url}"

        for url in non_youtube_urls:
            assert not image_fetcher._is_youtube_url(url), f"Should not detect YouTube URL: {url}"

    def test_extract_youtube_video_id(self, image_fetcher):
        """Test YouTube video ID extraction."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123", "dQw4w9WgXcQ"),
            ("https://example.com/not-youtube", None),
        ]

        for url, expected_id in test_cases:
            result = image_fetcher._extract_youtube_video_id(url)
            assert result == expected_id, f"URL: {url}, Expected: {expected_id}, Got: {result}"

    @patch('src.utils.image_fetcher.requests.Session.get')
    def test_get_youtube_thumbnail_success(self, mock_get, image_fetcher):
        """Test successful YouTube thumbnail download."""
        # Mock successful thumbnail response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_test_image_bytes(1280, 720)
        mock_get.return_value = mock_response

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        with patch.object(image_fetcher, '_save_to_temp_file') as mock_save, \
             patch.object(image_fetcher, '_validate_image', return_value=True):

            mock_temp_path = Path("/tmp/test_thumbnail.tmp")
            mock_save.return_value = mock_temp_path

            result = image_fetcher._get_youtube_thumbnail(url, "test-article")

            assert result == mock_temp_path
            mock_save.assert_called_once()
            assert mock_get.called

    @patch('src.utils.image_fetcher.requests.Session.get')
    def test_get_youtube_thumbnail_all_qualities_fail(self, mock_get, image_fetcher):
        """Test YouTube thumbnail when all qualities fail."""
        # Mock failed responses for all qualities
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        url = "https://www.youtube.com/watch?v=invalid_video_id"
        result = image_fetcher._get_youtube_thumbnail(url, "test-article")

        assert result is None
        # Should try multiple qualities
        assert mock_get.call_count >= 3

    @patch('src.utils.image_fetcher.requests.Session.get')
    def test_get_ogp_image_success(self, mock_get, image_fetcher, mock_html_response, mock_response):
        """Test successful OGP image extraction."""
        # First call returns HTML with OGP tags, second call downloads image
        mock_get.side_effect = [mock_html_response, mock_response]

        with patch.object(image_fetcher, '_save_to_temp_file') as mock_save, \
             patch.object(image_fetcher, '_validate_image', return_value=True):

            mock_temp_path = Path("/tmp/test_ogp.tmp")
            mock_save.return_value = mock_temp_path

            url = "https://example.com/article"
            result = image_fetcher._get_ogp_image(url, "test-article")

            assert result == mock_temp_path
            assert mock_get.call_count == 2  # HTML + image download

    @patch('src.utils.image_fetcher.requests.Session.get')
    def test_get_ogp_image_no_og_tags(self, mock_get, image_fetcher):
        """Test OGP extraction when no OG tags are found."""
        html_content = "<html><head><title>No OG tags</title></head><body></body></html>"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = html_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        url = "https://example.com/article"
        result = image_fetcher._get_ogp_image(url, "test-article")

        assert result is None

    def test_resolve_url(self, image_fetcher):
        """Test URL resolution for relative paths."""
        test_cases = [
            ("https://example.com/image.jpg", "https://example.com/", "https://example.com/image.jpg"),
            ("/image.jpg", "https://example.com/article", "https://example.com/image.jpg"),
            ("../image.jpg", "https://example.com/news/article", "https://example.com/image.jpg"),
            ("image.jpg", "https://example.com/news/", "https://example.com/news/image.jpg"),
        ]

        for image_url, base_url, expected in test_cases:
            result = image_fetcher._resolve_url(image_url, base_url)
            assert result == expected, f"Image: {image_url}, Base: {base_url}, Expected: {expected}, Got: {result}"

    def test_is_suitable_content_image(self, image_fetcher):
        """Test content image suitability detection."""
        from bs4 import BeautifulSoup

        # Test cases: (html, src, expected_result)
        test_cases = [
            # Good content images
            ('<img src="content.jpg" width="800" height="600" alt="Article content">', "content.jpg", True),
            ('<img src="feature-image.jpg" class="article-image">', "feature-image.jpg", True),
            ('<img src="hero-banner.jpg">', "hero-banner.jpg", True),

            # Bad images (icons, UI elements)
            ('<img src="icon.png" width="16" height="16">', "icon.png", False),
            ('<img src="logo.svg" width="50" height="20">', "logo.svg", False),
            ('<img src="avatar.jpg" width="40" height="40">', "avatar.jpg", False),
            ('<img src="ad-banner.jpg">', "ad-banner.jpg", False),
            ('<img src="tracking-pixel.gif" width="1" height="1">', "tracking-pixel.gif", False),
        ]

        for html, src, expected in test_cases:
            soup = BeautifulSoup(html, 'html.parser')
            img_tag = soup.find('img')
            result = image_fetcher._is_suitable_content_image(img_tag, src)
            assert result == expected, f"HTML: {html}, Expected: {expected}, Got: {result}"

    @patch('src.utils.image_fetcher.requests.Session.get')
    def test_download_image_success(self, mock_get, image_fetcher, mock_response):
        """Test successful image download."""
        mock_get.return_value = mock_response

        with patch.object(image_fetcher, '_save_to_temp_file') as mock_save, \
             patch.object(image_fetcher, '_validate_image', return_value=True):

            mock_temp_path = Path("/tmp/test_download.tmp")
            mock_save.return_value = mock_temp_path

            result = image_fetcher._download_image(
                "https://example.com/image.jpg",
                "test_prefix",
                "test-article"
            )

            assert result == mock_temp_path
            mock_save.assert_called_once()

    @patch('src.utils.image_fetcher.requests.Session.get')
    def test_download_image_invalid_content_type(self, mock_get, image_fetcher):
        """Test image download with invalid content type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.content = b"<html>Not an image</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = image_fetcher._download_image(
            "https://example.com/not-image.html",
            "test_prefix",
            "test-article"
        )

        assert result is None

    @patch('src.utils.image_fetcher.requests.Session.get')
    def test_download_image_too_large(self, mock_get, image_fetcher):
        """Test image download that exceeds size limit."""
        # Create a mock response that appears to be very large
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.raise_for_status = Mock()

        # Mock iter_content to simulate large file
        large_chunk = b'x' * (2 * 1024 * 1024)  # 2MB chunks
        mock_response.iter_content.return_value = [large_chunk] * 10  # 20MB total

        mock_get.return_value = mock_response

        # Set small limit for testing
        image_fetcher.max_image_size_mb = 5

        result = image_fetcher._download_image(
            "https://example.com/huge-image.jpg",
            "test_prefix",
            "test-article"
        )

        assert result is None

    def test_validate_image_valid(self, image_fetcher):
        """Test image validation with valid image."""
        # Create a valid test image
        img = Image.new('RGB', (400, 300), color='red')
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img.save(temp_file.name, 'JPEG')
        temp_file.close()

        try:
            result = image_fetcher._validate_image(Path(temp_file.name))
            assert result is True
        finally:
            os.unlink(temp_file.name)

    def test_validate_image_too_small(self, image_fetcher):
        """Test image validation with too small image."""
        # Create a very small image
        img = Image.new('RGB', (50, 50), color='red')
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img.save(temp_file.name, 'JPEG')
        temp_file.close()

        try:
            result = image_fetcher._validate_image(Path(temp_file.name))
            assert result is False
        finally:
            os.unlink(temp_file.name)

    def test_validate_image_bad_aspect_ratio(self, image_fetcher):
        """Test image validation with unusual aspect ratio."""
        # Create a very narrow image
        img = Image.new('RGB', (1000, 100), color='red')  # 10:1 aspect ratio
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img.save(temp_file.name, 'JPEG')
        temp_file.close()

        try:
            result = image_fetcher._validate_image(Path(temp_file.name))
            assert result is False
        finally:
            os.unlink(temp_file.name)

    def test_save_to_temp_file(self, image_fetcher):
        """Test saving content to temporary file."""
        content = b"test image data"
        filename_prefix = "test_prefix"
        article_id = "test-article"

        result = image_fetcher._save_to_temp_file(content, filename_prefix, article_id)

        assert result is not None
        assert result.exists()
        assert result.name.endswith('.tmp')
        assert 'test_prefix' in result.name
        assert 'test-article' in result.name

        # Verify content
        with open(result, 'rb') as f:
            assert f.read() == content

        # Cleanup
        result.unlink()

    def test_cleanup_temp_files(self, image_fetcher):
        """Test cleanup of old temporary files."""
        import time

        # Create some test temp files
        temp_dir = Path(tempfile.gettempdir()) / "ainews_images"
        temp_dir.mkdir(exist_ok=True)

        # Create an old file (simulate by modifying mtime)
        old_file = temp_dir / "old_file.tmp"
        old_file.write_text("old content")

        # Set modification time to 25 hours ago
        old_time = time.time() - (25 * 3600)
        os.utime(old_file, (old_time, old_time))

        # Create a new file
        new_file = temp_dir / "new_file.tmp"
        new_file.write_text("new content")

        try:
            # Run cleanup (max_age_hours=24)
            image_fetcher.cleanup_temp_files(max_age_hours=24)

            # Old file should be removed, new file should remain
            assert not old_file.exists()
            assert new_file.exists()

        finally:
            # Cleanup
            if new_file.exists():
                new_file.unlink()


class TestImageFetcherIntegration:
    """Integration tests for ImageFetcher."""

    @patch('src.utils.image_fetcher.requests.Session.get')
    def test_get_image_from_url_youtube_success(self, mock_get):
        """Test complete image fetching for YouTube URL."""
        # Mock YouTube thumbnail response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = TestImageFetcher()._create_test_image_bytes()
        mock_get.return_value = mock_response

        with patch('src.utils.image_fetcher.get_settings'), \
             patch('tempfile.gettempdir', return_value='/tmp'):

            fetcher = ImageFetcher()

            with patch.object(fetcher, '_validate_image', return_value=True):
                result = fetcher.get_image_from_url(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "test-article"
                )

                assert result is not None
                assert result.exists()

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test is_youtube_url
        assert is_youtube_url("https://www.youtube.com/watch?v=123") is True
        assert is_youtube_url("https://example.com/article") is False

        # Test get_image_for_article (will fail without mocking, but should not crash)
        result = get_image_for_article("https://example.com/article", "test")
        # Should return None due to no actual network access, but shouldn't crash
        assert result is None or isinstance(result, Path)


class TestImageProcessor:
    """Test cases for the ImageProcessor class."""

    @patch('src.utils.image_processor.ImageFetcher')
    @patch('src.utils.image_processor.ImageUploader')
    def test_process_article_image_success(self, mock_uploader_class, mock_fetcher_class):
        """Test successful article image processing."""
        # Mock the fetcher
        mock_fetcher = Mock()
        mock_temp_path = Path("/tmp/test_image.tmp")
        mock_temp_path.exists = Mock(return_value=True)
        mock_temp_path.stat = Mock(return_value=Mock(st_size=50000))
        mock_temp_path.unlink = Mock()
        mock_fetcher.get_image_from_url.return_value = mock_temp_path
        mock_fetcher_class.return_value = mock_fetcher

        # Mock the uploader
        mock_uploader = Mock()
        mock_uploader.upload_image.return_value = "https://supabase.example.com/image.jpg"
        mock_uploader_class.return_value = mock_uploader

        # Mock PIL Image
        with patch('src.utils.image_processor.Image') as mock_image:
            mock_img = Mock()
            mock_img.width = 600
            mock_img.height = 400
            mock_img.format = 'JPEG'
            mock_image.open.return_value.__enter__.return_value = mock_img

            processor = ImageProcessor()
            result = processor.process_article_image(
                "https://example.com/article",
                "test-article"
            )

            assert result is not None
            assert result['image_url'] == "https://supabase.example.com/image.jpg"
            assert result['dimensions']['width'] == 600
            assert result['dimensions']['height'] == 400
            assert result['file_size'] == 50000

            # Verify temp file cleanup
            mock_temp_path.unlink.assert_called_once()

    @patch('src.utils.image_processor.ImageFetcher')
    @patch('src.utils.image_processor.ImageUploader')
    def test_process_article_image_fetch_failure(self, mock_uploader_class, mock_fetcher_class):
        """Test article image processing when fetch fails."""
        # Mock fetcher to return None (fetch failed)
        mock_fetcher = Mock()
        mock_fetcher.get_image_from_url.return_value = None
        mock_fetcher_class.return_value = mock_fetcher

        mock_uploader = Mock()
        mock_uploader_class.return_value = mock_uploader

        processor = ImageProcessor()
        result = processor.process_article_image(
            "https://example.com/article",
            "test-article"
        )

        assert result is None
        # Uploader should not be called if fetch failed
        mock_uploader.upload_image.assert_not_called()

    @patch('src.utils.image_processor.ImageFetcher')
    @patch('src.utils.image_processor.ImageUploader')
    def test_process_article_image_upload_failure(self, mock_uploader_class, mock_fetcher_class):
        """Test article image processing when upload fails."""
        # Mock successful fetch
        mock_fetcher = Mock()
        mock_temp_path = Path("/tmp/test_image.tmp")
        mock_temp_path.exists = Mock(return_value=True)
        mock_temp_path.unlink = Mock()
        mock_fetcher.get_image_from_url.return_value = mock_temp_path
        mock_fetcher_class.return_value = mock_fetcher

        # Mock failed upload
        mock_uploader = Mock()
        mock_uploader.upload_image.return_value = None
        mock_uploader_class.return_value = mock_uploader

        processor = ImageProcessor()
        result = processor.process_article_image(
            "https://example.com/article",
            "test-article"
        )

        assert result is None
        # Temp file should still be cleaned up
        mock_temp_path.unlink.assert_called_once()

    def test_convenience_functions(self):
        """Test convenience functions for ImageProcessor."""
        # These will fail without proper mocking but should not crash
        result = process_article_image("https://example.com/article", "test")
        assert result is None or isinstance(result, dict)

        result = test_image_processing()
        assert isinstance(result, bool)


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
