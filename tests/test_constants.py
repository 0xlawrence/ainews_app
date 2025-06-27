"""
Test suite for constants modules.

This module tests the centralized constants management system including
mappings, settings, and messages.
"""

import pytest
import re
from typing import Dict, List

# Test constants imports
def test_constants_import():
    """Test that all constants modules can be imported successfully."""
    try:
        from src.constants.mappings import (
            COMPANY_MAPPINGS, PRODUCT_MAPPINGS, SOURCE_MAPPINGS,
            OFFICIAL_DOMAINS, REPUTABLE_DOMAINS, COMPANY_PATTERNS
        )
        from src.constants.settings import (
            TEXT_LIMITS, PERFORMANCE, SIMILARITY_THRESHOLDS,
            LLM_SETTINGS, NEWSLETTER
        )
        from src.constants.messages import (
            ERROR_MESSAGES, DEFAULT_CONTENT, STATUS_MESSAGES,
            VALIDATION_MESSAGES, CLEANING_PATTERNS
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import constants: {e}")


def test_company_mappings():
    """Test company name mappings functionality."""
    from src.constants.mappings import COMPANY_MAPPINGS, format_company_name
    
    # Test known mappings
    assert COMPANY_MAPPINGS["openai"] == "OpenAI"
    assert COMPANY_MAPPINGS["google"] == "Google"
    assert COMPANY_MAPPINGS["anthropic"] == "Anthropic"
    
    # Test format function
    assert format_company_name("openai") == "OpenAI"
    assert format_company_name("google") == "Google"
    assert format_company_name("unknown") == "Unknown"  # Title case fallback


def test_product_mappings():
    """Test product name mappings functionality."""
    from src.constants.mappings import PRODUCT_MAPPINGS, format_product_name
    
    # Test known mappings
    assert PRODUCT_MAPPINGS["gpt"] == "GPT"
    assert PRODUCT_MAPPINGS["claude"] == "Claude"
    assert PRODUCT_MAPPINGS["dall-e"] == "DALL-E"
    
    # Test format function
    assert format_product_name("gpt") == "GPT"
    assert format_product_name("claude") == "Claude"
    assert format_product_name("unknown") == "unknown"  # Unchanged for unknown


def test_domain_classifications():
    """Test domain classification functionality."""
    from src.constants.mappings import (
        OFFICIAL_DOMAINS, REPUTABLE_DOMAINS,
        is_official_domain, is_reputable_domain
    )
    
    # Test official domains
    assert "openai.com" in OFFICIAL_DOMAINS
    assert "google.com" in OFFICIAL_DOMAINS
    assert "anthropic.com" in OFFICIAL_DOMAINS
    
    # Test reputable domains
    assert "techcrunch.com" in REPUTABLE_DOMAINS
    assert "theverge.com" in REPUTABLE_DOMAINS
    assert "wired.com" in REPUTABLE_DOMAINS
    
    # Test classification functions
    assert is_official_domain("openai.com") == True
    assert is_official_domain("example.com") == False
    assert is_reputable_domain("techcrunch.com") == True
    assert is_reputable_domain("example.com") == False


def test_company_patterns():
    """Test regex patterns for company detection."""
    from src.constants.mappings import COMPANY_PATTERNS
    
    # Should be list of regex patterns
    assert isinstance(COMPANY_PATTERNS, list)
    assert len(COMPANY_PATTERNS) > 0
    
    # Test pattern compilation
    for pattern in COMPANY_PATTERNS:
        try:
            compiled = re.compile(pattern)
            assert compiled is not None
        except re.error:
            pytest.fail(f"Invalid regex pattern: {pattern}")


def test_text_limits():
    """Test text processing limits configuration."""
    from src.constants.settings import TEXT_LIMITS
    
    # Required limit keys
    required_limits = [
        'toc_short', 'title_short', 'citation_max',
        'summary_point_max', 'summary_point_min'
    ]
    
    for limit_key in required_limits:
        assert limit_key in TEXT_LIMITS
        assert isinstance(TEXT_LIMITS[limit_key], int)
        assert TEXT_LIMITS[limit_key] > 0


def test_similarity_thresholds():
    """Test similarity thresholds configuration."""
    from src.constants.settings import SIMILARITY_THRESHOLDS
    
    # Required threshold keys
    required_thresholds = [
        'duplicate_jaccard', 'duplicate_sequence', 'duplicate_main',
        'context_similarity', 'ai_relevance_high'
    ]
    
    for threshold_key in required_thresholds:
        assert threshold_key in SIMILARITY_THRESHOLDS
        assert isinstance(SIMILARITY_THRESHOLDS[threshold_key], (int, float))
        assert 0.0 <= SIMILARITY_THRESHOLDS[threshold_key] <= 1.0


def test_performance_settings():
    """Test performance configuration settings."""
    from src.constants.settings import PERFORMANCE
    
    # Required performance keys
    required_keys = [
        'max_concurrent_llm', 'max_concurrent_citations',
        'semaphore_limit', 'cache_max_size'
    ]
    
    for key in required_keys:
        assert key in PERFORMANCE
        assert isinstance(PERFORMANCE[key], int)
        assert PERFORMANCE[key] > 0


def test_error_messages():
    """Test error message templates."""
    from src.constants.messages import ERROR_MESSAGES
    
    # Should have common error types
    required_errors = [
        'llm_generation_failed', 'translation_failed',
        'citation_generation_failed', 'context_analysis_failed'
    ]
    
    for error_key in required_errors:
        assert error_key in ERROR_MESSAGES
        assert isinstance(ERROR_MESSAGES[error_key], str)
        assert len(ERROR_MESSAGES[error_key]) > 0


def test_default_content():
    """Test default content fallbacks."""
    from src.constants.messages import DEFAULT_CONTENT
    
    # Should have fallback content
    required_defaults = [
        'summary_point_fallback', 'title_fallback',
        'translation_fallback', 'citation_fallback'
    ]
    
    for default_key in required_defaults:
        assert default_key in DEFAULT_CONTENT
        assert isinstance(DEFAULT_CONTENT[default_key], str)
        assert len(DEFAULT_CONTENT[default_key]) > 0


def test_cleaning_patterns():
    """Test regex cleaning patterns."""
    from src.constants.messages import CLEANING_PATTERNS
    
    # Should have cleaning pattern categories
    required_categories = ['meta_removal', 'title_prefixes', 'title_suffixes']
    
    for category in required_categories:
        assert category in CLEANING_PATTERNS
        assert isinstance(CLEANING_PATTERNS[category], list)
        
        # Test pattern compilation
        for pattern in CLEANING_PATTERNS[category]:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                assert compiled is not None
            except re.error:
                pytest.fail(f"Invalid cleaning pattern: {pattern}")


def test_newsletter_settings():
    """Test newsletter generation settings."""
    from src.constants.settings import NEWSLETTER
    
    # Required newsletter settings
    required_settings = [
        'max_citations_per_article', 'target_article_count',
        'max_articles_processing', 'lead_text_sentences'
    ]
    
    for setting_key in required_settings:
        assert setting_key in NEWSLETTER
        assert isinstance(NEWSLETTER[setting_key], int)
        assert NEWSLETTER[setting_key] > 0


def test_llm_settings():
    """Test LLM operation settings."""
    from src.constants.settings import LLM_SETTINGS
    
    # Required LLM settings
    required_settings = [
        'retry_delay', 'max_retries', 'timeout_seconds',
        'summary_max_tokens', 'temperature_conservative'
    ]
    
    for setting_key in required_settings:
        assert setting_key in LLM_SETTINGS
        assert isinstance(LLM_SETTINGS[setting_key], (int, float))
        assert LLM_SETTINGS[setting_key] > 0


def test_constants_consistency():
    """Test consistency between related constants."""
    from src.constants.settings import TEXT_LIMITS, NEWSLETTER
    
    # TOC length should be shorter than title length
    assert TEXT_LIMITS['toc_short'] <= TEXT_LIMITS['title_short']
    
    # Summary point limits should be reasonable
    assert TEXT_LIMITS['summary_point_min'] < TEXT_LIMITS['summary_point_max']
    
    # Newsletter settings should be consistent
    assert NEWSLETTER['target_article_count'] <= NEWSLETTER['max_articles_processing']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])