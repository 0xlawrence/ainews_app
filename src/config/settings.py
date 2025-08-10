"""
Configuration settings using Pydantic BaseSettings.

This module centralizes all configuration values including magic numbers,
thresholds, and environment variables with proper type safety.
"""

import os
from typing import Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM-related configuration settings."""

    # API Keys
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    claude_api_key: str = Field(..., env="CLAUDE_API_KEY", alias="anthropic_api_key")

    # Model names
    primary_model: str = Field(default_factory=lambda: os.getenv("PRIMARY_LLM_MODEL", "gemini-2.5-flash"))
    fallback_model: str = Field(default_factory=lambda: os.getenv("FALLBACK_LLM_MODEL", "claude-3-5-sonnet-20241022"))
    final_fallback_model: str = Field(default_factory=lambda: os.getenv("FINAL_FALLBACK_LLM_MODEL", "gpt-4o-mini"))
    topic_naming_model: str = Field(default_factory=lambda: os.getenv("TOPIC_NAMING_MODEL", "gemini-2.5-flash"))

    # Retry settings
    max_retries: int = Field(default=3, env="LLM_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="LLM_RETRY_DELAY")
    timeout: int = Field(default=30, env="LLM_TIMEOUT")

    # Rate limiting
    requests_per_minute: int = Field(default=60, env="LLM_REQUESTS_PER_MINUTE")

    @field_validator("claude_api_key", mode="before")
    @classmethod
    def get_claude_key(cls, v):
        """Get Claude API key from either CLAUDE_API_KEY or ANTHROPIC_API_KEY."""
        if v:
            return v
        return os.getenv("ANTHROPIC_API_KEY", "")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_SERVICE_KEY")

    # Storage settings for image uploads
    supabase_image_bucket: str = Field(default="ainews-images", env="SUPABASE_IMAGE_BUCKET")

    # Connection settings
    max_connections: int = Field(default=10, env="DB_MAX_CONNECTIONS")
    connection_timeout: int = Field(default=30, env="DB_CONNECTION_TIMEOUT")

    @field_validator("supabase_key", mode="before")
    @classmethod
    def get_supabase_key(cls, v):
        """Get Supabase key, preferring SERVICE_KEY over KEY."""
        if v:
            return v
        return os.getenv("SUPABASE_KEY", "")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


class EmbeddingSettings(BaseSettings):
    """Embedding and similarity search settings."""

    # Embedding model
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, env="EMBEDDING_DIMENSIONS")

    # Similarity thresholds (these were previously magic numbers)
    # バランス調整: 真の重複のみ除去、関連記事は保持 - ULTRA CONSERVATIVE
    duplicate_similarity_threshold: float = Field(default=0.85, env="DUPLICATE_SIMILARITY_THRESHOLD")
    consolidation_threshold_adjustment: float = Field(default=0.25, env="CONSOLIDATION_THRESHOLD_ADJUSTMENT")
    # Align with tests expecting 0.55 as default
    minimum_consolidation_threshold: float = Field(default_factory=lambda: float(os.getenv("MIN_CONSOLIDATION_THRESHOLD", "0.55")))

    # Context analysis thresholds - バランス調整: 品質と記事数の両立
    # Align with tests expecting 0.75
    context_similarity_threshold: float = Field(default=0.75, env="CONTEXT_SIMILARITY_THRESHOLD")
    sequel_detection_threshold: float = Field(default=0.8, env="SEQUEL_DETECTION_THRESHOLD")
    enhanced_diff_threshold: float = Field(default=0.15, env="ENHANCED_DIFF_THRESHOLD")  # Enhanced vs basic similarity difference
    multi_source_detection_threshold: float = Field(default=0.85, env="MULTI_SOURCE_DETECTION_THRESHOLD")  # Multi-source topic detection

    # Vector search settings
    max_search_results: int = Field(default=50, env="MAX_SEARCH_RESULTS")
    search_days_back: int = Field(default=7, env="SEARCH_DAYS_BACK")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


class ProcessingSettings(BaseSettings):
    """Content processing and workflow settings."""

    # Article processing limits - increased to ensure sufficient articles
    max_articles_per_run: int = Field(default=30, env="MAX_ARTICLES_PER_RUN")
    max_content_length: int = Field(default=10000, env="MAX_CONTENT_LENGTH")
    min_content_length: int = Field(default=100, env="MIN_CONTENT_LENGTH")
    min_articles_target: int = Field(default=10, env="MIN_ARTICLES_TARGET")

    # Summary generation
    min_bullet_points: int = Field(default=3, env="MIN_BULLET_POINTS")
    max_bullet_points: int = Field(default=4, env="MAX_BULLET_POINTS")
    min_sentence_length: int = Field(default=30, env="MIN_SENTENCE_LENGTH")

    # Text processing limits
    title_short_length: int = Field(default=120, env="TITLE_SHORT_LENGTH")  # Section title length (doubled for Japanese)

    # Quality thresholds - lowered to increase article yield for PRD F-5 compliance
    min_quality_score: float = Field(default=0.7, env="MIN_QUALITY_SCORE")
    # Align with tests expecting 2 as default
    max_forbidden_phrases: int = Field(default=2, env="MAX_FORBIDDEN_PHRASES")

    # Clustering settings
    max_clusters: int = Field(default=8, env="MAX_CLUSTERS")
    min_cluster_size: int = Field(default=2, env="MIN_CLUSTER_SIZE")

    # Performance settings
    async_concurrency_limit: int = Field(default=5, env="ASYNC_CONCURRENCY_LIMIT")
    batch_size: int = Field(default=10, env="BATCH_SIZE")
    
    # Embedding batch processing settings (Phase 3.2b optimization)
    embedding_batch_size: int = Field(default=50, env="EMBEDDING_BATCH_SIZE")  # OpenAI supports up to 2048
    max_concurrent_embedding_batches: int = Field(default=3, env="MAX_CONCURRENT_EMBEDDING_BATCHES")
    embedding_cache_size: int = Field(default=1000, env="EMBEDDING_CACHE_SIZE")
    embedding_cache_memory_mb: float = Field(default=100.0, env="EMBEDDING_CACHE_MEMORY_MB")
    
    # LLM batch processing settings (Phase 3.2c optimization)
    llm_batch_size: int = Field(default=8, env="LLM_BATCH_SIZE")  # Articles per batch
    max_concurrent_llm_batches: int = Field(default=2, env="MAX_CONCURRENT_LLM_BATCHES")  # Prevent rate limiting
    enable_llm_batch_processing: bool = Field(default=True, env="ENABLE_LLM_BATCH_PROCESSING")
    batch_timeout_seconds: int = Field(default=120, env="BATCH_TIMEOUT_SECONDS")  # Per-batch timeout
    
    # Database bulk operations settings (Phase 3.2d optimization)
    db_bulk_insert_size: int = Field(default=50, env="DB_BULK_INSERT_SIZE")  # Records per bulk insert
    enable_db_bulk_operations: bool = Field(default=True, env="ENABLE_DB_BULK_OPERATIONS")
    db_bulk_timeout_seconds: int = Field(default=60, env="DB_BULK_TIMEOUT_SECONDS")  # Per-bulk timeout
    max_concurrent_db_operations: int = Field(default=3, env="MAX_CONCURRENT_DB_OPERATIONS")  # Parallel bulk ops

    # Content processing settings (migrated from constants/settings.py)
    excerpt_length: int = Field(default=500, env="EXCERPT_LENGTH")
    max_keywords: int = Field(default=3, env="MAX_KEYWORDS")
    min_japanese_ratio: float = Field(default=0.5, env="MIN_JAPANESE_RATIO")
    consolidation_threshold_adjustment: float = Field(default=0.25, env="CONSOLIDATION_THRESHOLD_ADJUSTMENT")

    # Similarity weights for duplicate detection (migrated from constants/settings.py)
    title_weight: float = Field(default=0.40, env="TITLE_WEIGHT")
    content_weight: float = Field(default=0.35, env="CONTENT_WEIGHT")
    excerpt_weight: float = Field(default=0.20, env="EXCERPT_WEIGHT")
    source_bonus_weight: float = Field(default=0.05, env="SOURCE_BONUS_WEIGHT")

    # Quality control patterns (migrated from constants/settings.py)
    japanese_char_pattern: str = Field(
        default=r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]',
        env="JAPANESE_CHAR_PATTERN"
    )
    forbidden_phrase_threshold: int = Field(default=1, env="FORBIDDEN_PHRASE_THRESHOLD")
    min_content_quality_score: float = Field(default=0.5, env="MIN_CONTENT_QUALITY_SCORE")
    translation_min_length: int = Field(default=20, env="TRANSLATION_MIN_LENGTH")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


class MonitoringSettings(BaseSettings):
    """Monitoring and logging settings."""

    # LangSmith tracing
    langsmith_api_key: Union[str, None] = Field(default=None, env="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="ai-news-app", env="LANGSMITH_PROJECT")
    enable_tracing: bool = Field(default=True, env="ENABLE_TRACING")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    structured_logging: bool = Field(default=True, env="STRUCTURED_LOGGING")

    # Metrics
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_export_interval: int = Field(default=60, env="METRICS_EXPORT_INTERVAL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


class WorkflowSettings(BaseSettings):
    """Workflow processing configuration (extracted magic numbers)."""
    
    # Content fetching
    default_hours_lookback: int = Field(default=24, env="DEFAULT_HOURS_LOOKBACK")
    min_items_per_source: int = Field(default=3, env="MIN_ITEMS_PER_SOURCE")
    default_source_priority: int = Field(default=999, env="DEFAULT_SOURCE_PRIORITY")
    
    # Article limits (PRD compliance)
    min_newsletter_articles: int = Field(default=7, env="MIN_NEWSLETTER_ARTICLES")
    max_newsletter_articles: int = Field(default=8, env="MAX_NEWSLETTER_ARTICLES")
    
    # Citations and clustering
    max_citations_per_article: int = Field(default=3, env="MAX_CITATIONS_PER_ARTICLE")
    max_cluster_sources: int = Field(default=4, env="MAX_CLUSTER_SOURCES")
    max_similar_articles_context: int = Field(default=5, env="MAX_SIMILAR_ARTICLES_CONTEXT")
    
    # Concurrent processing limits
    max_concurrent_summaries: int = Field(default=5, env="MAX_CONCURRENT_SUMMARIES")
    max_concurrent_images: int = Field(default=5, env="MAX_CONCURRENT_IMAGES")
    
    # Text length limits
    title_truncate_length: int = Field(default=50, env="TITLE_TRUNCATE_LENGTH")
    
    # Monitoring and history
    success_rate_history_limit: int = Field(default=100, env="SUCCESS_RATE_HISTORY_LIMIT")
    
    # Context analysis limits
    max_references_per_article: int = Field(default=3, env="MAX_REFERENCES_PER_ARTICLE")
    max_past_links: int = Field(default=2, env="MAX_PAST_LINKS")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


class AppSettings(BaseSettings):
    """Main application settings that combines all other settings."""

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    workflow: WorkflowSettings = Field(default_factory=WorkflowSettings)

    # Application-level settings
    app_name: str = Field(default="AI News App", env="APP_NAME")
    app_version: str = Field(default="0.1.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # File paths
    sources_file: str = Field(default="sources.json", env="SOURCES_FILE")
    output_dir: str = Field(default="drafts", env="OUTPUT_DIR")
    logs_dir: str = Field(default="logs", env="LOGS_DIR")
    data_dir: str = Field(default="data", env="DATA_DIR")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


# Global settings instance
settings = AppSettings()


def get_settings() -> AppSettings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> AppSettings:
    """Reload settings from environment/file."""
    global settings
    settings = AppSettings()
    return settings
