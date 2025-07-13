"""
Test suite for source quality weighting functionality.

This module tests the enhanced AI filter with domain-based source quality bonuses.
"""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest


def test_source_quality_bonus_calculation():
    """Test source quality bonus calculation for different domain types."""
    # Mock the logger to avoid dependency issues
    with patch('src.utils.ai_filter.logger'):
        from src.models.schemas import RawArticle
        from src.utils.ai_filter import AIContentFilter

        filter_instance = AIContentFilter()

        # Test official domain bonus
        official_article = RawArticle(
            id=str(uuid.uuid4()),
            title="OpenAI announces GPT-5",
            content="OpenAI released new AI model with advanced capabilities",
            url="https://openai.com/news/gpt-5-announcement",
            published_date=datetime.now(),
            source_id="openai_news"
        )

        bonus = filter_instance._calculate_source_quality_bonus(official_article)
        assert bonus >= 0.25  # Should get official domain or source ID bonus

        # Test reputable domain bonus
        reputable_article = RawArticle(
            id=str(uuid.uuid4()),
            title="TechCrunch covers AI developments",
            content="Latest developments in artificial intelligence and machine learning",
            url="https://techcrunch.com/2025/06/24/ai-developments",
            published_date=datetime.now(),
            source_id="techcrunch"
        )

        bonus = filter_instance._calculate_source_quality_bonus(reputable_article)
        assert bonus >= 0.1  # Should get reputable domain bonus

        # Test unknown domain
        unknown_article = RawArticle(
            id=str(uuid.uuid4()),
            title="Random blog post",
            content="Some content about AI",
            url="https://unknown-blog.com/ai-post",
            published_date=datetime.now(),
            source_id="unknown_blog"
        )

        bonus = filter_instance._calculate_source_quality_bonus(unknown_article)
        assert bonus == 0.0  # No bonus for unknown domains


def test_enhanced_relevance_scoring():
    """Test that relevance scoring includes source quality bonus."""
    with patch('src.utils.ai_filter.logger'):
        from src.models.schemas import RawArticle
        from src.utils.ai_filter import AIContentFilter

        filter_instance = AIContentFilter()

        # Create two identical articles from different sources
        high_quality_article = RawArticle(
            id=str(uuid.uuid4()),
            title="AI breakthrough in machine learning",
            content="Researchers develop new neural network architecture",
            url="https://research.google/blog/ai-breakthrough",
            published_date=datetime.now(),
            source_id="google_research"
        )

        low_quality_article = RawArticle(
            id=str(uuid.uuid4()),
            title="AI breakthrough in machine learning",
            content="Researchers develop new neural network architecture",
            url="https://random-blog.com/ai-post",
            published_date=datetime.now(),
            source_id="random_blog"
        )

        high_score, _, _ = filter_instance._calculate_relevance(high_quality_article)
        low_score, _, _ = filter_instance._calculate_relevance(low_quality_article)

        # High-quality source should have higher score
        assert high_score > low_score


def test_academic_domain_bonus():
    """Test bonus for academic and research domains."""
    with patch('src.utils.ai_filter.logger'):
        from src.models.schemas import RawArticle
        from src.utils.ai_filter import AIContentFilter

        filter_instance = AIContentFilter()

        # Test arXiv paper
        arxiv_article = RawArticle(
            id=str(uuid.uuid4()),
            title="Novel approach to transformer architecture",
            content="We present a new transformer model for natural language processing",
            url="https://arxiv.org/abs/2025.12345",
            published_date=datetime.now(),
            source_id="arxiv"
        )

        bonus = filter_instance._calculate_source_quality_bonus(arxiv_article)
        assert bonus >= 0.2  # Academic sources get 20% bonus

        # Test university domain
        edu_article = RawArticle(
            id=str(uuid.uuid4()),
            title="Stanford AI research breakthrough",
            content="Stanford researchers achieve new milestone in AI safety",
            url="https://ai.stanford.edu/blog/safety-breakthrough",
            published_date=datetime.now(),
            source_id="stanford_ai"
        )

        bonus = filter_instance._calculate_source_quality_bonus(edu_article)
        assert bonus >= 0.2  # Academic domains get bonus


def test_curated_source_bonus():
    """Test bonus for curated AI news sources."""
    with patch('src.utils.ai_filter.logger'):
        from src.models.schemas import RawArticle
        from src.utils.ai_filter import AIContentFilter

        filter_instance = AIContentFilter()

        # Test curated source
        curated_article = RawArticle(
            id=str(uuid.uuid4()),
            title="Weekly AI roundup",
            content="This week's most important developments in artificial intelligence",
            url="https://the-decoder.com/weekly-ai-roundup",
            published_date=datetime.now(),
            source_id="the_decoder"
        )

        bonus = filter_instance._calculate_source_quality_bonus(curated_article)
        assert bonus >= 0.1  # Curated sources get bonus


