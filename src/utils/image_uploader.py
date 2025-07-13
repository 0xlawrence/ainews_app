"""
Image uploader utility for Supabase storage integration.

This module handles uploading processed images to Supabase storage buckets
and returns public URLs for embedding in newsletters.
"""

import os
import io
import time
import hashlib
from pathlib import Path
from typing import Optional, Union
import logging

# Image processing
try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

# Supabase client
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    Client = None

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ImageUploader:
    """Handles image upload to Supabase storage with optimization."""
    
    def __init__(self):
        """Initialize the image uploader with Supabase client."""
        if not HAS_SUPABASE:
            raise ImportError("supabase package is required for image upload")
        
        if not HAS_PIL:
            raise ImportError("Pillow (PIL) package is required for image processing. Install with: pip install Pillow")
        
        self.settings = get_settings()
        self.client = self._initialize_client()
        self.bucket_name = self._get_bucket_name()
        
        logger.info(f"ImageUploader initialized with bucket: {self.bucket_name}")
    
    def _initialize_client(self) -> Client:
        """Initialize Supabase client with environment validation."""
        supabase_url = self.settings.database.supabase_url
        supabase_key = self.settings.database.supabase_key
        
        if not supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        
        if not supabase_key:
            raise ValueError("SUPABASE_KEY environment variable is required")
        
        # Validate URL format
        if not supabase_url.startswith('https://') or '.supabase.co' not in supabase_url:
            raise ValueError("SUPABASE_URL appears to be invalid")
        
        logger.info(f"Connecting to Supabase: {supabase_url[:30]}...")
        
        try:
            client = create_client(supabase_url, supabase_key)
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def _get_bucket_name(self) -> str:
        """Get the image storage bucket name from configuration."""
        bucket_name = self.settings.database.supabase_image_bucket
        
        logger.info(f"Using image bucket: {bucket_name}")
        return bucket_name
    
    def upload_image(
        self, 
        image_path: Union[str, Path], 
        article_id: Optional[str] = None,
        max_size_kb: int = 500,
        max_width: int = 600
    ) -> str:
        """
        Upload and optimize an image to Supabase storage.
        
        Args:
            image_path: Path to the image file to upload
            article_id: Optional article identifier for unique naming
            max_size_kb: Maximum file size in KB (default: 500KB)
            max_width: Maximum image width in pixels (default: 600px)
        
        Returns:
            Public URL of the uploaded image
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image processing fails
            Exception: If upload to Supabase fails
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        logger.info(f"Processing image for upload: {image_path}")
        
        # Process and optimize the image
        optimized_image_data = self._optimize_image(
            image_path, 
            max_size_kb=max_size_kb, 
            max_width=max_width
        )
        
        # Generate unique filename
        filename = self._generate_filename(image_path, article_id)
        
        # Upload to Supabase
        public_url = self._upload_to_supabase(optimized_image_data, filename)
        
        logger.info(f"Image uploaded successfully: {public_url}")
        return public_url
    
    def _optimize_image(
        self, 
        image_path: Path, 
        max_size_kb: int = 500, 
        max_width: int = 600
    ) -> bytes:
        """
        Optimize image for web embedding: resize, convert to JPEG, compress.
        
        Args:
            image_path: Path to the original image
            max_size_kb: Target maximum file size in KB
            max_width: Target maximum width in pixels
            
        Returns:
            Optimized image data as bytes
        """
        try:
            # Open and process the image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (handles PNG transparency, etc.)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Auto-orient based on EXIF data
                img = ImageOps.exif_transpose(img)
                
                # Resize if too wide
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    logger.debug(f"Resized image to {max_width}x{new_height}")
                
                # Compress to target size
                return self._compress_to_target_size(img, max_size_kb)
                
        except Exception as e:
            logger.error(f"Failed to optimize image {image_path}: {e}")
            raise ValueError(f"Image optimization failed: {e}")
    
    def _compress_to_target_size(self, img, max_size_kb: int) -> bytes:
        """
        Compress image to target file size by adjusting JPEG quality.
        
        Args:
            img: PIL Image object
            max_size_kb: Target maximum size in KB
            
        Returns:
            Compressed image data as bytes
        """
        target_size = max_size_kb * 1024  # Convert to bytes
        
        # Start with high quality and reduce if needed
        for quality in range(95, 20, -5):
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            size = buffer.tell()
            
            if size <= target_size:
                buffer.seek(0)
                image_data = buffer.getvalue()
                logger.debug(f"Compressed image to {size} bytes (quality: {quality})")
                return image_data
        
        # If still too large, use minimum quality
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=20, optimize=True)
        buffer.seek(0)
        image_data = buffer.getvalue()
        
        final_size = len(image_data)
        logger.warning(f"Image compressed to minimum quality: {final_size} bytes")
        
        return image_data
    
    def _generate_filename(self, original_path: Path, article_id: Optional[str] = None) -> str:
        """
        Generate unique filename for uploaded image.
        
        Args:
            original_path: Original image file path
            article_id: Optional article identifier
            
        Returns:
            Unique filename for storage
        """
        timestamp = int(time.time())
        
        # Create hash of original filename for uniqueness
        filename_hash = hashlib.md5(str(original_path).encode()).hexdigest()[:8]
        
        if article_id:
            # Clean article ID for filename
            clean_article_id = "".join(c for c in article_id if c.isalnum() or c in '-_')[:20]
            filename = f"{timestamp}_{clean_article_id}_{filename_hash}.jpg"
        else:
            filename = f"{timestamp}_{filename_hash}.jpg"
        
        return filename
    
    def _upload_to_supabase(self, image_data: bytes, filename: str) -> str:
        """
        Upload image data to Supabase storage bucket.
        
        Args:
            image_data: Optimized image bytes
            filename: Target filename in bucket
            
        Returns:
            Public URL of uploaded image
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Upload to storage bucket
            response = self.client.storage.from_(self.bucket_name).upload(
                path=filename,
                file=image_data,
                file_options={
                    "content-type": "image/jpeg",
                    "cache-control": "3600"  # Cache for 1 hour
                }
            )
            
            # Check for upload errors
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Supabase upload error: {response.error}")
            
            # Get public URL
            public_url_response = self.client.storage.from_(self.bucket_name).get_public_url(filename)
            
            if isinstance(public_url_response, dict) and 'publicUrl' in public_url_response:
                public_url = public_url_response['publicUrl']
            else:
                # Fallback: construct URL manually
                base_url = self.settings.database.supabase_url
                public_url = f"{base_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
            
            # Validate URL format
            if not public_url.startswith('https://'):
                raise Exception(f"Invalid public URL format: {public_url}")
            
            logger.info(f"Successfully uploaded {filename} to {self.bucket_name}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload image to Supabase: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test connection to Supabase storage.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to list buckets to test connection
            buckets = self.client.storage.list_buckets()
            
            if hasattr(buckets, 'error') and buckets.error:
                logger.error(f"Supabase connection test failed: {buckets.error}")
                return False
            
            logger.info("Supabase connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Supabase connection test error: {e}")
            return False


# Convenience function for simple usage
def upload_image_to_supabase(
    image_path: Union[str, Path], 
    article_id: Optional[str] = None
) -> Optional[str]:
    """
    Convenience function to upload an image to Supabase.
    
    Args:
        image_path: Path to image file
        article_id: Optional article identifier
        
    Returns:
        Public URL if successful, None if failed
    """
    try:
        uploader = ImageUploader()
        return uploader.upload_image(image_path, article_id)
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        return None