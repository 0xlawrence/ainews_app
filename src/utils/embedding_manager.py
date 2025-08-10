"""
Embedding management for article similarity search.

This module handles OpenAI embeddings generation and FAISS vector search
for contextual article analysis and relationship detection.
"""

# Standard library imports
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Union, Optional

# Third-party imports
import numpy as np
import weakref
from collections import OrderedDict

# ---------------------------------------------------------------------------
# Optional FAISS import
# ---------------------------------------------------------------------------
#   • Linux (GitHub Actions) では `requirements.txt` で faiss-cpu がインストール
#   • macOS / Windows ローカル開発ではビルド環境が整っていない場合が多く、
#     ImportError が発生しやすい。
#   • そこで軽量フォールバックとして scikit-learn の cosine_similarity を
#     使ったシンプルなインデックスを用意し、最低限の開発・テストを可能に
#     する。（本番運用は FAISS 推奨）
# ---------------------------------------------------------------------------

try:
    import faiss  # type: ignore
except Exception:  # pylint: disable=broad-except
    import numpy as _np
    from sklearn.metrics.pairwise import cosine_similarity as _cos_sim  # type: ignore

    class _SklearnFlatIP:  # pragma: no cover – fallback implementation
        """FAISS `IndexFlatIP` 互換の最小実装 (cosine similarity)。"""

        def __init__(self, dim: int):
            self.dim = dim
            self._vectors: list[_np.ndarray] = []

        # --- FAISS 互換プロパティ ------------------------------------------------
        @property
        def ntotal(self) -> int:  # noqa: N802 – mimic FAISS API
            return len(self._vectors)

        # --- FAISS 互換メソッド --------------------------------------------------
        def add(self, vecs: _np.ndarray) -> None:  # noqa: N802 – mimic FAISS API
            if vecs.ndim != 2 or vecs.shape[1] != self.dim:
                raise ValueError("Vector shape mismatch for fallback index")
            self._vectors.extend(vecs.copy())

        def search(self, query: _np.ndarray, k: int):  # noqa: N802 – mimic FAISS API
            if not self._vectors:
                # Return empty results in FAISS 互換 shape
                return _np.zeros((1, 0), dtype=_np.float32), _np.full((1, 0), -1, dtype=_np.int32)

            all_vecs = _np.vstack(self._vectors)
            sims = _cos_sim(query, all_vecs).astype(_np.float32)

            # Top-k indices (descending order)
            topk_idx = _np.argsort(-sims, axis=1)[:, :k]
            topk_scores = _np.take_along_axis(sims, topk_idx, axis=1)
            return topk_scores, topk_idx

    class _FaissFallbackModule:  # pragma: no cover – dynamic stub
        IndexFlatIP = _SklearnFlatIP

        @staticmethod
        def read_index(_path: str):  # noqa: D401 – simple stub
            raise RuntimeError("FAISS not available – cannot read index file")

        @staticmethod
        def write_index(_index, _path: str) -> None:  # noqa: D401 – simple stub
            pass  # Silently ignore

    # Inject stub under name `faiss` so downstream code works transparently
    import sys as _sys

    _sys.modules.setdefault("faiss", _FaissFallbackModule())
    import faiss  # type: ignore  # noqa: E402 – after stub injection

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


