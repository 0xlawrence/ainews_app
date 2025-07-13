"""
Application settings and configuration constants.

This module is **deprecated**. All new code should import
`src.config.settings` and use `get_settings()` instead.
For backward compatibility, we expose read-only snapshots of
commonly used dictionaries, constructed from the current
AppSettings instance so values stay in sync.
"""

from __future__ import annotations

import warnings
from types import MappingProxyType

from src.config.settings import get_settings

_s = get_settings()

# Emit deprecation warning once per interpreter
warnings.warn(
    "`src.constants.settings` is deprecated. Import from `src.config.settings` instead.",
    DeprecationWarning,
    stacklevel=2,
)

# ---------------------------------------------------------------------------
# Helper builders – create read-only dictionaries that mirror new settings
# ---------------------------------------------------------------------------


def _build_similarity_thresholds():
    return {
        "duplicate_jaccard": _s.embedding.duplicate_similarity_threshold,
        "duplicate_sequence": _s.embedding.duplicate_similarity_threshold,
        "duplicate_main": _s.embedding.duplicate_similarity_threshold,
        "context_similarity": _s.embedding.context_similarity_threshold,
        "enhanced_diff_threshold": 0.15,
        "ai_relevance_high": 0.75,
        "multi_source_detection": 0.85,
    }


def _build_llm_settings():
    return {
        "retry_delay": _s.llm.retry_delay,
        "max_retries": _s.llm.max_retries,
        "timeout_seconds": _s.llm.timeout,
        "summary_max_tokens": 250,
        "title_max_tokens": 150,
        "citation_max_tokens": 200,
        "temperature_conservative": 0.1,
        "temperature_balanced": 0.2,
    }


# ---------------------------------------------------------------------------
# Public (legacy) constants
# ---------------------------------------------------------------------------

SIMILARITY_THRESHOLDS = MappingProxyType(_build_similarity_thresholds())
LLM_SETTINGS = MappingProxyType(_build_llm_settings())

# The rest of the legacy constants remain unchanged below

# Text processing limits
TEXT_LIMITS = {
    'toc_short': 70,          # TOC title length (increased for Japanese)
    'title_short': 120,       # Section title length (doubled for Japanese)
    'title_min': 10,          # Minimum title length for validation
    'citation_max': 200,      # Citation translation max length
    'summary_point_max': 300, # Summary point max length
    'summary_point_min': 30,  # Summary point min length
    'lead_title_max': 80,     # Lead text title max length (increased for Japanese)
    'lead_body_max': 180,     # Lead text body max length
}

# Performance and concurrency settings
PERFORMANCE = {
    'max_concurrent_llm': 8,        # Max concurrent LLM operations
    'max_concurrent_citations': 8,  # Max concurrent citation generations
    'semaphore_limit': 8,           # General semaphore limit
    'cache_max_size': 1000,         # Max articles in duplicate checker cache
}

# Legacy constants removed - all moved to config/settings.py with Pydantic validation

# Content extraction and processing
CONTENT_PROCESSING = {
    'excerpt_length': 500,          # Content excerpt length for comparison
    'max_keywords': 3,              # Max keywords to extract
    'min_japanese_ratio': 0.5,     # Min Japanese char ratio for translation
    'consolidation_threshold_adjustment': 0.25, # Threshold reduction for consolidation
}

# Newsletter generation settings
NEWSLETTER = {
    'max_citations_per_article': 3, # Max citations per article
    'target_article_count': 10,     # Target number of articles (increased for more content)
    'max_articles_processing': 30,  # Max articles to process
    'lead_text_sentences': 3,       # Max sentences in lead text
}

# Validation and quality controls
QUALITY_CONTROLS = {
    'forbidden_phrase_threshold': 1, # Max forbidden phrases allowed
    'min_content_quality_score': 0.5, # Min content quality score
    'translation_min_length': 20,   # Min translation length
    'japanese_char_patterns': r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]',
}

# File and output settings
OUTPUT_SETTINGS = {
    'default_output_dir': 'drafts/',
    'log_retention_days': 30,
    'max_log_file_size_mb': 100,
}

# Weighting factors for enhanced similarity calculation
SIMILARITY_WEIGHTS = {
    'title': 0.40,          # Title similarity weight
    'content': 0.35,        # Content similarity weight
    'excerpt': 0.20,        # Content excerpt weight
    'source_bonus': 0.05,   # Cross-source bonus weight
}

# Time and date settings
TIME_SETTINGS = {
    'processing_timeout_minutes': 10,   # Max processing time
    'article_freshness_hours': 24,      # Article freshness for filtering
    'cache_expiry_hours': 24,           # Cache expiry time
}

# Legacy LLM_CONFIG removed - moved to config/settings.py LLMSettings

# Embedding Settings
EMBEDDING_SETTINGS = {
    "current": {
        "model": "text-embedding-3-small",
        "dimension": 1536,
        "cost_per_1m_tokens": 0.02
    },
    "large_full": {
        "model": "text-embedding-3-large",
        "dimension": 3072,
        "cost_per_1m_tokens": 0.13
    },
    "large_compressed": {
        "model": "text-embedding-3-large",
        "dimension": 1024,  # Good balance
        "cost_per_1m_tokens": 0.13
    },
    "large_ultra_compressed": {
        "model": "text-embedding-3-large",
        "dimension": 256,   # Ultra efficient
        "cost_per_1m_tokens": 0.13
    }
}
