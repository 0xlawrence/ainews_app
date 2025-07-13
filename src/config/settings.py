"""
Configuration settings using Pydantic BaseSettings.

This module centralizes all configuration values including magic numbers,
thresholds, and environment variables with proper type safety.
"""

import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM-related configuration settings."""

    # API Keys
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    claude_api_key: str = Field(..., env="CLAUDE_API_KEY", alias="anthropic_api_key")

    # Model names
    primary_model: str = Field(default="gemini-2.5-flash", env="PRIMARY_LLM_MODEL")
    fallback_model: str = Field(default="claude-3-5-sonnet-20241022", env="FALLBACK_LLM_MODEL")
    final_fallback_model: str = Field(default="gpt-4o-mini", env="FINAL_FALLBACK_LLM_MODEL")
    topic_naming_model: str = Field(default="gemini-1.5-flash", env="TOPIC_NAMING_MODEL")

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
    duplicate_similarity_threshold: float = Field(default=0.88, env="DUPLICATE_SIMILARITY_THRESHOLD")
    consolidation_threshold_adjustment: float = Field(default=0.25, env="CONSOLIDATION_THRESHOLD_ADJUSTMENT")
    minimum_consolidation_threshold: float = Field(default=0.6, env="MIN_CONSOLIDATION_THRESHOLD")

    # Context analysis thresholds - バランス調整: 品質と記事数の両立
    context_similarity_threshold: float = Field(default=0.6, env="CONTEXT_SIMILARITY_THRESHOLD")  # 品質確保しつつ記事数維持
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
    max_articles_per_run: int = Field(default=50, env="MAX_ARTICLES_PER_RUN")
    max_content_length: int = Field(default=10000, env="MAX_CONTENT_LENGTH")
    min_content_length: int = Field(default=100, env="MIN_CONTENT_LENGTH")

    # Summary generation
    min_bullet_points: int = Field(default=3, env="MIN_BULLET_POINTS")
    max_bullet_points: int = Field(default=4, env="MAX_BULLET_POINTS")
    min_sentence_length: int = Field(default=30, env="MIN_SENTENCE_LENGTH")

    # Text processing limits
    title_short_length: int = Field(default=120, env="TITLE_SHORT_LENGTH")  # Section title length (doubled for Japanese)

    # Quality thresholds - lowered to increase article yield for PRD F-5 compliance
    min_quality_score: float = Field(default=0.5, env="MIN_QUALITY_SCORE")
    max_forbidden_phrases: int = Field(default=3, env="MAX_FORBIDDEN_PHRASES")

    # Clustering settings
    max_clusters: int = Field(default=8, env="MAX_CLUSTERS")
    min_cluster_size: int = Field(default=2, env="MIN_CLUSTER_SIZE")

    # Performance settings
    async_concurrency_limit: int = Field(default=5, env="ASYNC_CONCURRENCY_LIMIT")
    batch_size: int = Field(default=10, env="BATCH_SIZE")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


class MonitoringSettings(BaseSettings):
    """Monitoring and logging settings."""

    # LangSmith tracing
    langsmith_api_key: str | None = Field(default=None, env="LANGSMITH_API_KEY")
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


class AppSettings(BaseSettings):
    """Main application settings that combines all other settings."""

    # Sub-settings
    llm: LLMSettings = LLMSettings()
    database: DatabaseSettings = DatabaseSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    processing: ProcessingSettings = ProcessingSettings()
    monitoring: MonitoringSettings = MonitoringSettings()

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
