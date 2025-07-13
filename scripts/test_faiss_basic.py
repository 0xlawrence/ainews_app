#!/usr/bin/env python3
"""
Basic FAISS test script to verify installation and create dummy index.
"""

import json
import numpy as np
from pathlib import Path

# Test FAISS functionality
try:
    import faiss
    version = getattr(faiss, "__version__", "fallback")
    print(f"✅ FAISS imported successfully (version: {version})")
except ImportError as e:
    print(f"❌ FAISS import failed: {e}")
    exit(1)

# Check if metadata exists
metadata_path = Path("data/faiss/metadata.json")
if metadata_path.exists():
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    print(f"📄 Found metadata with {len(metadata)} articles")
    
    # Display first few articles
    for i, article in enumerate(metadata[:3]):
        print(f"  {i+1}. {article['title'][:60]}...")
else:
    print("❌ No metadata.json found")
    exit(1)

# Create a simple test index
print("\n🔧 Testing FAISS index creation...")

# Create index with proper dimension (1536 for text-embedding-3-small)
dimension = 1536
index = faiss.IndexFlatIP(dimension)

print(f"✅ Created FAISS IndexFlatIP with dimension {dimension}")
print(f"   Index type: {type(index)}")
print(f"   Initial vectors: {index.ntotal}")

# Create dummy vectors for testing
n_vectors = len(metadata)
dummy_vectors = np.random.rand(n_vectors, dimension).astype(np.float32)

# Normalize vectors for cosine similarity
for i in range(n_vectors):
    dummy_vectors[i] = dummy_vectors[i] / np.linalg.norm(dummy_vectors[i])

# Add to index
index.add(dummy_vectors)
print(f"✅ Added {n_vectors} dummy vectors to index")
print(f"   Total vectors in index: {index.ntotal}")

# Test search
query_vector = np.random.rand(1, dimension).astype(np.float32)
query_vector = query_vector / np.linalg.norm(query_vector)

scores, indices = index.search(query_vector, min(3, n_vectors))
print(f"\n🔍 Test search results:")
print(f"   Query shape: {query_vector.shape}")
print(f"   Top 3 similarities: {scores[0]}")
print(f"   Top 3 indices: {indices[0]}")

# Test saving index
index_path = Path("data/faiss/index.bin")
try:
    faiss.write_index(index, str(index_path))
    print(f"\n💾 Index saved to: {index_path}")
    
    # Verify file was created
    if index_path.exists():
        file_size = index_path.stat().st_size
        print(f"✅ index.bin created successfully ({file_size} bytes)")
        
        # Test loading
        loaded_index = faiss.read_index(str(index_path))
        print(f"✅ Index loaded successfully ({loaded_index.ntotal} vectors)")
        
        # Clean up test file
        index_path.unlink()
        print("🧹 Test index file removed")
        
    else:
        print("❌ index.bin file was not created")
        
except Exception as e:
    print(f"❌ Error saving/loading index: {e}")

print("\n🎯 FAISS functionality test completed!")
print("   Next step: Install OpenAI API key for embedding generation")
print("   Command: export OPENAI_API_KEY=your_key_here")