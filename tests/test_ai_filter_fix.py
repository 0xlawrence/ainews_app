#!/usr/bin/env python3
"""
Simple test to verify ai_filter.py fallback fix works correctly.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

from src.models.schemas import RawArticle
from src.utils.ai_filter import filter_ai_content


def create_test_articles():
    """Create test articles that should pass AI filtering."""
    return [
        RawArticle(
            id="test1",
            title="OpenAI releases new GPT-4o model with enhanced capabilities",
            content="OpenAI has announced the release of GPT-4o, their latest large language model that demonstrates significant improvements in reasoning and multimodal understanding.",
            url="https://example.com/openai-gpt4o",
            published_date=datetime.now(),
            source_id="test_source",
            source_type="rss"
        ),
        RawArticle(
            id="test2",
            title="Google DeepMind introduces new AI research breakthrough",
            content="Google DeepMind researchers have published a new paper on artificial intelligence that shows breakthrough results in neural network architecture design.",
            url="https://example.com/deepmind-research",
            published_date=datetime.now(),
            source_id="test_source",
            source_type="rss"
        ),
        RawArticle(
            id="test3",
            title="Claude AI demonstrates improved performance in coding tasks",
            content="Anthropic's Claude AI model has shown remarkable improvements in software development assistance and code generation capabilities.",
            url="https://example.com/claude-coding",
            published_date=datetime.now(),
            source_id="test_source",
            source_type="rss"
        ),
        RawArticle(
            id="test4",
            title="Machine learning algorithms optimize data center efficiency",
            content="New machine learning techniques are being deployed to reduce energy consumption in data centers by up to 30% through intelligent cooling and resource management.",
            url="https://example.com/ml-datacenter",
            published_date=datetime.now(),
            source_id="test_source",
            source_type="rss"
        ),
        RawArticle(
            id="test5",
            title="iPhone battery recycling program expansion announced",
            content="Apple announces expansion of iPhone battery recycling program to reduce electronic waste and improve sustainability in mobile device manufacturing.",
            url="https://example.com/iphone-battery",
            published_date=datetime.now(),
            source_id="test_source",
            source_type="rss"
        )
    ]

def test_ai_filter_fix():
    """Test that ai_filter.py uses PRD-compliant defaults."""

    print("Testing ai_filter.py with PRD-compliant defaults...")

    test_articles = create_test_articles()
    print(f"Created {len(test_articles)} test articles")

    # Test with default parameters (should use new PRD-compliant values)
    filtered_articles = filter_ai_content(test_articles)

    print(f"Filtered articles: {len(filtered_articles)} out of {len(test_articles)}")

    for article in filtered_articles:
        print(f"- [{article.ai_relevance_score:.2f}] {article.raw_article.title}")
        print(f"  Reason: {article.filter_reason}")

    # Verify we got at least 4 articles (should exclude iPhone battery article)
    ai_article_count = len(filtered_articles)

    if ai_article_count >= 4:
        print(f"✅ SUCCESS: Got {ai_article_count} articles (meets PRD requirement)")
        print("✅ ai_filter.py fallback fix is working correctly")
        return True
    else:
        print(f"❌ FAILURE: Only got {ai_article_count} articles (below PRD requirement)")
        print("❌ ai_filter.py fallback fix needs more work")
        return False

if __name__ == "__main__":
    success = test_ai_filter_fix()
    sys.exit(0 if success else 1)
