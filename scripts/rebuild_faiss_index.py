#!/usr/bin/env python3
"""
FAISS Index Rebuild Script

This script rebuilds the FAISS index from existing metadata.json
to recover from the fallback implementation issue.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(str(Path(__file__).parent.parent / ".env"))
except ImportError:
    pass

from src.utils.embedding_manager import EmbeddingManager
from src.config.settings import get_settings
from src.utils.logger import setup_logging

logger = setup_logging()


async def rebuild_faiss_index():
    """Rebuild FAISS index from existing metadata."""
    
    logger.info("Starting FAISS index rebuild from metadata")
    
    # Initialize embedding manager
    embedding_manager = EmbeddingManager()
    
    # Check if metadata exists
    metadata_path = Path("data/faiss/metadata.json")
    if not metadata_path.exists():
        logger.error(f"Metadata file not found: {metadata_path}")
        return False
    
    # Load existing metadata
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata_entries = json.load(f)
    
    logger.info(f"Found {len(metadata_entries)} articles in metadata")
    
    # Clear existing index and create fresh one
    embedding_manager._create_new_index()
    embedding_manager.metadata = []
    
    successful_rebuilds = 0
    
    for i, entry in enumerate(metadata_entries):
        try:
            article_id = entry.get("article_id")
            embedding_text = entry.get("embedding_text", "")
            
            # Use the full content if embedding_text is truncated
            if embedding_text.endswith("..."):
                # Reconstruct from available fields
                title = entry.get("title", "")
                content_summary = entry.get("content_summary", "")
                embedding_text = f"{title}\n{content_summary}"
            
            logger.info(f"Rebuilding embedding for article {i+1}/{len(metadata_entries)}: {article_id}")
            
            # Generate new embedding
            embedding = await embedding_manager.generate_embedding(embedding_text)
            if embedding is None:
                logger.warning(f"Failed to generate embedding for {article_id}")
                continue
            
            # Add to FAISS index
            embedding_manager.index.add(embedding.reshape(1, -1))
            
            # Add metadata entry
            embedding_manager.metadata.append(entry)
            
            successful_rebuilds += 1
            logger.debug(f"Successfully rebuilt {article_id}")
            
        except Exception as e:
            logger.error(f"Failed to rebuild article {entry.get('article_id', 'unknown')}: {e}")
            continue
    
    # Save the rebuilt index
    embedding_manager._save_index()
    
    # Verify the rebuild
    stats = embedding_manager.get_index_stats()
    
    logger.info(
        "FAISS index rebuild completed",
        successful_rebuilds=successful_rebuilds,
        total_articles=len(metadata_entries),
        index_stats=stats
    )
    
    # Verify index file was created
    index_path = Path("data/faiss/index.bin")
    if index_path.exists():
        file_size = index_path.stat().st_size
        logger.info(f"✅ index.bin file created successfully ({file_size} bytes)")
        return True
    else:
        logger.error("❌ index.bin file was not created")
        return False


async def test_similarity_search():
    """Test similarity search functionality after rebuild."""
    
    logger.info("Testing similarity search functionality")
    
    embedding_manager = EmbeddingManager()
    
    # Test search with a query
    test_query = "Anthropic economic impact AI jobs"
    similar_articles = await embedding_manager.search_by_text(
        query_text=test_query,
        top_k=3,
        similarity_threshold=0.5
    )
    
    logger.info(
        "Similarity search test completed",
        query=test_query,
        results_found=len(similar_articles),
        similarities=[round(a["similarity_score"], 3) for a in similar_articles[:3]]
    )
    
    if similar_articles:
        logger.info("✅ F-16 context analysis system is now functional")
        for i, article in enumerate(similar_articles[:3]):
            logger.info(
                f"Similar article {i+1}",
                title=article["title"][:50] + "...",
                similarity=round(article["similarity_score"], 3)
            )
        return True
    else:
        logger.warning("⚠️ No similar articles found - may need adjustment")
        return False


if __name__ == "__main__":
    import time
    start_time = time.time()
    
    # Check OpenAI API key via settings
    try:
        settings = get_settings()
        if not settings.llm.openai_api_key:
            logger.error("OPENAI_API_KEY not found in configuration")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        sys.exit(1)
    
    # Run rebuild
    success = asyncio.run(rebuild_faiss_index())
    
    if success:
        # Test functionality
        asyncio.run(test_similarity_search())
        
        execution_time = time.time() - start_time
        logger.info(f"✅ FAISS index rebuild completed successfully in {execution_time:.2f} seconds")
        sys.exit(0)
    else:
        logger.error("❌ FAISS index rebuild failed")
        sys.exit(1)