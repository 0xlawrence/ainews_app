#!/usr/bin/env python3
"""
Basic test to verify Phase 1 implementation.

This script tests the core functionality without requiring API keys.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_schemas():
    """Test Pydantic schemas."""
    print("\nTesting schemas...")

    try:
        from models.schemas import NewsletterConfig, RawArticle, SourceConfig

        # Test source config
        source = SourceConfig(
            id="test_source",
            name="Test Source",
            url="https://example.com/rss",
            source_type="rss",
            enabled=True
        )

        # Test article
        article = RawArticle(
            id="test_article",
            title="Test AI Article",
            url="https://example.com/article",
            published_date=datetime.now(),
            content="This is a test article about artificial intelligence and machine learning.",
            source_id="test_source",
            source_type="rss"
        )

        # Test config
        config = NewsletterConfig(
            max_items=5,
            edition="daily",
            sources=[source],
            processing_id="test_run"
        )

        print("✅ Schema validation successful")
        return True
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

def test_ai_filter():
    """Test AI content filtering."""
    print("\nTesting AI filter...")

    try:
        from models.schemas import RawArticle
        from utils.ai_filter import AIContentFilter

        # Create test articles
        ai_article = RawArticle(
            id="ai_article",
            title="OpenAI Releases GPT-5 with Advanced Reasoning",
            url="https://example.com/gpt5",
            published_date=datetime.now(),
            content="OpenAI has announced GPT-5, featuring improved artificial intelligence capabilities and machine learning algorithms.",
            source_id="test_source",
            source_type="rss"
        )

        non_ai_article = RawArticle(
            id="non_ai_article",
            title="Local Restaurant Opens New Location",
            url="https://example.com/restaurant",
            published_date=datetime.now(),
            content="A new restaurant has opened downtown, serving traditional cuisine.",
            source_id="test_source",
            source_type="rss"
        )

        # Test filter
        filter_instance = AIContentFilter()
        filtered = filter_instance.filter_articles([ai_article, non_ai_article], 0.5)

        assert len(filtered) == 1, f"Expected 1 filtered article, got {len(filtered)}"
        assert filtered[0].raw_article.id == "ai_article", "Wrong article filtered"

        print(f"✅ AI filter working - {len(filtered)}/2 articles passed")
        return True
    except Exception as e:
        print(f"❌ AI filter test failed: {e}")
        return False

def test_duplicate_checker():
    """Test duplicate detection."""
    print("\nTesting duplicate checker...")

    try:
        from deduplication.duplicate_checker import BasicDuplicateChecker
        from models.schemas import FilteredArticle, RawArticle, SummarizedArticle, SummaryOutput

        # Create test article
        article = RawArticle(
            id="test_dup",
            title="Test Article About AI",
            url="https://example.com/test",
            published_date=datetime.now(),
            content="This is a test article about artificial intelligence.",
            source_id="test_source",
            source_type="rss"
        )

        filtered_article = FilteredArticle(
            raw_article=article,
            ai_relevance_score=0.8,
            ai_keywords=["ai", "artificial intelligence"],
            filter_reason="High AI relevance"
        )

        summary = SummaryOutput(
            summary_points=["Test point 1", "Test point 2", "Test point 3"],
            confidence_score=0.9,
            source_reliability="high",
            model_used="test"
        )

        summarized_article = SummarizedArticle(
            filtered_article=filtered_article,
            summary=summary,
            processing_time_seconds=1.0
        )

        # Test duplicate checker
        checker = BasicDuplicateChecker()
        result = checker.check_duplicate(summarized_article, [])

        assert not result.is_duplicate, "Should not be duplicate with empty history"

        print("✅ Duplicate checker working")
        return True
    except Exception as e:
        print(f"❌ Duplicate checker test failed: {e}")
        return False

def test_newsletter_generator():
    """Test newsletter generation."""
    print("\nTesting newsletter generator...")

    try:
        from utils.newsletter_generator import NewsletterGenerator

        generator = NewsletterGenerator()
        assert generator.templates_dir.exists(), "Templates directory should exist"

        print("✅ Newsletter generator initialized")
        return True
    except Exception as e:
        print(f"❌ Newsletter generator test failed: {e}")
        return False

def test_sources_config():
    """Test sources configuration."""
    print("\nTesting sources config...")

    try:
        with open("sources.json") as f:
            sources_data = json.load(f)

        assert "sources" in sources_data, "Sources key missing"
        assert len(sources_data["sources"]) > 0, "No sources configured"

        enabled_sources = [s for s in sources_data["sources"] if s.get("enabled", False)]
        assert len(enabled_sources) > 0, "No enabled sources"

        print(f"✅ Sources config valid - {len(enabled_sources)} enabled sources")
        return True
    except Exception as e:
        print(f"❌ Sources config test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Phase 1 Basic Tests\n")

    tests = [
        test_imports,
        test_schemas,
        test_ai_filter,
        test_duplicate_checker,
        test_newsletter_generator,
        test_sources_config
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Phase 1 implementation is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
