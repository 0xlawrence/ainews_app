#!/usr/bin/env python3
"""
Create Supabase Storage bucket using HTTP API directly.
"""

import os
import sys

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_bucket_via_api():
    """Create bucket using Supabase REST API directly."""

    url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not url or not service_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return False

    print(f"🔗 Creating bucket via API: {url}")

    # API endpoint for storage
    api_url = f"{url}/storage/v1/bucket"

    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "apikey": service_key
    }

    # Bucket configuration
    bucket_config = {
        "id": "ainews-images",
        "name": "ainews-images",
        "public": True,
        "file_size_limit": 500000,  # 500KB
        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"]
    }

    try:
        print("🛠️  Creating bucket...")
        response = requests.post(api_url, json=bucket_config, headers=headers)

        if response.status_code == 200:
            print("✅ Bucket created successfully!")
            return True
        elif response.status_code == 409:
            print("ℹ️  Bucket already exists")
            return True
        else:
            print(f"❌ Error creating bucket: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ API request failed: {e}")
        return False

def test_bucket_access():
    """Test if bucket is accessible."""

    url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')

    # List buckets to verify
    api_url = f"{url}/storage/v1/bucket"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key
    }

    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            buckets = response.json()
            bucket_names = [b.get('name', b.get('id', 'unknown')) for b in buckets]
            print(f"📋 Available buckets: {bucket_names}")

            if 'ainews-images' in bucket_names:
                print("✅ ainews-images bucket confirmed")
                return True
            else:
                print("❌ ainews-images bucket not found")
                return False
        else:
            print(f"❌ Failed to list buckets: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Bucket verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Supabase Storage Bucket Setup")
    print("=" * 40)

    created = create_bucket_via_api()
    if created:
        verified = test_bucket_access()
        if verified:
            print("\n🎉 Supabase Storage is ready!")
            print("✅ You can now run image processing tests")
        else:
            print("\n⚠️  Bucket created but verification failed")
    else:
        print("\n❌ Bucket creation failed")
        print("\n📝 Manual setup instructions:")
        print("1. Go to https://supabase.com/dashboard")
        print("2. Select your project")
        print("3. Go to Storage → Create bucket")
        print("4. Name: 'ainews-images', Public: Yes")

    sys.exit(0 if created else 1)
