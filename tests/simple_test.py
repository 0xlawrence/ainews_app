#!/usr/bin/env python3
"""
Simple test script to validate citation relevance fixes.
"""

import sys

sys.path.append('/Users/shimada/Documents/WorkSpace/ainews_app')

import asyncio

from src.models.schemas import RawArticle
from src.utils.citation_generator import CitationGenerator


async def test_citation_validation():
    """Test the citation validation logic with problematic examples."""

    print("Testing Citation Validation Fixes...")
    print("=" * 50)

    citation_generator = CitationGenerator()

    # Test case 1: Meta research article vs LinkedIn hiring article (should be blocked)
    meta_article = RawArticle(
        id="meta_test",
        title="MetaがOpenAIからトップAI研究者3名を獲得、元DeepMindの精鋭集結",
        content="Meta社は、OpenAIからLucas Beyer氏、Alexander Kolesnikov氏、Xiaohua Zhai氏の3名のトップAI研究者を新たに雇用しました。",
        url="https://example.com/meta-research",
        source_id="test_source",
        published_date="2025-06-27T10:00:00Z",
        source_type="rss"
    )

    linkedin_article = RawArticle(
        id="linkedin_test",
        title="LinkedIn hiring assistant、LinkedInの科学者たちは、人材の…",
        content="LinkedInの科学者たちは、人材のソーシングと採用を支援するAIエージェント「LinkedIn hiring assistant」の開発と活用において成功を収めています。",
        url="https://example.com/linkedin-hiring",
        source_id="test_source",
        published_date="2025-06-27T10:00:00Z",
        source_type="rss"
    )

    # Test domain validation
    same_domain = citation_generator._validate_same_topic_domain(meta_article, linkedin_article)
    print(f"Test 1: Meta research vs LinkedIn hiring - Same domain: {same_domain}")
    print("Expected: False (should be blocked)")

    # Test incompatible citation check
    incompatible = citation_generator._is_incompatible_citation(meta_article.title, linkedin_article.title)
    print(f"Test 1: Meta research vs LinkedIn hiring - Incompatible: {incompatible}")
    print("Expected: True (should be blocked)")
    print()

    # Test case 2: Economic policy vs hiring (should be blocked)
    economic_article = RawArticle(
        id="economic_test",
        title="Anthropic、AI経済フューチャープログラムで雇用喪失への懸念を表明",
        content="AI経済への影響について懸念を表明しています。",
        url="https://example.com/economic-impact",
        source_id="test_source",
        published_date="2025-06-27T10:00:00Z",
        source_type="rss"
    )

    hiring_article = RawArticle(
        id="hiring_test",
        title="Meta CTO confirms massive offers to top AI executives",
        content="Meta社のCTOが、トップAI幹部に対する大規模なオファーを確認しました。",
        url="https://example.com/massive-offers",
        source_id="test_source",
        published_date="2025-06-27T10:00:00Z",
        source_type="rss"
    )

    same_domain_2 = citation_generator._validate_same_topic_domain(economic_article, hiring_article)
    print(f"Test 2: Economic policy vs hiring - Same domain: {same_domain_2}")
    print("Expected: False (should be blocked)")

    incompatible_2 = citation_generator._is_incompatible_citation(economic_article.title, hiring_article.title)
    print(f"Test 2: Economic policy vs hiring - Incompatible: {incompatible_2}")
    print("Expected: True (should be blocked)")
    print()

    # Test case 3: Valid related articles (should be allowed)
    openai_article_1 = RawArticle(
        id="openai_1",
        title="OpenAI releases new GPT-4 Turbo with improved reasoning",
        content="OpenAI announced the release of GPT-4 Turbo with enhanced reasoning capabilities.",
        url="https://example.com/openai-gpt4-turbo",
        source_id="test_source",
        published_date="2025-06-27T10:00:00Z",
        source_type="rss"
    )

    openai_article_2 = RawArticle(
        id="openai_2",
        title="OpenAI expands API access to deep research models",
        content="OpenAI is expanding developer access to its deep research models through API.",
        url="https://example.com/openai-api-access",
        source_id="test_source",
        published_date="2025-06-27T10:00:00Z",
        source_type="rss"
    )

    same_domain_3 = citation_generator._validate_same_topic_domain(openai_article_1, openai_article_2)
    print(f"Test 3: OpenAI model vs OpenAI API - Same domain: {same_domain_3}")
    print("Expected: True (should be allowed)")

    incompatible_3 = citation_generator._is_incompatible_citation(openai_article_1.title, openai_article_2.title)
    print(f"Test 3: OpenAI model vs OpenAI API - Incompatible: {incompatible_3}")
    print("Expected: False (should be allowed)")
    print()

    print("Citation validation tests completed!")
    print("=" * 50)


async def main():
    """Run all tests."""
    await test_citation_validation()

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("- Raised clustering similarity threshold to 0.85")
    print("- Added domain-based topic validation")
    print("- Enhanced citation incompatibility checks")
    print("- Added specific blocks for Meta vs LinkedIn citations")
    print("- These fixes should prevent the ChatGPT guide citing Anthropic/Meta issue")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
