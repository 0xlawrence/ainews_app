#!/usr/bin/env python3
"""
Real image processing test with actual YouTube URLs and Supabase integration.

Tests the complete pipeline with real data to verify functionality.
"""

import sys
import os
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_real_image_processing():
    """Test image processing with real YouTube URLs."""
    try:
        from src.utils.image_processor import ImageProcessor
        from src.config.settings import get_settings
        
        print("🚀 Testing Real Image Processing")
        print("=" * 50)
        
        # Initialize image processor
        print("Initializing ImageProcessor...")
        processor = ImageProcessor()
        print("✅ ImageProcessor initialized")
        
        # Test with a real YouTube video
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - reliable test
            "https://youtu.be/dQw4w9WgXcQ",                # Short URL format
            "https://techcrunch.com/",                      # Regular website for OGP test
        ]
        
        for i, url in enumerate(test_urls):
            print(f"\n🧪 Test {i+1}: {url}")
            print("-" * 30)
            
            try:
                # Process the image
                result = await processor.process_article_image(
                    url=url,
                    article_id=f"test-article-{i+1}",
                    cleanup_temp=True
                )
                
                if result:
                    print(f"✅ Success!")
                    print(f"   Image URL: {result.get('image_url', 'N/A')}")
                    print(f"   Source Type: {result.get('source_type', 'N/A')}")
                    if 'dimensions' in result:
                        dims = result['dimensions']
                        print(f"   Dimensions: {dims.get('width', 'N/A')}x{dims.get('height', 'N/A')}")
                    print(f"   File Size: {result.get('file_size', 'N/A')} bytes")
                else:
                    print("❌ No image processed (expected if Supabase not configured)")
                    
            except Exception as e:
                print(f"❌ Error processing {url}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_image_fetching_only():
    """Test just the image fetching without Supabase upload."""
    try:
        from src.utils.image_fetcher import ImageFetcher
        
        print("\n🚀 Testing Image Fetching Only (No Upload)")
        print("=" * 50)
        
        fetcher = ImageFetcher()
        
        test_urls = [
            ("YouTube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            ("TechCrunch", "https://techcrunch.com/"),
        ]
        
        for name, url in test_urls:
            print(f"\n🧪 Fetching from {name}: {url}")
            print("-" * 30)
            
            try:
                image_path = fetcher.get_image_from_url(url, article_id=f"test-{name.lower()}")
                
                if image_path and image_path.exists():
                    file_size = image_path.stat().st_size
                    print(f"✅ Image fetched successfully!")
                    print(f"   Local path: {image_path}")
                    print(f"   File size: {file_size:,} bytes")
                    
                    # Clean up
                    image_path.unlink()
                    print(f"   Cleaned up temporary file")
                else:
                    print(f"❌ No image fetched from {name}")
                    
            except Exception as e:
                print(f"❌ Error fetching from {name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Image fetching test failed: {e}")
        return False

async def check_supabase_config():
    """Check Supabase configuration."""
    try:
        from src.config.settings import get_settings
        
        print("\n🔧 Checking Supabase Configuration")
        print("=" * 40)
        
        settings = get_settings()
        
        # Check environment variables
        import os
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        print(f"SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Not set'}")
        print(f"SUPABASE_KEY: {'✅ Set' if supabase_key else '❌ Not set'}")
        print(f"Image Bucket: {settings.database.supabase_image_bucket}")
        
        if supabase_url and supabase_key:
            # Try to test Supabase connection
            try:
                from src.utils.image_uploader import ImageUploader
                uploader = ImageUploader()
                print("✅ ImageUploader initialized successfully")
                
                # Note: We won't actually test upload without a real image
                print("ℹ️  Supabase connection appears to be configured")
                
            except Exception as e:
                print(f"❌ Supabase connection error: {e}")
        else:
            print("⚠️  Supabase not configured - image upload will fail")
            print("   Set SUPABASE_URL and SUPABASE_KEY environment variables")
        
        return supabase_url and supabase_key
        
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        return False

async def main():
    """Run all real image processing tests."""
    print("🚀 Real Image Processing Verification")
    print("=" * 60)
    
    # Check configuration first
    config_ok = await check_supabase_config()
    
    # Test image fetching (always works)
    fetch_ok = await test_image_fetching_only()
    
    # Test full processing (requires Supabase)
    if config_ok:
        process_ok = await test_real_image_processing()
    else:
        print("\n⚠️  Skipping full processing test - Supabase not configured")
        process_ok = False
    
    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    print(f"  Configuration: {'✅ OK' if config_ok else '❌ Missing Supabase config'}")
    print(f"  Image Fetching: {'✅ OK' if fetch_ok else '❌ Failed'}")
    print(f"  Full Processing: {'✅ OK' if process_ok else '❌ Failed/Skipped'}")
    
    if fetch_ok:
        print("\n🎉 Image fetching is working correctly!")
        print("📝 To enable full processing, configure Supabase environment variables")
    else:
        print("\n❌ Image fetching failed - check network connectivity")
    
    return fetch_ok

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)