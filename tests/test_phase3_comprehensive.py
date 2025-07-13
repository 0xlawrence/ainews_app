#!/usr/bin/env python3
"""
Comprehensive Phase 3 test suite for newsletter generation system.

This test suite validates all Phase 3 features including:
- Topic clustering
- Citation generation
- Structured outputs
- Prompt management
- Content validation
- Error handling
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    from src.models.enhanced_schemas import (
        EnhancedProcessedArticle,
        NewsletterQualityReport,
        ProcessingTelemetry,
        QualityLevel,
        StructuredSummary,
        ValidationResult,
    )
    from src.models.schemas import (
        FilteredArticle,
        ProcessedArticle,
        RawArticle,
        SummarizedArticle,
        SummaryOutput,
    )
    from src.utils.citation_generator import CitationGenerator, enhance_articles_with_citations
    from src.utils.content_validator import ContentValidator, validate_article_content
    from src.utils.error_handler import GracefulDegradation, with_circuit_breaker, with_retry
    from src.utils.langsmith_tracer import LangSmithTracer, get_tracer
    from src.utils.prompt_manager import PromptManager, get_default_prompt_manager
    from src.utils.topic_clustering import (
        TopicCluster,
        TopicClusterer,
        cluster_articles_for_newsletter,
    )

    PHASE3_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Phase 3 imports not available: {e}")
    PHASE3_IMPORTS_AVAILABLE = False


class TestTopicClustering:
    """Test topic clustering functionality."""

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_topic_clusterer_initialization(self):
        """Test topic clusterer initialization."""
        clusterer = TopicClusterer()

        assert clusterer is not None
        assert hasattr(clusterer, 'embedding_manager')
        assert hasattr(clusterer, 'use_advanced_clustering')

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_simple_clustering(self):
        """Test simple clustering fallback."""
        clusterer = TopicClusterer()

        # Create mock articles
        articles = []
        for i in range(3):
            raw_article = RawArticle(
                id=f"article_{i}",
                title=f"Test Article {i}",
                url=f"https://example.com/{i}",
                published_date=datetime.now(),
                content=f"Content for article {i}",
                source_id=f"source_{i}",
                source_type="rss"
            )

            filtered_article = FilteredArticle(
                raw_article=raw_article,
                ai_relevance_score=0.8
            )

            summary = SummaryOutput(
                summary_points=[f"Point 1 for article {i}", f"Point 2 for article {i}"],
                confidence_score=0.9,
                source_reliability="high",
                model_used="test"
            )

            summarized_article = SummarizedArticle(
                filtered_article=filtered_article,
                summary=summary,
                processing_time_seconds=1.0,
                retry_count=0,
                fallback_used=False
            )

            processed_article = ProcessedArticle(
                summarized_article=summarized_article,
                duplicate_check=Mock(),
                context_analysis=None,
                final_summary="Test summary",
                citations=[],
                is_update=False
            )

            articles.append(processed_article)

        # Test simple clustering
        result = asyncio.run(clusterer._simple_clustering(articles, max_clusters=2))

        assert isinstance(result, list)
        assert len(result) <= 2
        assert all(isinstance(cluster, TopicCluster) for cluster in result)


class TestCitationGeneration:
    """Test citation generation functionality."""

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_citation_generator_initialization(self):
        """Test citation generator initialization."""
        generator = CitationGenerator()

        assert generator is not None
        assert hasattr(generator, 'llm_router')

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_format_source_name(self):
        """Test source name formatting."""
        generator = CitationGenerator()

        assert generator._format_source_name("techcrunch") == "TechCrunch"
        assert generator._format_source_name("openai_blog") == "OpenAI Blog"
        assert generator._format_source_name("unknown_source") == "Unknown Source"

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_extract_keywords(self):
        """Test keyword extraction."""
        generator = CitationGenerator()

        keywords = generator._extract_keywords("OpenAI Announces New GPT-4 Model Release")

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert any("openai" in keyword.lower() for keyword in keywords)


class TestPromptManagement:
    """Test prompt management system."""

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_prompt_manager_initialization(self):
        """Test prompt manager initialization."""
        manager = PromptManager()

        assert manager is not None
        assert hasattr(manager, 'templates')
        assert hasattr(manager, 'usage_stats')

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_add_prompt(self):
        """Test adding a new prompt."""
        manager = PromptManager()

        template = manager.add_prompt(
            name="test_prompt",
            content="This is a test prompt with {{ variable }}",
            description="Test prompt",
            variables=["variable"],
            defaults={"variable": "default_value"}
        )

        assert template.name == "test_prompt"
        assert "variable" in template.variables
        assert template.default_values["variable"] == "default_value"

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_get_prompt(self):
        """Test prompt retrieval and rendering."""
        manager = PromptManager()

        manager.add_prompt(
            name="greeting",
            content="Hello, {{ name }}!",
            variables=["name"]
        )

        rendered = manager.get_prompt("greeting", {"name": "World"})
        assert rendered == "Hello, World!"

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_default_prompt_manager(self):
        """Test default prompt manager with enhanced prompts."""
        manager = get_default_prompt_manager()

        prompts = manager.list_prompts()
        assert len(prompts) > 0

        # Check for enhanced prompts
        prompt_names = [p["name"] for p in prompts]
        assert "summary_with_validation" in prompt_names
        assert "quality_check" in prompt_names


class TestContentValidation:
    """Test content validation system."""

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_content_validator_initialization(self):
        """Test content validator initialization."""
        validator = ContentValidator()

        assert validator is not None
        assert hasattr(validator, 'rules')
        assert len(validator.rules) > 0

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_validate_good_content(self):
        """Test validation of good content."""
        validator = ContentValidator()

        good_content = [
            "OpenAI社が新しいGPT-5モデルを発表しました",
            "このモデルは従来比50%の性能向上を実現しています",
            "企業向けAPIは2025年第3四半期から提供開始です",
            "価格は月額100ドルからの予定となっています"
        ]

        result = validator.validate_content(good_content)

        assert isinstance(result, ValidationResult)
        assert result.quality_score > 0.7
        assert result.quality_level in [QualityLevel.GOOD, QualityLevel.EXCELLENT]

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_validate_bad_content(self):
        """Test validation of content with issues."""
        validator = ContentValidator()

        bad_content = [
            "この技術はすごいです",  # Demonstrative pronoun
            "短い",  # Too short
            "あの会社が発表したこの製品はその機能でどの市場でも成功するかもしれません" * 5  # Too long + multiple issues
        ]

        result = validator.validate_content(bad_content)

        assert isinstance(result, ValidationResult)
        assert len(result.violations) > 0
        assert result.quality_score < 0.8

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_validate_article_content_function(self):
        """Test article content validation function."""
        summary_points = [
            "OpenAI社がGPT-5を発表し、従来比50%の性能向上を実現しました",
            "企業向けAPIは2025年Q3から月額100ドルで提供開始です",
            "マルチモーダル機能により動画理解・生成が可能になります"
        ]

        result = validate_article_content(summary_points)

        assert isinstance(result, ValidationResult)
        assert result.is_valid  # Should be valid content


class TestErrorHandling:
    """Test error handling and recovery mechanisms."""

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_retry_decorator_success(self):
        """Test retry decorator with successful function."""
        call_count = 0

        @with_retry(max_attempts=3)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_function()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_retry_decorator_with_failure(self):
        """Test retry decorator with eventual success."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = test_function()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_graceful_degradation(self):
        """Test graceful degradation system."""
        degradation = GracefulDegradation()

        # Test initial state
        assert degradation.current_level == "full"

        # Test degradation trigger
        should_degrade = degradation.should_degrade(error_rate=0.6)
        assert should_degrade is True

        # Test degraded config
        config = degradation.get_degraded_config("medium")
        assert config["quality_threshold"] == 0.6
        assert "basic_summary" in config["features"]


