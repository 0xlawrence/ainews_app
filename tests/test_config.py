"""Tests for configuration settings."""

import os
from unittest.mock import patch

from src.config.settings import (
    AppSettings,
    DatabaseSettings,
    EmbeddingSettings,
    LLMSettings,
    ProcessingSettings,
    get_settings,
    reload_settings,
)


class TestLLMSettings:
    """Test LLM configuration settings."""

    def test_default_values(self):
        """Test default LLM configuration values."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-openai",
            "GEMINI_API_KEY": "test-gemini",
            "CLAUDE_API_KEY": "test-claude"
        }, clear=True):
            settings = LLMSettings()
            assert settings.primary_model == "gemini-2.5-flash"
            assert settings.fallback_model == "claude-3-5-sonnet-20241022"
            assert settings.final_fallback_model == "gpt-4o-mini"
            assert settings.max_retries == 3
            assert settings.retry_delay == 1.0
            assert settings.timeout == 30

    def test_anthropic_api_key_fallback(self):
        """Test that ANTHROPIC_API_KEY is used as fallback for CLAUDE_API_KEY."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-openai",
            "GEMINI_API_KEY": "test-gemini",
            "ANTHROPIC_API_KEY": "test-anthropic"
        }, clear=True):
            settings = LLMSettings()
            assert settings.claude_api_key == "test-anthropic"


class TestEmbeddingSettings:
    """Test embedding configuration settings."""

    def test_similarity_thresholds(self):
        """Test similarity threshold default values."""
        settings = EmbeddingSettings()
        assert settings.duplicate_similarity_threshold == 0.85
        assert settings.consolidation_threshold_adjustment == 0.25
        assert settings.minimum_consolidation_threshold == 0.55
        assert settings.context_similarity_threshold == 0.75
        assert settings.sequel_detection_threshold == 0.8

    def test_embedding_model_settings(self):
        """Test embedding model configuration."""
        settings = EmbeddingSettings()
        assert settings.embedding_model == "text-embedding-3-small"
        assert settings.embedding_dimensions == 1536
        assert settings.max_search_results == 50
        assert settings.search_days_back == 7


class TestProcessingSettings:
    """Test processing configuration settings."""

    def test_article_limits(self):
        """Test article processing limits."""
        settings = ProcessingSettings()
        assert settings.max_articles_per_run == 30
        assert settings.max_content_length == 10000
        assert settings.min_content_length == 100
        assert settings.min_bullet_points == 3
        assert settings.max_bullet_points == 4

    def test_quality_settings(self):
        """Test quality control settings."""
        settings = ProcessingSettings()
        assert settings.min_quality_score == 0.7
        assert settings.max_forbidden_phrases == 2
        assert settings.max_clusters == 8
        assert settings.min_cluster_size == 2


class TestDatabaseSettings:
    """Test database configuration settings."""

    def test_supabase_key_fallback(self):
        """Test that SUPABASE_KEY is used as fallback for SUPABASE_SERVICE_KEY."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "test-key"
        }, clear=True):
            settings = DatabaseSettings()
            assert settings.supabase_key == "test-key"

    def test_connection_settings(self):
        """Test database connection settings."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-service-key"
        }, clear=True):
            settings = DatabaseSettings()
            assert settings.max_connections == 10
            assert settings.connection_timeout == 30


class TestAppSettings:
    """Test main application settings."""

    def test_app_info(self):
        """Test application information settings."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-openai",
            "GEMINI_API_KEY": "test-gemini",
            "CLAUDE_API_KEY": "test-claude",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-key"
        }, clear=True):
            settings = AppSettings()
            assert settings.app_name == "AI News App"
            assert settings.app_version == "0.1.0"
            assert settings.environment == "development"
            assert settings.debug is False

    def test_file_paths(self):
        """Test default file path settings."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-openai",
            "GEMINI_API_KEY": "test-gemini",
            "CLAUDE_API_KEY": "test-claude",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-key"
        }, clear=True):
            settings = AppSettings()
            assert settings.sources_file == "sources.json"
            assert settings.output_dir == "drafts"
            assert settings.logs_dir == "logs"
            assert settings.data_dir == "data"


class TestSettingsFunctions:
    """Test settings utility functions."""

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-openai",
        "GEMINI_API_KEY": "test-gemini",
        "CLAUDE_API_KEY": "test-claude",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key"
    }, clear=True)
    def test_get_settings(self):
        """Test get_settings function."""
        settings = get_settings()
        assert isinstance(settings, AppSettings)
        assert settings.llm.primary_model == "gemini-2.5-flash"
        assert settings.embedding.duplicate_similarity_threshold == 0.85

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-openai-new",
        "GEMINI_API_KEY": "test-gemini-new",
        "CLAUDE_API_KEY": "test-claude-new",
        "SUPABASE_URL": "https://test-new.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key-new",
        "PRIMARY_LLM_MODEL": "gemini-3.0-flash"
    }, clear=True)
    def test_reload_settings(self):
        """Test reload_settings function."""
        settings = reload_settings()
        assert isinstance(settings, AppSettings)
        assert settings.llm.primary_model == "gemini-3.0-flash"
        assert settings.llm.openai_api_key == "test-openai-new"


class TestEnvironmentVariableOverrides:
    """Test environment variable overrides."""

    def test_llm_model_override(self):
        """Test LLM model can be overridden via environment."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-openai",
            "GEMINI_API_KEY": "test-gemini",
            "CLAUDE_API_KEY": "test-claude",
            "PRIMARY_LLM_MODEL": "custom-model",
            "FALLBACK_LLM_MODEL": "custom-fallback"
        }, clear=True):
            settings = LLMSettings()
            assert settings.primary_model == "custom-model"
            assert settings.fallback_model == "custom-fallback"

    def test_threshold_override(self):
        """Test similarity thresholds can be overridden."""
        with patch.dict(os.environ, {
            "DUPLICATE_SIMILARITY_THRESHOLD": "0.9",
            "MIN_CONSOLIDATION_THRESHOLD": "0.6"
        }, clear=True):
            settings = EmbeddingSettings()
            assert settings.duplicate_similarity_threshold == 0.9
            assert settings.minimum_consolidation_threshold == 0.6

    def test_processing_limits_override(self):
        """Test processing limits can be overridden."""
        with patch.dict(os.environ, {
            "MAX_ARTICLES_PER_RUN": "50",
            "MIN_BULLET_POINTS": "2",
            "MAX_BULLET_POINTS": "5"
        }, clear=True):
            settings = ProcessingSettings()
            assert settings.max_articles_per_run == 50
            assert settings.min_bullet_points == 2
            assert settings.max_bullet_points == 5
