#!/usr/bin/env python3
"""
Simple test for Supabase image upload functionality.
"""

import os
import sys
import tempfile

from dotenv import load_dotenv
from PIL import Image

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_simple_upload():
    """Test simple image upload to Supabase."""

    # Set environment variables
    os.environ['SUPABASE_URL'] = 'https://gzzrthvxcmwjieqdtoxf.supabase.co'
    os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6enJ0aHZ4Y213amllcWR0b3hmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0ODc4MTE2OSwiZXhwIjoyMDY0MzU3MTY5fQ.LZhTfw-6rJCVWylGwuY_5rR3PfA8Ve2M3tQl51-lnr8'

    try:
        from src.utils.image_uploader import ImageUploader

        print("🚀 Testing Simple Image Upload")
        print("=" * 40)

        # Initialize uploader
        uploader = ImageUploader()
        print("✅ ImageUploader initialized")

        # Create a test image
        print("🖼️  Creating test image...")

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            # Create a simple test image
            img = Image.new('RGB', (300, 200), color='blue')
            img.save(tmp_file.name, 'PNG')

            file_size = os.path.getsize(tmp_file.name)
            print(f"   Created: {tmp_file.name} ({file_size:,} bytes)")

            try:
                # Upload the image
                print("☁️  Uploading to Supabase...")

                public_url = uploader.upload_image(
                    image_path=tmp_file.name,
                    article_id="test-simple-upload",
                    max_size_kb=500,
                    max_width=600
                )

                if public_url:
                    print("✅ Upload successful!")
                    print(f"🔗 Public URL: {public_url}")

                    # Verify URL is accessible
                    import requests
                    response = requests.head(public_url)
                    if response.status_code == 200:
                        print("✅ Image is publicly accessible")
                    else:
                        print(f"⚠️  Image URL returned status: {response.status_code}")

                    return True
                else:
                    print("❌ Upload failed - no URL returned")
                    return False

            except Exception as e:
                print(f"❌ Upload error: {e}")
                return False

            finally:
                # Clean up temp file
                os.unlink(tmp_file.name)
                print("🧹 Cleaned up temp file")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_upload()
    if success:
        print("\n🎉 Supabase image upload is working!")
        print("✅ Ready for production image processing")
    else:
        print("\n❌ Image upload test failed")

    sys.exit(0 if success else 1)