class TestEnhancedSchemas:
    """Test enhanced Pydantic schemas."""

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_structured_summary_validation(self):
        """Test structured summary validation."""
        # Valid summary
        valid_summary = StructuredSummary(
            summary_points=[
                "OpenAI社がGPT-5モデルを発表し、従来比50%の性能向上を実現しました",
                "企業向けAPIは2025年第3四半期から月額100ドルで提供開始です",
                "マルチモーダル機能により動画理解・生成が可能になります"
            ],
            confidence_score=0.9,
            model_used="gemini",
            processing_time_seconds=2.5
        )

        assert valid_summary.confidence_score == 0.9
        assert len(valid_summary.summary_points) == 3

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_validation_result(self):
        """Test validation result structure."""
        result = ValidationResult(
            is_valid=True,
            quality_level=QualityLevel.GOOD,
            quality_score=0.85,
            violations=[],
            metrics={"word_count": 100}
        )

        # Test adding violation
        result.add_violation(
            rule_id="test_rule",
            severity="warning",
            message="Test violation",
            details={"test": "detail"}
        )

        assert len(result.violations) == 1
        assert result.violations[0]["rule_id"] == "test_rule"


class TestLangSmithIntegration:
    """Test LangSmith tracing integration."""

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_tracer_initialization(self):
        """Test LangSmith tracer initialization."""
        tracer = LangSmithTracer()

        assert tracer is not None
        assert hasattr(tracer, 'enabled')
        assert hasattr(tracer, 'trace_events')

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_trace_operation_context(self):
        """Test trace operation context manager."""
        tracer = LangSmithTracer()

        with tracer.trace_operation("test_operation", "test") as trace:
            assert trace.operation == "test_operation"
            assert trace.event_type == "test"
            trace.metadata["test_key"] = "test_value"

        assert len(tracer.trace_events) == 1
        assert tracer.trace_events[0].metadata["test_key"] == "test_value"

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_session_management(self):
        """Test session start/end."""
        tracer = LangSmithTracer()

        session_id = tracer.start_session("test_session")
        assert session_id is not None
        assert tracer.current_run_id == session_id

        tracer.end_session(success=True, summary={"test": "data"})
        assert tracer.current_run_id is None


