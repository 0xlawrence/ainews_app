#!/usr/bin/env python3
"""
Test YouTube image fetch and upload to Supabase.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_youtube_upload():
    """Test YouTube image fetch and upload."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = 'https://gzzrthvxcmwjieqdtoxf.supabase.co'
    os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6enJ0aHZ4Y213amllcWR0b3hmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0ODc4MTE2OSwiZXhwIjoyMDY0MzU3MTY5fQ.LZhTfw-6rJCVWylGwuY_5rR3PfA8Ve2M3tQl51-lnr8'
    
    try:
        from src.utils.image_fetcher import ImageFetcher
        from src.utils.image_uploader import ImageUploader
        
        print("🚀 Testing YouTube Image Upload")
        print("=" * 40)
        
        # Initialize components
        fetcher = ImageFetcher()
        uploader = ImageUploader()
        
        # Test URL
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        article_id = "test-youtube-upload"
        
        print(f"📺 Fetching YouTube thumbnail: {youtube_url}")
        
        # Fetch image
        image_path = fetcher.get_image_from_url(youtube_url, article_id)
        
        if not image_path or not image_path.exists():
            print("❌ Failed to fetch YouTube image")
            return False
        
        file_size = image_path.stat().st_size
        print(f"✅ Image fetched: {file_size:,} bytes")
        print(f"📁 Local path: {image_path}")
        
        try:
            # Upload to Supabase
            print("☁️  Uploading to Supabase...")
            
            public_url = uploader.upload_image(
                image_path=image_path,
                article_id=article_id,
                max_size_kb=500,
                max_width=600
            )
            
            if public_url:
                print(f"✅ Upload successful!")
                print(f"🔗 Public URL: {public_url}")
                
                # Verify URL is accessible
                import requests
                response = requests.head(public_url)
                if response.status_code == 200:
                    print("✅ YouTube image is publicly accessible")
                    return True
                else:
                    print(f"⚠️  Image URL returned status: {response.status_code}")
                    return False
            else:
                print("❌ Upload failed - no URL returned")
                return False
                
        finally:
            # Clean up temp file
            if image_path.exists():
                image_path.unlink()
                print("🧹 Cleaned up temp file")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_youtube_upload()
    if success:
        print("\n🎉 YouTube image upload pipeline working!")
        print("✅ Ready for full newsletter generation with images")
    else:
        print("\n❌ YouTube image upload test failed")
    
    sys.exit(0 if success else 1)