class EmbeddingManager:
    """Manages embeddings and similarity search using OpenAI + FAISS with memory management."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        index_path: str = "data/faiss/index.bin",
        metadata_path: str = "data/faiss/metadata.json",
        cache_size: Optional[int] = None,
        cache_memory_mb: Optional[float] = None
    ):
        """
        Initialize embedding manager with memory management and optimized batch processing.

        Args:
            model: OpenAI embedding model
            dimension: Embedding dimension
            index_path: Path to FAISS index file
            metadata_path: Path to metadata file
            cache_size: Maximum cache entries (uses settings if None)
            cache_memory_mb: Maximum cache memory in MB (uses settings if None)
        """
        self.settings = get_settings()
        self.model = model
        self.dimension = dimension
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        
        # Use configuration-based cache settings with fallbacks
        effective_cache_size = cache_size or self.settings.processing.embedding_cache_size
        effective_cache_memory = cache_memory_mb or self.settings.processing.embedding_cache_memory_mb
        
        # Initialize memory-aware cache with optimized settings
        self.embedding_cache = LRUCache(effective_cache_size, effective_cache_memory)
        
        # Ensure directories exist
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize OpenAI client using settings
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
        
        logger.info(f"EmbeddingManager initialized: {dimension}D, cache: {cache_size} items")

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
                self.index = faiss.read_index(str(self.index_path))

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

        # Create flat index for cosine similarity
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        logger.info(f"Created new FAISS index: {self.dimension}D")

    @track_memory_usage("save_index")
    def _save_index(self) -> None:
        """Save index and metadata to disk with memory management."""
        try:
            # Save FAISS index
            if self.index:
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

    @track_memory_usage("generate_embeddings_batch")
    async def generate_embeddings_batch(
        self, 
        texts: list[str], 
        batch_size: int = 100,
        max_concurrent_batches: int = 3
    ) -> list[Optional[np.ndarray]]:
        """
        Generate embeddings for multiple texts using batch processing.
        
        This method significantly improves performance by:
        - Using OpenAI's batch embedding API (up to 2048 inputs per request)
        - Processing multiple batches concurrently
        - Leveraging cache for already processed texts
        - Maintaining input order in results
        
        Args:
            texts: List of texts to generate embeddings for
            batch_size: Number of texts per batch (max 2048 for OpenAI)
            max_concurrent_batches: Maximum concurrent batch requests
            
        Returns:
            List of embeddings in same order as input texts (None for failed items)
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available for batch processing")
            return [None] * len(texts)
        
        if not texts:
            return []
            
        # Step 1: Check cache and prepare uncached texts
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            cache_key = f"{self.model}:{hash(text)}"
            cached_embedding = self.embedding_cache.get(cache_key)
            
            if cached_embedding is not None:
                results[i] = cached_embedding
                logger.debug(f"Retrieved embedding {i} from cache")
            else:
                uncached_indices.append(i)
                
                # Clean and prepare text
                clean_text = text.replace('\n', ' ').strip()
                if len(clean_text) > 8000:  # OpenAI limit
                    clean_text = clean_text[:8000]
                uncached_texts.append(clean_text)
        
        if not uncached_texts:
            logger.info(f"All {len(texts)} embeddings retrieved from cache")
            return results
            
        logger.info(f"Processing {len(uncached_texts)} uncached embeddings in batches of {batch_size}")
        
        # Step 2: Create batches for uncached texts
        batches = []
        batch_indices = []
        
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i:i + batch_size]
            batch_idx = uncached_indices[i:i + batch_size]
            batches.append(batch_texts)
            batch_indices.append(batch_idx)
        
        # Step 3: Process batches concurrently with semaphore
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        async def process_batch(batch_texts: list[str], batch_idx: list[int]) -> list[tuple[int, Optional[np.ndarray]]]:
            """Process a single batch of texts."""
            async with semaphore:
                try:
                    # Prepare embedding parameters
                    embedding_params = {
                        "model": self.model,
                        "input": batch_texts,  # Send entire batch
                        "encoding_format": "float"
                    }
                    
                    # Add dimensions parameter for text-embedding-3-* models
                    if "text-embedding-3" in self.model and self.dimension != 3072:
                        embedding_params["dimensions"] = self.dimension
                    
                    # Make batch API call
                    logger.debug(f"Making batch embedding request for {len(batch_texts)} texts")
                    response = self.openai_client.embeddings.create(**embedding_params)
                    
                    # Process results
                    batch_results = []
                    for j, embedding_data in enumerate(response.data):
                        try:
                            # Convert to numpy array and normalize
                            embedding = np.array(embedding_data.embedding, dtype=np.float32)
                            embedding = embedding / np.linalg.norm(embedding)
                            
                            # Cache the embedding
                            original_idx = batch_idx[j]
                            original_text = texts[original_idx]
                            cache_key = f"{self.model}:{hash(original_text)}"
                            self.embedding_cache.put(cache_key, embedding)
                            
                            batch_results.append((original_idx, embedding))
                            
                        except Exception as e:
                            logger.error(f"Failed to process embedding {j} in batch: {e}")
                            batch_results.append((batch_idx[j], None))
                    
                    logger.debug(f"Successfully processed batch: {len(batch_results)} embeddings")
                    return batch_results
                    
                except Exception as e:
                    logger.error(f"Batch embedding generation failed: {e}")
                    # Return None for all items in failed batch
                    return [(idx, None) for idx in batch_idx]
        
        # Step 4: Execute all batches concurrently
        batch_tasks = [
            process_batch(batch_texts, batch_idx) 
            for batch_texts, batch_idx in zip(batches, batch_indices)
        ]
        
        start_time = time.time()
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        processing_time = time.time() - start_time
        
        # Step 5: Merge batch results back into original order
        successful_batches = 0
        total_embeddings_generated = 0
        
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Batch processing exception: {batch_result}")
                continue
                
            successful_batches += 1
            for original_idx, embedding in batch_result:
                results[original_idx] = embedding
                if embedding is not None:
                    total_embeddings_generated += 1
        
        # Step 6: Log performance metrics
        cache_hits = len(texts) - len(uncached_texts)
        success_rate = (total_embeddings_generated / len(uncached_texts)) * 100 if uncached_texts else 100
        
        logger.info(
            f"Batch embedding generation completed: "
            f"{total_embeddings_generated}/{len(uncached_texts)} generated, "
            f"{cache_hits} cache hits, "
            f"{success_rate:.1f}% success rate, "
            f"{processing_time:.2f}s total, "
            f"{len(batches)} batches processed"
        )
        
        return results

    async def add_article(
        self,
        article: SummarizedArticle,
        save_immediately: bool = True
    ) -> bool:
        """Add article to embedding index."""

        try:
            raw_article = article.filtered_article.raw_article

            # Create text for embedding
            embedding_text = f"{raw_article.title}\n{raw_article.content}"
            if len(article.summary.summary_points) > 0:
                embedding_text += "\n" + "\n".join(article.summary.summary_points)

            # Generate embedding
            embedding = await self.generate_embedding(embedding_text)
            if embedding is None:
                return False

            # Add to index
            self.index.add(embedding.reshape(1, -1))

            # Add metadata
            metadata_entry = {
                "article_id": raw_article.id,
                "title": raw_article.title,
                "url": str(raw_article.url),
                "published_date": raw_article.published_date.isoformat(),
                "source_id": raw_article.source_id,
                "content_summary": " ".join(article.summary.summary_points),
                "embedding_text": embedding_text[:500] + "..." if len(embedding_text) > 500 else embedding_text,
                "added_at": datetime.now().isoformat(),
                "topic_cluster": None,  # Will be filled by clustering
                "ai_relevance_score": article.filtered_article.ai_relevance_score
            }

            self.metadata.append(metadata_entry)

            if save_immediately:
                self._save_index()

            logger.info(
                "Added article to embedding index",
                article_id=raw_article.id,
                total_vectors=self.index.ntotal
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to add article to index",
                article_id=article.filtered_article.raw_article.id,
                error=str(e)
            )
            return False

    async def search_similar_articles(
        self,
        query_article: SummarizedArticle,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> list[dict]:
        """Search for similar articles in the index."""

        try:
            if self.index.ntotal == 0:
                logger.debug("No articles in index for similarity search")
                return []

            raw_article = query_article.filtered_article.raw_article

            # Create text for embedding
            query_text = f"{raw_article.title}\n{raw_article.content}"
            if len(query_article.summary.summary_points) > 0:
                query_text += "\n" + "\n".join(query_article.summary.summary_points)

            # Generate embedding
            query_embedding = await self.generate_embedding(query_text)
            if query_embedding is None:
                return []

            # Search similar vectors
            scores, indices = self.index.search(
                query_embedding.reshape(1, -1),
                min(top_k * 2, self.index.ntotal)  # Get more results to filter
            )

            # Filter results by similarity threshold
            similar_articles = []
            for score, idx in zip(scores[0], indices[0], strict=False):
                if idx == -1:  # FAISS returns -1 for invalid indices
                    break

                similarity = float(score)  # Cosine similarity (higher is better)

                if similarity >= similarity_threshold:
                    metadata = self.metadata[idx].copy()
                    metadata["similarity_score"] = similarity
                    similar_articles.append(metadata)

            # Sort by similarity score (descending)
            similar_articles.sort(key=lambda x: x["similarity_score"], reverse=True)

            # Limit to top_k results
            similar_articles = similar_articles[:top_k]

            logger.info(
                "Found similar articles",
                query_article_id=raw_article.id,
                similar_count=len(similar_articles),
                top_similarity=similar_articles[0]["similarity_score"] if similar_articles else 0
            )

            return similar_articles

        except Exception as e:
            logger.error(
                "Failed to search similar articles",
                query_article_id=query_article.filtered_article.raw_article.id,
                error=str(e)
            )
            return []

    async def search_by_text(
        self,
        query_text: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> list[dict]:
        """Search for articles similar to given text."""

        try:
            if self.index.ntotal == 0:
                return []

            # Generate embedding for query
            query_embedding = await self.generate_embedding(query_text)
            if query_embedding is None:
                return []

            # Search
            scores, indices = self.index.search(
                query_embedding.reshape(1, -1),
                min(top_k * 2, self.index.ntotal)
            )

            # Filter and format results
            similar_articles = []
            for score, idx in zip(scores[0], indices[0], strict=False):
                if idx == -1:
                    break

                similarity = float(score)
                if similarity >= similarity_threshold:
                    metadata = self.metadata[idx].copy()
                    metadata["similarity_score"] = similarity
                    similar_articles.append(metadata)

            similar_articles.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_articles[:top_k]

        except Exception as e:
            logger.error("Failed to search by text", error=str(e))
            return []

    def get_index_stats(self) -> dict:
        """Get statistics about the current index."""

        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "metadata_count": len(self.metadata),
            "dimension": self.dimension,
            "model": self.model,
            "index_file_exists": self.index_path.exists(),
            "metadata_file_exists": self.metadata_path.exists(),
            "index_size_mb": self.index_path.stat().st_size / (1024*1024) if self.index_path.exists() else 0
        }

    def clear_old_articles(self, days_to_keep: int = 30) -> int:
        """Remove articles older than specified days."""

        try:
            cutoff_date = datetime.now().replace(
                day=datetime.now().day - days_to_keep
            )

            # Find indices to remove
            indices_to_remove = []
            for i, metadata in enumerate(self.metadata):
                article_date = datetime.fromisoformat(metadata["added_at"])
                if article_date < cutoff_date:
                    indices_to_remove.append(i)

            if not indices_to_remove:
                return 0

            # Remove from metadata (reverse order to maintain indices)
            for i in reversed(indices_to_remove):
                del self.metadata[i]

            # For FAISS, we need to rebuild the index (no direct deletion)
            if indices_to_remove:
                logger.info(f"Rebuilding FAISS index after removing {len(indices_to_remove)} old articles")
                self._rebuild_index()

            return len(indices_to_remove)

        except Exception as e:
            logger.error("Failed to clear old articles", error=str(e))
            return 0

    def _rebuild_index(self) -> None:
        """Rebuild FAISS index from current metadata."""

        # This is a simplified rebuild - in production, you'd want to
        # re-generate embeddings from stored articles
        logger.warning("Index rebuild not fully implemented - creating new empty index")
        self._create_new_index()
        self._save_index()

    async def sync_with_supabase(self, days_back: int = 7) -> int:
        """
        Sync FAISS index with Supabase contextual articles.

        Args:
            days_back: Number of days of articles to sync

        Returns:
            Number of articles synced
        """
        try:
            from src.utils.supabase_client import get_recent_contextual_articles

            # Get recent articles from Supabase
            contextual_articles = await get_recent_contextual_articles(
                days_back=days_back,
                limit=1000
            )

            if not contextual_articles:
                logger.info("No contextual articles found in Supabase to sync")
                return 0

            # Clear current index and rebuild with Supabase data
            self._create_new_index()
            self.metadata = []

            synced_count = 0
            for article in contextual_articles:
                try:
                    # Skip if no embedding
                    if not article.get("embedding"):
                        continue

                    # Convert embedding to numpy array with proper handling of string format
                    embedding_data = article["embedding"]
                    if isinstance(embedding_data, str):
                        # Handle string format (e.g., "[0.1, 0.2, ...]")
                        try:
                            # First try JSON parsing
                            embedding_data = json.loads(embedding_data)
                        except json.JSONDecodeError:
                            try:
                                # Try parsing as Python list string (fallback)
                                embedding_data = eval(embedding_data)
                            except (ValueError, SyntaxError):
                                logger.warning(
                                    f"Failed to parse embedding for article {article.get('article_id')}: invalid format"
                                )
                                continue

                    # Convert to numpy array
                    try:
                        embedding = np.array(embedding_data, dtype=np.float32)
                        if embedding.shape[0] != self.dimension:
                            logger.warning(
                                f"Embedding dimension mismatch for article {article.get('article_id')}: "
                                f"expected {self.dimension}, got {embedding.shape[0]}"
                            )
                            continue
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Failed to convert embedding to numpy array for article {article.get('article_id')}: {e}"
                        )
                        continue

                    # Normalize for cosine similarity
                    embedding = embedding / np.linalg.norm(embedding)

                    # Add to FAISS index
                    self.index.add(embedding.reshape(1, -1))

                    # Add metadata
                    metadata_entry = {
                        "article_id": article["article_id"],
                        "title": article["title"],
                        "url": article.get("source_url", ""),
                        "published_date": article["published_date"],
                        "source_id": article.get("source_id", ""),
                        "content_summary": article["content_summary"],
                        "embedding_text": article["content_summary"][:500] + "...",
                        "added_at": article.get("created_at", datetime.now().isoformat()),
                        "topic_cluster": article.get("topic_cluster"),
                        "ai_relevance_score": article.get("ai_relevance_score", 0.0),
                        "japanese_title": article.get("japanese_title"),
                        "is_update": article.get("is_update", False)
                    }

                    self.metadata.append(metadata_entry)
                    synced_count += 1

                except Exception as e:
                    logger.warning(
                        f"Failed to sync article {article.get('article_id')}: {e}"
                    )
                    continue

            # Save synced index
            self._save_index()

            logger.info(
                f"Synced {synced_count} articles from Supabase to FAISS index"
            )

            return synced_count

        except Exception as e:
            logger.error(f"Failed to sync with Supabase: {e}")
            return 0

    async def get_or_create_embedding(
        self,
        article_id: str,
        text: str,
        force_regenerate: bool = False
    ) -> Optional[np.ndarray]:
        """
        Get existing embedding or create new one.

        Args:
            article_id: Unique article identifier
            text: Text to generate embedding for
            force_regenerate: Force regeneration even if exists

        Returns:
            Embedding vector or None
        """

        if not force_regenerate:
            # Check if embedding already exists in metadata
            for _i, meta in enumerate(self.metadata):
                if meta["article_id"] == article_id:
                    logger.debug(f"Found existing embedding for {article_id}")
                    # Return the embedding from FAISS
                    # Note: FAISS doesn't support direct retrieval by index
                    # This is a limitation - in production, store embeddings separately
                    return None

        # Generate new embedding
        return await self.generate_embedding(text)

    # ---------------------------------------------------------------------
    # Compatibility helpers
    # ---------------------------------------------------------------------

    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Alias maintained for backward-compatibility.

        A number of downstream utilities – e.g. ``TopicClusterer`` – still
        call ``EmbeddingManager.get_embedding``.  The method was renamed to
        :py:meth:`generate_embedding` during Phase-3 refactor, which broke
        those callers at runtime ("object has no attribute 'get_embedding'").

        This thin wrapper simply forwards to :py:meth:`generate_embedding` so
        that both names are supported.
        """

        return await self.generate_embedding(text)

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


# Convenience functions
async def create_embedding_manager() -> EmbeddingManager:
    """Create and initialize embedding manager."""
    return EmbeddingManager()


async def add_articles_to_index(
    articles: list[SummarizedArticle],
    embedding_manager: Union[EmbeddingManager, None] = None
) -> int:
    """
    Add multiple articles to embedding index.

    Args:
        articles: List of summarized articles to add
        embedding_manager: Optional existing manager

    Returns:
        Number of articles successfully added
    """

    if embedding_manager is None:
        embedding_manager = await create_embedding_manager()

    added_count = 0

    for i, article in enumerate(articles):
        try:
            success = await embedding_manager.add_article(
                article, save_immediately=(i == len(articles) - 1)  # Save only on last
            )
            if success:
                added_count += 1
        except Exception as e:
            logger.error(
                "Failed to add article to index",
                article_id=article.filtered_article.raw_article.id,
                error=str(e)
            )

    logger.info(
        "Batch added articles to embedding index",
        added_count=added_count,
        total_articles=len(articles)
    )

    return added_count

# ---------------------------------------------------------------------------
# 共通依存
# ---------------------------------------------------------------------------