class TestIntegration:
    """Integration tests for Phase 3 components."""

    @pytest.mark.skipif(not PHASE3_IMPORTS_AVAILABLE, reason="Phase 3 modules not available")
    def test_end_to_end_article_processing(self):
        """Test end-to-end article processing with Phase 3 features."""
        # Create a sample article
        raw_article = RawArticle(
            id="test_article",
            title="OpenAI Releases Advanced GPT-5 Model",
            url="https://example.com/gpt5",
            published_date=datetime.now(),
            content="OpenAI has announced the release of GPT-5, featuring significant improvements in reasoning and multimodal capabilities.",
            source_id="techcrunch",
            source_type="rss"
        )

        filtered_article = FilteredArticle(
            raw_article=raw_article,
            ai_relevance_score=0.95
        )

        summary = SummaryOutput(
            summary_points=[
                "OpenAI社が最新のGPT-5モデルを正式発表し、推論能力が大幅に向上しました",
                "マルチモーダル機能により動画理解・生成が可能となり、創作分野での活用が期待されます",
                "企業向けAPIは2025年第3四半期から段階的に提供開始される予定です"
            ],
            confidence_score=0.92,
            source_reliability="high",
            model_used="gemini"
        )

        summarized_article = SummarizedArticle(
            filtered_article=filtered_article,
            summary=summary,
            processing_time_seconds=3.2,
            retry_count=0,
            fallback_used=False
        )

        processed_article = ProcessedArticle(
            summarized_article=summarized_article,
            duplicate_check=Mock(),
            context_analysis=None,
            final_summary="",
            citations=[],
            is_update=False
        )

        # Test content validation
        result = validate_article_content(summary.summary_points)
        assert result.is_valid
        assert result.quality_level in [QualityLevel.GOOD, QualityLevel.EXCELLENT]

        # Test citation generation
        citation_generator = CitationGenerator()
        citations = asyncio.run(citation_generator.generate_citations(processed_article))
        assert len(citations) > 0
        assert "TechCrunch" in citations[0]

        print("✅ End-to-end article processing test passed")


def run_tests():
    """Run all Phase 3 tests."""
    if not PHASE3_IMPORTS_AVAILABLE:
        print("❌ Phase 3 modules not available - skipping comprehensive tests")
        return False

    print("🧪 Running Phase 3 Comprehensive Tests\n")

    # Test categories
    test_classes = [
        TestTopicClustering,
        TestCitationGeneration,
        TestPromptManagement,
        TestContentValidation,
        TestErrorHandling,
        TestEnhancedSchemas,
        TestLangSmithIntegration,
        TestIntegration
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n--- Testing {test_class.__name__} ---")

        # Get test methods
        test_methods = [
            method for method in dir(test_class)
            if method.startswith('test_')
        ]

        test_instance = test_class()

        for test_method_name in test_methods:
            total_tests += 1
            test_method = getattr(test_instance, test_method_name)

            try:
                test_method()
                print(f"✅ {test_method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"❌ {test_method_name}: {e}")

    print(f"\n📊 Test Results: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 All Phase 3 tests passed!")
        return True
    else:
        print("⚠️  Some Phase 3 tests failed.")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
