"""
Unit tests for image uploader functionality.

Tests image optimization, Supabase upload, and error handling.
"""

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

# Import the module under test
from src.utils.image_uploader import ImageUploader, upload_image_to_supabase


class TestImageUploader:
    """Test cases for the ImageUploader class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.database = Mock()
        settings.database.supabase_url = "https://test.supabase.co"
        settings.database.supabase_key = "test-key"
        settings.database.supabase_image_bucket = "test-bucket"
        return settings

    @pytest.fixture
    def sample_image_path(self):
        """Create a temporary test image."""
        # Create a test image in memory
        img = Image.new('RGB', (800, 600), color='red')

        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name, 'PNG')
        temp_file.close()

        yield Path(temp_file.name)

        # Cleanup
        os.unlink(temp_file.name)

    @pytest.fixture
    def large_image_path(self):
        """Create a large test image for compression testing."""
        # Create a large image
        img = Image.new('RGB', (2000, 1500), color='blue')

        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img.save(temp_file.name, 'JPEG', quality=95)
        temp_file.close()

        yield Path(temp_file.name)

        # Cleanup
        os.unlink(temp_file.name)

    @pytest.fixture
    def png_with_transparency(self):
        """Create a PNG image with transparency."""
        # Create RGBA image with transparency
        img = Image.new('RGBA', (400, 300), (255, 0, 0, 128))  # Semi-transparent red

        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name, 'PNG')
        temp_file.close()

        yield Path(temp_file.name)

        # Cleanup
        os.unlink(temp_file.name)

    @patch('src.utils.image_uploader.create_client')
    @patch('src.utils.image_uploader.get_settings')
    def test_initialization_success(self, mock_get_settings, mock_create_client, mock_settings):
        """Test successful initialization of ImageUploader."""
        mock_get_settings.return_value = mock_settings
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        uploader = ImageUploader()

        assert uploader.settings == mock_settings
        assert uploader.client == mock_client
        assert uploader.bucket_name == "test-bucket"

    @patch('src.utils.image_uploader.get_settings')
    def test_initialization_missing_supabase_url(self, mock_get_settings):
        """Test initialization fails with missing Supabase URL."""
        settings = Mock()
        settings.database = Mock()
        settings.database.supabase_url = ""
        settings.database.supabase_key = "test-key"
        mock_get_settings.return_value = settings

        with pytest.raises(ValueError, match="SUPABASE_URL environment variable is required"):
            ImageUploader()

    @patch('src.utils.image_uploader.get_settings')
    def test_initialization_invalid_supabase_url(self, mock_get_settings):
        """Test initialization fails with invalid Supabase URL."""
        settings = Mock()
        settings.database = Mock()
        settings.database.supabase_url = "http://invalid-url.com"
        settings.database.supabase_key = "test-key"
        mock_get_settings.return_value = settings

        with pytest.raises(ValueError, match="SUPABASE_URL appears to be invalid"):
            ImageUploader()

    def test_optimize_image_resize(self, sample_image_path):
        """Test image resizing functionality."""
        uploader = ImageUploader.__new__(ImageUploader)  # Create without __init__

        # Test image should be 800x600, resize to max_width=400
        optimized_data = uploader._optimize_image(sample_image_path, max_width=400)

        # Load the optimized image to check dimensions
        img = Image.open(io.BytesIO(optimized_data))
        assert img.width == 400
        assert img.height == 300  # Should maintain aspect ratio
        assert img.format == 'JPEG'

    def test_optimize_image_compression(self, large_image_path):
        """Test image compression to target size."""
        uploader = ImageUploader.__new__(ImageUploader)  # Create without __init__

        # Compress to 100KB
        optimized_data = uploader._optimize_image(large_image_path, max_size_kb=100)

        # Check that file size is approximately within target (allow some variance)
        assert len(optimized_data) <= 100 * 1024 * 1.1  # Allow 10% variance

        # Verify it's still a valid JPEG
        img = Image.open(io.BytesIO(optimized_data))
        assert img.format == 'JPEG'

    def test_optimize_png_with_transparency(self, png_with_transparency):
        """Test conversion of PNG with transparency to JPEG."""
        uploader = ImageUploader.__new__(ImageUploader)  # Create without __init__

        optimized_data = uploader._optimize_image(png_with_transparency)

        # Should convert to JPEG with white background
        img = Image.open(io.BytesIO(optimized_data))
        assert img.format == 'JPEG'
        assert img.mode == 'RGB'

        # Check that there's no transparency (should be white background)
        # Get pixel at a location that was transparent
        pixel = img.getpixel((0, 0))
        # Should be some blend of red and white (no alpha channel)
        assert len(pixel) == 3  # RGB, no alpha

    def test_generate_filename_with_article_id(self):
        """Test filename generation with article ID."""
        uploader = ImageUploader.__new__(ImageUploader)  # Create without __init__

        original_path = Path("test_image.png")
        article_id = "test-article-123"

        filename = uploader._generate_filename(original_path, article_id)

        assert filename.endswith('.jpg')
        assert 'test-article-123' in filename
        assert len(filename.split('_')) >= 3  # timestamp_article_hash.jpg

    def test_generate_filename_without_article_id(self):
        """Test filename generation without article ID."""
        uploader = ImageUploader.__new__(ImageUploader)  # Create without __init__

        original_path = Path("test_image.png")

        filename = uploader._generate_filename(original_path, None)

        assert filename.endswith('.jpg')
        assert len(filename.split('_')) == 2  # timestamp_hash.jpg

    def test_generate_filename_cleans_article_id(self):
        """Test that article ID is cleaned for safe filename."""
        uploader = ImageUploader.__new__(ImageUploader)  # Create without __init__

        original_path = Path("test.png")
        article_id = "article/with:special*chars?"

        filename = uploader._generate_filename(original_path, article_id)

        # Should contain only alphanumeric, dash, underscore
        parts = filename.split('_')
        article_part = parts[1]  # Should be the cleaned article ID
        assert all(c.isalnum() or c in '-_' for c in article_part)

    @patch('src.utils.image_uploader.create_client')
    @patch('src.utils.image_uploader.get_settings')
    def test_upload_to_supabase_success(self, mock_get_settings, mock_create_client, mock_settings):
        """Test successful upload to Supabase."""
        mock_get_settings.return_value = mock_settings
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock successful upload response
        mock_upload_response = Mock()
        mock_upload_response.error = None
        mock_client.storage.from_().upload.return_value = mock_upload_response

        # Mock public URL response
        mock_client.storage.from_().get_public_url.return_value = {
            'publicUrl': 'https://test.supabase.co/storage/v1/object/public/test-bucket/test.jpg'
        }

        uploader = ImageUploader()
        image_data = b'fake image data'
        filename = 'test.jpg'

        public_url = uploader._upload_to_supabase(image_data, filename)

        assert public_url == 'https://test.supabase.co/storage/v1/object/public/test-bucket/test.jpg'
        mock_client.storage.from_().upload.assert_called_once()

    @patch('src.utils.image_uploader.create_client')
    @patch('src.utils.image_uploader.get_settings')
    def test_upload_to_supabase_upload_error(self, mock_get_settings, mock_create_client, mock_settings):
        """Test handling of Supabase upload error."""
        mock_get_settings.return_value = mock_settings
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock upload error
        mock_upload_response = Mock()
        mock_upload_response.error = "Upload failed"
        mock_client.storage.from_().upload.return_value = mock_upload_response

        uploader = ImageUploader()
        image_data = b'fake image data'
        filename = 'test.jpg'

        with pytest.raises(Exception, match="Supabase upload error"):
            uploader._upload_to_supabase(image_data, filename)

    @patch('src.utils.image_uploader.create_client')
    @patch('src.utils.image_uploader.get_settings')
    def test_upload_to_supabase_fallback_url(self, mock_get_settings, mock_create_client, mock_settings):
        """Test fallback URL construction when get_public_url fails."""
        mock_get_settings.return_value = mock_settings
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock successful upload
        mock_upload_response = Mock()
        mock_upload_response.error = None
        mock_client.storage.from_().upload.return_value = mock_upload_response

        # Mock public URL failure (returns string instead of dict)
        mock_client.storage.from_().get_public_url.return_value = "invalid response"

        uploader = ImageUploader()
        image_data = b'fake image data'
        filename = 'test.jpg'

        public_url = uploader._upload_to_supabase(image_data, filename)

        expected_url = "https://test.supabase.co/storage/v1/object/public/test-bucket/test.jpg"
        assert public_url == expected_url

    @patch('src.utils.image_uploader.create_client')
    @patch('src.utils.image_uploader.get_settings')
    def test_test_connection_success(self, mock_get_settings, mock_create_client, mock_settings):
        """Test successful connection test."""
        mock_get_settings.return_value = mock_settings
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock successful bucket list
        mock_buckets_response = Mock()
        mock_buckets_response.error = None
        mock_client.storage.list_buckets.return_value = mock_buckets_response

        uploader = ImageUploader()
        result = uploader.test_connection()

        assert result is True
        mock_client.storage.list_buckets.assert_called_once()

    @patch('src.utils.image_uploader.create_client')
    @patch('src.utils.image_uploader.get_settings')
    def test_test_connection_failure(self, mock_get_settings, mock_create_client, mock_settings):
        """Test connection test failure."""
        mock_get_settings.return_value = mock_settings
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock connection error
        mock_buckets_response = Mock()
        mock_buckets_response.error = "Connection failed"
        mock_client.storage.list_buckets.return_value = mock_buckets_response

        uploader = ImageUploader()
        result = uploader.test_connection()

        assert result is False

    def test_upload_image_file_not_found(self):
        """Test handling of non-existent image file."""
        uploader = ImageUploader.__new__(ImageUploader)  # Create without __init__

        non_existent_path = Path("non_existent_image.jpg")

        with pytest.raises(FileNotFoundError, match="Image file not found"):
            uploader.upload_image(non_existent_path)

    @patch('src.utils.image_uploader.ImageUploader')
    def test_convenience_function_success(self, mock_uploader_class):
        """Test the convenience function for successful upload."""
        # Mock the uploader instance and methods
        mock_uploader = Mock()
        mock_uploader.upload_image.return_value = "https://example.com/image.jpg"
        mock_uploader_class.return_value = mock_uploader

        result = upload_image_to_supabase("test.jpg", "article-123")

        assert result == "https://example.com/image.jpg"
        mock_uploader.upload_image.assert_called_once_with("test.jpg", "article-123")

    @patch('src.utils.image_uploader.ImageUploader')
    def test_convenience_function_failure(self, mock_uploader_class):
        """Test the convenience function handling failure."""
        # Mock the uploader to raise an exception
        mock_uploader_class.side_effect = Exception("Upload failed")

        result = upload_image_to_supabase("test.jpg")

        assert result is None

    def test_compress_to_target_size_quality_adjustment(self):
        """Test that compression adjusts quality to meet size target."""
        uploader = ImageUploader.__new__(ImageUploader)  # Create without __init__

        # Create a test image
        img = Image.new('RGB', (1000, 800), color='red')

        # Test compression to very small size (should reduce quality significantly)
        compressed_data = uploader._compress_to_target_size(img, max_size_kb=10)

        assert len(compressed_data) <= 10 * 1024 * 1.2  # Allow 20% variance for edge cases

        # Verify it's still a valid JPEG
        result_img = Image.open(io.BytesIO(compressed_data))
        assert result_img.format == 'JPEG'


class TestImageUploaderIntegration:
    """Integration tests that test multiple components together."""

    @pytest.fixture
    def mock_supabase_env(self):
        """Mock environment variables for Supabase."""
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key',
            'SUPABASE_IMAGE_BUCKET': 'test-images'
        }):
            yield

    @patch('src.utils.image_uploader.create_client')
    @patch('src.utils.image_uploader.get_settings')
    def test_full_upload_workflow(self, mock_get_settings, mock_create_client, sample_image_path, mock_settings):
        """Test the complete upload workflow from file to URL."""
        mock_get_settings.return_value = mock_settings
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock successful responses
        mock_upload_response = Mock()
        mock_upload_response.error = None
        mock_client.storage.from_().upload.return_value = mock_upload_response
        mock_client.storage.from_().get_public_url.return_value = {
            'publicUrl': 'https://test.supabase.co/storage/v1/object/public/test-bucket/uploaded.jpg'
        }

        uploader = ImageUploader()
        public_url = uploader.upload_image(sample_image_path, "test-article")

        assert public_url.startswith('https://')
        assert 'test-bucket' in public_url
        assert public_url.endswith('.jpg')

        # Verify upload was called with correct parameters
        upload_call = mock_client.storage.from_().upload.call_args
        assert upload_call[1]['file_options']['content-type'] == 'image/jpeg'
        assert upload_call[1]['file_options']['cache-control'] == '3600'


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