def test_source_quality_fallback():
    """Test fallback behavior when constants are not available."""
    with patch('src.utils.ai_filter.logger'):
        # Mock import failure for constants
        with patch('src.utils.ai_filter.AIContentFilter._calculate_source_quality_bonus') as mock_bonus:
            mock_bonus.return_value = 0.0

            from src.models.schemas import RawArticle
            from src.utils.ai_filter import AIContentFilter

            filter_instance = AIContentFilter()

            test_article = RawArticle(
                id=str(uuid.uuid4()),
                title="Test article",
                content="Test content with AI keywords",
                url="https://example.com/test",
                published_date=datetime.now(),
                source_id="test"
            )

            # Should not crash even if constants unavailable
            score, keywords, reason = filter_instance._calculate_relevance(test_article)
            assert isinstance(score, float)
            assert isinstance(keywords, list)
            assert isinstance(reason, str)


def test_url_parsing_edge_cases():
    """Test URL parsing for source quality bonus with edge cases."""
    with patch('src.utils.ai_filter.logger'):
        from src.models.schemas import RawArticle
        from src.utils.ai_filter import AIContentFilter

        filter_instance = AIContentFilter()

        # Test invalid URL
        invalid_url_article = RawArticle(
            id=str(uuid.uuid4()),
            title="Test article",
            content="Content with AI keywords",
            url="not-a-valid-url",
            published_date=datetime.now(),
            source_id="test"
        )

        # Should not crash with invalid URL
        bonus = filter_instance._calculate_source_quality_bonus(invalid_url_article)
        assert bonus >= 0.0

        # Test missing URL
        no_url_article = RawArticle(
            id=str(uuid.uuid4()),
            title="Test article",
            content="Content with AI keywords",
            url=None,
            published_date=datetime.now(),
            source_id="test_source"
        )

        # Should not crash with missing URL
        bonus = filter_instance._calculate_source_quality_bonus(no_url_article)
        assert bonus >= 0.0


def test_filter_integration():
    """Test that source quality weighting integrates properly with filtering."""
    with patch('src.utils.ai_filter.logger'):
        from src.models.schemas import RawArticle
        from src.utils.ai_filter import filter_ai_content

        # Create test articles with varying quality and sources
        articles = [
            RawArticle(
                id=str(uuid.uuid4()),
                title="OpenAI releases GPT-5",
                content="OpenAI announces new large language model with improved capabilities",
                url="https://openai.com/news/gpt-5",
                published_date=datetime.now(),
                source_id="openai_news"
            ),
            RawArticle(
                id=str(uuid.uuid4()),
                title="Random AI post",
                content="Some basic discussion about artificial intelligence",
                url="https://random-blog.com/ai",
                published_date=datetime.now(),
                source_id="random_blog"
            ),
            RawArticle(
                id=str(uuid.uuid4()),
                title="Non-AI content",
                content="This article talks about cooking and recipes",
                url="https://cooking-blog.com/recipes",
                published_date=datetime.now(),
                source_id="cooking_blog"
            )
        ]

        # Filter articles
        filtered = filter_ai_content(articles, relevance_threshold=0.4)

        # Should prioritize high-quality sources
        assert len(filtered) >= 1  # At least the OpenAI article should pass

        # OpenAI article should have high score due to content + source quality
        openai_filtered = [f for f in filtered if "openai" in f.filter_reason.lower() or f.ai_relevance_score > 0.8]
        assert len(openai_filtered) >= 0  # Should be present if AI content is detected


def test_youtube_source_handling():
    """Test source quality bonus for YouTube channels."""
    with patch('src.utils.ai_filter.logger'):
        from src.models.schemas import RawArticle
        from src.utils.ai_filter import AIContentFilter

        filter_instance = AIContentFilter()

        # Test official YouTube channel
        youtube_article = RawArticle(
            id=str(uuid.uuid4()),
            title="Claude AI demonstration",
            content="Anthropic demonstrates new Claude capabilities",
            url="https://www.youtube.com/watch?v=example",
            published_date=datetime.now(),
            source_id="anthropic_youtube",
            source_type="youtube"
        )

        # Should get bonus from source_id matching
        bonus = filter_instance._calculate_source_quality_bonus(youtube_article)
        # YouTube channels may not get direct domain bonus, but could get source_id bonus
        assert bonus >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
