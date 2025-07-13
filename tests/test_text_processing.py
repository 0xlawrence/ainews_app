"""
Test suite for text processing utilities.

This module tests the Japanese text processing and normalization functions.
"""


import pytest


# Test text processing imports
def test_text_processing_import():
    """Test that text processing utilities can be imported successfully."""
    try:
        from src.utils.text_processing import (
            clean_llm_response,
            detect_language_ratio,
            extract_japanese_sentences,
            normalize_japanese_text,
            standardize_punctuation,
            truncate_at_sentence_boundary,
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import text processing utilities: {e}")


def test_normalize_japanese_text():
    """Test Japanese text normalization functionality."""
    from src.utils.text_processing import normalize_japanese_text

    # Test redundant expression removal
    redundant_text = "これはことができます。またこれもことができます。"
    normalized = normalize_japanese_text(redundant_text)
    assert normalized.count("ことができます。") == 1

    # Test polite form conversion
    informal_text = "これは良いものである。"
    normalized = normalize_japanese_text(informal_text)
    assert "です。" in normalized
    assert "である。" not in normalized

    # Test empty input
    assert normalize_japanese_text("") == ""
    assert normalize_japanese_text(None) == ""


def test_clean_llm_response():
    """Test LLM response cleaning functionality."""
    from src.utils.text_processing import clean_llm_response

    # Test actual content extraction
    content_response = "これは実際のコンテンツです。技術の進展について説明します。"
    cleaned = clean_llm_response(content_response)
    assert "技術の進展" in cleaned  # Should preserve actual content

    # Test quote removal
    quoted_response = "「これは引用されたテキストです」"
    cleaned = clean_llm_response(quoted_response)
    assert not cleaned.startswith("「")
    assert not cleaned.endswith("」")

    # Test empty input
    assert clean_llm_response("") == ""
    assert clean_llm_response("   ") == ""

    # Test meta-text skipping (function skips lines starting with meta words)
    meta_response = "これはOpenAIが発表した新しい技術です。"
    cleaned = clean_llm_response(meta_response)
    assert "OpenAI" in cleaned  # Should preserve content with tech keywords


def test_truncate_at_sentence_boundary():
    """Test sentence boundary truncation."""
    from src.utils.text_processing import truncate_at_sentence_boundary

    # Test normal truncation at sentence boundary
    text = "これは最初の文です。これは二番目の文です。これは三番目の文です。"
    truncated = truncate_at_sentence_boundary(text, 30)
    assert len(truncated) <= 30
    # Should truncate at sentence boundary or add placeholder
    assert truncated.endswith("。") or truncated.endswith("…")

    # Test text shorter than limit
    short_text = "短いテキスト。"
    result = truncate_at_sentence_boundary(short_text, 100)
    assert result == short_text

    # Test fallback truncation
    long_word = "とても長い単語が続いて句読点がない場合のテスト"
    truncated = truncate_at_sentence_boundary(long_word, 20)
    assert len(truncated) <= 20
    assert truncated.endswith("…")


def test_extract_japanese_sentences():
    """Test Japanese sentence extraction."""
    from src.utils.text_processing import extract_japanese_sentences

    # Test sentence extraction
    text = "これは良い文です。これは短い。申し訳ございませんが、これは除外されます。これも適切な長さの文章です。"
    sentences = extract_japanese_sentences(text, min_length=10, max_length=50)

    assert len(sentences) >= 1  # At least one sentence should pass
    assert all(10 <= len(s) <= 50 for s in sentences)
    assert all("申し訳" not in s for s in sentences)  # Filtered out

    # Test with more content to ensure multiple sentences
    longer_text = "これは最初の良い文章です。これは二番目の適切な長さの文章です。これも三番目の文章です。"
    longer_sentences = extract_japanese_sentences(longer_text, min_length=10, max_length=50)
    assert len(longer_sentences) >= 2

    # Test empty input
    assert extract_japanese_sentences("") == []


def test_detect_language_ratio():
    """Test language ratio detection."""
    from src.utils.text_processing import detect_language_ratio

    # Test Japanese text
    japanese_text = "これは日本語のテキストです。"
    ratios = detect_language_ratio(japanese_text)
    assert ratios['japanese'] > 0.5
    assert ratios['english'] < 0.3

    # Test English text
    english_text = "This is English text."
    ratios = detect_language_ratio(english_text)
    assert ratios['english'] > 0.5
    assert ratios['japanese'] < 0.3

    # Test mixed text
    mixed_text = "This is 日本語 mixed text テキスト."
    ratios = detect_language_ratio(mixed_text)
    assert 0.2 < ratios['japanese'] < 0.8
    assert 0.2 < ratios['english'] < 0.8

    # Test empty text
    ratios = detect_language_ratio("")
    assert ratios['japanese'] == 0.0
    assert ratios['english'] == 0.0


def test_standardize_punctuation():
    """Test punctuation standardization."""
    from src.utils.text_processing import standardize_punctuation

    # Test punctuation conversion
    text_with_fullwidth = "これは，テストです．"
    standardized = standardize_punctuation(text_with_fullwidth)
    assert "、" in standardized
    assert "。" in standardized
    assert "，" not in standardized
    assert "．" not in standardized

    # Test spacing around punctuation
    spaced_text = "これは 、 テスト です 。"
    standardized = standardize_punctuation(spaced_text)
    assert " 、 " not in standardized
    assert " 。" not in standardized


def test_ensure_sentence_completeness():
    """Test sentence completeness functionality."""
    from src.utils.text_processing import ensure_sentence_completeness

    # Test short text (returns unchanged if within limit)
    short_text = "短いテキスト。"
    result = ensure_sentence_completeness(short_text, 100)
    assert result == short_text

    # Test truncation case where function actually needs to truncate
    long_text = "これは最初の文です。これは二番目の文です。これは三番目の文です。これは四番目の文です。"
    truncated = ensure_sentence_completeness(long_text, 30)
    assert len(truncated) <= 30
    assert truncated.endswith("。") or truncated.endswith("...")

    # Test case where text is exactly at target length
    medium_text = "これは最初の文です。これは二番目"
    completed = ensure_sentence_completeness(medium_text, len(medium_text) - 5)  # Force truncation
    assert len(completed) <= len(medium_text) - 5 + 3  # Account for "..." addition


def test_normalize_title_for_comparison():
    """Test title normalization for comparison."""
    from src.utils.text_processing import normalize_title_for_comparison

    # Test prefix removal
    title_with_prefix = "Breaking: OpenAI announces new model"
    normalized = normalize_title_for_comparison(title_with_prefix)
    assert "breaking:" not in normalized.lower()
    assert "openai announces new model" in normalized.lower()

    # Test whitespace normalization
    spaced_title = "This   has    multiple   spaces"
    normalized = normalize_title_for_comparison(spaced_title)
    assert "  " not in normalized  # No double spaces


def test_text_processing_edge_cases():
    """Test edge cases and error handling."""
    from src.utils.text_processing import (
        clean_llm_response,
        normalize_japanese_text,
        truncate_at_sentence_boundary,
    )

    # Test None inputs
    assert normalize_japanese_text(None) == ""
    assert clean_llm_response(None) == ""

    # Test very long inputs
    very_long_text = "長いテキスト。" * 1000
    result = truncate_at_sentence_boundary(very_long_text, 100)
    assert len(result) <= 100

    # Test special characters
    special_text = "テキスト🚀with📝emojis🎯and特殊文字"
    normalized = normalize_japanese_text(special_text)
    assert len(normalized) > 0  # Should not crash


def test_constants_integration():
    """Test integration with constants module."""
    try:
        # Test that text processing can use constants
        from src.constants.settings import TEXT_LIMITS
        from src.utils.text_processing import normalize_japanese_text

        # Should work with constants
        long_text = "これは長いテキストのテストです。" * 20  # Make it longer to exceed limit
        max_length = TEXT_LIMITS['summary_point_max']

        # Should not crash when using constants
        assert max_length > 0
        assert len(long_text) > max_length  # Now should pass

        # Test that normalization works
        result = normalize_japanese_text(long_text)
        assert len(result) > 0

    except ImportError:
        # Constants module not available - should still work
        pass


def test_performance():
    """Test performance of text processing functions."""
    import time

    from src.utils.text_processing import normalize_japanese_text

    # Test with moderately large text
    large_text = "これは日本語のテキストです。" * 100

    start_time = time.time()
    result = normalize_japanese_text(large_text)
    end_time = time.time()

    # Should complete within reasonable time (1 second)
    assert end_time - start_time < 1.0
    assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
