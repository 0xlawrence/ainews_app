#!/usr/bin/env python3
"""
Check Supabase Storage configuration and create bucket if needed.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_supabase_storage():
    """Check Supabase storage and create bucket if needed."""
    
    try:
        from supabase import create_client, Client
        
        # Get credentials
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not key:
            print("❌ Supabase credentials not found in environment")
            return False
        
        print(f"🔗 Connecting to Supabase: {url[:30]}...")
        
        # Create client
        supabase: Client = create_client(url, key)
        
        # Check if bucket exists
        bucket_name = "ainews-images"
        print(f"🪣 Checking bucket: {bucket_name}")
        
        try:
            # List buckets
            buckets = supabase.storage.list_buckets()
            print(f"📋 Found {len(buckets)} buckets")
            
            # Check if our bucket exists
            bucket_exists = any(bucket.name == bucket_name for bucket in buckets)
            
            if bucket_exists:
                print(f"✅ Bucket '{bucket_name}' already exists")
            else:
                print(f"❌ Bucket '{bucket_name}' not found")
                print("🛠️  Creating bucket...")
                
                # Create bucket
                result = supabase.storage.create_bucket(bucket_name, {
                    "public": True,  # Make bucket public for image access
                    "allowedMimeTypes": ["image/jpeg", "image/png", "image/webp"],
                    "fileSizeLimit": 500000  # 500KB limit
                })
                
                if result:
                    print(f"✅ Bucket '{bucket_name}' created successfully")
                else:
                    print(f"❌ Failed to create bucket '{bucket_name}'")
                    return False
            
            # Test upload capability
            print("🧪 Testing upload capability...")
            
            # Create a small test file
            import tempfile
            from PIL import Image
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                # Create a small test image
                img = Image.new('RGB', (100, 100), color='red')
                img.save(tmp_file.name, 'JPEG')
                
                # Test upload
                test_filename = "test_upload.jpg"
                
                try:
                    with open(tmp_file.name, 'rb') as f:
                        result = supabase.storage.from_(bucket_name).upload(
                            test_filename, 
                            f,
                            {"content-type": "image/jpeg"}
                        )
                    
                    if result:
                        print("✅ Test upload successful")
                        
                        # Get public URL
                        public_url = supabase.storage.from_(bucket_name).get_public_url(test_filename)
                        print(f"🔗 Public URL: {public_url}")
                        
                        # Clean up test file
                        supabase.storage.from_(bucket_name).remove([test_filename])
                        print("🧹 Test file cleaned up")
                        
                    else:
                        print("❌ Test upload failed")
                        return False
                        
                except Exception as e:
                    print(f"❌ Upload test error: {e}")
                    return False
                
                finally:
                    # Clean up local temp file
                    os.unlink(tmp_file.name)
            
            print("🎉 Supabase Storage is ready for image uploads!")
            return True
            
        except Exception as e:
            print(f"❌ Storage operation error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Supabase connection error: {e}")
        return False

if __name__ == "__main__":
    success = check_supabase_storage()
    sys.exit(0 if success else 1)