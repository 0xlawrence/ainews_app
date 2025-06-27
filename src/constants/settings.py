"""
Application settings and configuration constants.

This module centralizes all numeric thresholds, limits, and configuration
values used throughout the application.
"""

# Text processing limits
TEXT_LIMITS = {
    'toc_short': 50,          # TOC title length
    'title_short': 60,        # Section title length
    'title_min': 10,          # Minimum title length for validation
    'citation_max': 200,      # Citation translation max length
    'summary_point_max': 300, # Summary point max length
    'summary_point_min': 30,  # Summary point min length
    'lead_title_max': 50,     # Lead text title max length
    'lead_body_max': 180,     # Lead text body max length
}

# Performance and concurrency settings
PERFORMANCE = {
    'max_concurrent_llm': 8,        # Max concurrent LLM operations
    'max_concurrent_citations': 8,  # Max concurrent citation generations
    'semaphore_limit': 8,           # General semaphore limit
    'cache_max_size': 1000,         # Max articles in duplicate checker cache
}

# Similarity and matching thresholds
SIMILARITY_THRESHOLDS = {
    'duplicate_jaccard': 0.6,      # Jaccard similarity threshold
    'duplicate_sequence': 0.65,    # Sequence similarity threshold
    'duplicate_main': 0.75,        # Main duplicate threshold (temporarily lowered for better 🆙 detection)
    'context_similarity': 0.55,    # Context analysis similarity (further lowered for 🆙 detection)
    'enhanced_diff_threshold': 0.15, # Enhanced vs basic similarity difference
    'ai_relevance_high': 0.75,     # High AI relevance threshold
    'multi_source_detection': 0.75, # Multi-source topic detection (CRITICAL: raised from dangerous 0.52 to prevent unrelated article grouping)
}

# Content extraction and processing
CONTENT_PROCESSING = {
    'excerpt_length': 500,          # Content excerpt length for comparison
    'max_keywords': 3,              # Max keywords to extract
    'min_japanese_ratio': 0.5,     # Min Japanese char ratio for translation
    'consolidation_threshold_adjustment': 0.25, # Threshold reduction for consolidation
}

# LLM operation settings
LLM_SETTINGS = {
    'retry_delay': 2.0,            # Retry delay in seconds
    'max_retries': 3,              # Max retry attempts
    'timeout_seconds': 30,         # LLM operation timeout
    'summary_max_tokens': 250,     # Max tokens for summary generation
    'title_max_tokens': 150,       # Max tokens for title generation
    'citation_max_tokens': 200,    # Max tokens for citation generation
    'temperature_conservative': 0.1, # Conservative temperature
    'temperature_balanced': 0.2,   # Balanced temperature
}

# Newsletter generation settings
NEWSLETTER = {
    'max_citations_per_article': 3, # Max citations per article
    'target_article_count': 7,      # Target number of articles
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

# LLM Configuration
LLM_CONFIG = {
    'primary_models': ['gemini-2.5-flash'],
    'fallback_models': ['claude-3-7-sonnet-20250219', 'gpt-4o-mini'],
    'max_retries': 3,
    'retry_delay': 2,
    'timeout': 60
}

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