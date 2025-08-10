"""
FIXED: Embedding management with comprehensive memory management.

This demonstrates how to fix memory leaks in the embedding manager:
- Limited cache sizes with LRU eviction
- Proper resource cleanup
- Memory-aware operations
- Automatic garbage collection
"""

import json
import logging
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Union, Optional
import weakref

import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

from openai import OpenAI

from src.config.settings import get_settings
from src.models.schemas import SummarizedArticle
from src.utils.logger import setup_logging
from src.utils.memory_manager import get_memory_manager, track_memory_usage

logger = setup_logging()


class LRUCache:
    """Memory-aware LRU cache with size limits."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: float = 100.0):
        """Initialize LRU cache with memory limits.
        
        Args:
            max_size: Maximum number of items
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = OrderedDict()
        self.memory_usage = 0
        
        # Register with memory manager
        get_memory_manager().track_cache_object(self)
    
    def get(self, key: str) -> Optional[np.ndarray]:
        """Get item from cache."""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: np.ndarray):
        """Put item in cache with memory management."""
        value_size = value.nbytes
        
        # Check if single item is too large
        if value_size > self.max_memory_bytes:
            logger.warning(f"Item too large for cache: {value_size / 1024 / 1024:.1f}MB")
            return
        
        # Remove existing key if present
        if key in self.cache:
            old_value = self.cache[key]
            self.memory_usage -= old_value.nbytes
            del self.cache[key]
        
        # Evict items until we have space
        while (len(self.cache) >= self.max_size or 
               self.memory_usage + value_size > self.max_memory_bytes):
            if not self.cache:
                break
            
            # Remove least recently used item
            lru_key, lru_value = self.cache.popitem(last=False)
            self.memory_usage -= lru_value.nbytes
            logger.debug(f"Evicted cache item: {lru_key}")
        
        # Add new item
        self.cache[key] = value
        self.memory_usage += value_size
        
        logger.debug(f"Cache: {len(self.cache)}/{self.max_size} items, "
                    f"{self.memory_usage / 1024 / 1024:.1f}MB/{self.max_memory_bytes / 1024 / 1024:.1f}MB")
    
    def clear(self):
        """Clear all cache items."""
        self.cache.clear()
        self.memory_usage = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "memory_mb": self.memory_usage / 1024 / 1024,
            "max_memory_mb": self.max_memory_bytes / 1024 / 1024,
            "memory_usage_percent": (self.memory_usage / self.max_memory_bytes) * 100
        }


class EmbeddingManagerFixed:
    """Fixed embedding manager with comprehensive memory management."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        index_path: str = "data/faiss/index.bin",
        metadata_path: str = "data/faiss/metadata.json",
        cache_size: int = 1000,
        cache_memory_mb: float = 100.0
    ):
        """Initialize embedding manager with memory management.
        
        Args:
            model: OpenAI embedding model
            dimension: Embedding dimension
            index_path: Path to FAISS index file
            metadata_path: Path to metadata file
            cache_size: Maximum cache entries
            cache_memory_mb: Maximum cache memory in MB
        """
        self.model = model
        self.dimension = dimension
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        
        # Initialize memory-aware cache
        self.embedding_cache = LRUCache(cache_size, cache_memory_mb)
        
        # Ensure directories exist
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize OpenAI client
        self.openai_client = self._initialize_openai_client()
        
        # Initialize FAISS index with memory management
        self.index = None
        self.metadata = []
        self._max_vectors_in_memory = 10000  # Limit in-memory vectors
        
        self._load_or_create_index()
        
        # Register for cleanup
        memory_manager = get_memory_manager()
        memory_manager.track_large_object(self)
        memory_manager.add_cleanup_callback(self.cleanup_resources)
        
        logger.info(f"EmbeddingManagerFixed initialized: {dimension}D, cache: {cache_size} items")

    def _initialize_openai_client(self) -> Optional[OpenAI]:
        """Initialize OpenAI client with error handling."""
        try:
            settings = get_settings()
            api_key = settings.llm.openai_api_key
            if not api_key:
                logger.warning("OpenAI API key not found in settings")
                return None
            
            client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            return None

    def _load_or_create_index(self) -> None:
        """Load existing index or create new one with memory limits."""
        try:
            if self.index_path.exists() and self.metadata_path.exists():
                # Check file size before loading
                index_size_mb = self.index_path.stat().st_size / 1024 / 1024
                
                if index_size_mb > 500:  # 500MB limit
                    logger.warning(f"Index file too large ({index_size_mb:.1f}MB), creating new index")
                    self._create_new_index()
                    return
                
                # Load existing index
                if HAS_FAISS:
                    self.index = faiss.read_index(str(self.index_path))
                else:
                    logger.warning("FAISS not available, using fallback index")
                    self._create_new_index()
                    return

                with open(self.metadata_path, encoding='utf-8') as f:
                    self.metadata = json.load(f)

                # Limit metadata in memory
                if len(self.metadata) > self._max_vectors_in_memory:
                    logger.info(f"Limiting metadata to {self._max_vectors_in_memory} recent entries")
                    self.metadata = self.metadata[-self._max_vectors_in_memory:]

                logger.info(
                    f"Loaded FAISS index: {self.index.ntotal if self.index else 0} vectors, "
                    f"{len(self.metadata)} metadata entries, {index_size_mb:.1f}MB"
                )
            else:
                self._create_new_index()

        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            self._create_new_index()

    def _create_new_index(self) -> None:
        """Create new FAISS index."""
        if HAS_FAISS:
            self.index = faiss.IndexFlatIP(self.dimension)
        else:
            # Fallback implementation
            self.index = None
            
        self.metadata = []
        logger.info(f"Created new FAISS index: {self.dimension}D")

    @track_memory_usage("save_index")
    def _save_index(self) -> None:
        """Save index and metadata to disk with memory management."""
        try:
            # Save FAISS index
            if self.index and HAS_FAISS:
                faiss.write_index(self.index, str(self.index_path))

            # Save metadata with compression
            metadata_to_save = self.metadata[-self._max_vectors_in_memory:]
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_to_save, f, separators=(',', ':'))  # Compact format

            logger.info(f"Saved FAISS index: {len(metadata_to_save)} metadata entries")

        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    @track_memory_usage("generate_embedding")
    async def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding with caching and memory management."""
        if not self.openai_client:
            logger.warning("OpenAI client not available")
            return None

        # Create cache key
        cache_key = f"{self.model}:{hash(text)}"
        
        # Check cache first
        cached_embedding = self.embedding_cache.get(cache_key)
        if cached_embedding is not None:
            logger.debug("Retrieved embedding from cache")
            return cached_embedding

        try:
            # Clean and prepare text
            clean_text = text.replace('\n', ' ').strip()
            if len(clean_text) > 8000:  # OpenAI limit
                clean_text = clean_text[:8000]

            # Prepare embedding parameters
            embedding_params = {
                "model": self.model,
                "input": clean_text,
                "encoding_format": "float"
            }

            # Add dimensions parameter for text-embedding-3-* models
            if "text-embedding-3" in self.model and self.dimension != 3072:
                embedding_params["dimensions"] = self.dimension

            # Generate embedding
            response = self.openai_client.embeddings.create(**embedding_params)
            embedding = np.array(response.data[0].embedding, dtype=np.float32)

            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)

            # Cache the embedding
            self.embedding_cache.put(cache_key, embedding)

            logger.debug(f"Generated and cached embedding: {embedding.shape}, text length: {len(clean_text)}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def cleanup_resources(self):
        """Clean up all resources to prevent memory leaks."""
        logger.info("Cleaning up EmbeddingManager resources")
        
        # Clear cache
        if hasattr(self, 'embedding_cache'):
            self.embedding_cache.clear()
        
        # Clear metadata if too large
        if hasattr(self, 'metadata') and len(self.metadata) > 1000:
            self.metadata = self.metadata[-1000:]  # Keep recent 1000
            logger.info("Truncated metadata to 1000 recent entries")
        
        # Clear FAISS index if too large
        if hasattr(self, 'index') and self.index and self.index.ntotal > self._max_vectors_in_memory:
            logger.warning(f"Index has {self.index.ntotal} vectors, clearing to prevent memory issues")
            self._create_new_index()

    def get_memory_usage_stats(self) -> dict:
        """Get detailed memory usage statistics."""
        stats = {
            "cache_stats": self.embedding_cache.get_stats() if hasattr(self, 'embedding_cache') else {},
            "index_vectors": self.index.ntotal if self.index else 0,
            "metadata_count": len(self.metadata) if hasattr(self, 'metadata') else 0,
            "estimated_index_memory_bytes": 0,
            "estimated_metadata_memory_bytes": 0
        }
        
        # Estimate memory usage
        if self.index and self.index.ntotal > 0:
            # Approximate: 4 bytes per float * dimension * number of vectors
            stats["estimated_index_memory_bytes"] = 4 * self.dimension * self.index.ntotal
        
        if hasattr(self, 'metadata'):
            # Rough estimate: 200 bytes per metadata entry
            stats["estimated_metadata_memory_bytes"] = len(self.metadata) * 200
        
        return stats

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup_resources()
        except Exception:
            pass  # Ignore errors in destructor