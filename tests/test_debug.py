#!/usr/bin/env python3
"""
Debug script to test basic newsletter generation functionality.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    # Test individual imports
    print("Testing schemas import...")
    from src.models.schemas import (
        ProcessedArticle, SummarizedArticle, FilteredArticle, RawArticle, SummaryOutput, DuplicateCheckResult
    )
    print("✅ Schemas imported successfully")
    
    print("Testing logger import...")
    try:
        from src.utils.logger import setup_logging
        print("✅ Logger imported successfully")
        HAS_LOGGER = True
    except ImportError as e:
        print(f"⚠️ Logger import failed (will use fallback): {e}")
        HAS_LOGGER = False
    
    print("Testing newsletter generator import...")
    from src.utils.newsletter_generator import NewsletterGenerator
    print("✅ Newsletter generator imported successfully")
    
    print("✅ All basic imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def create_test_article(title: str, content: str) -> ProcessedArticle:
    """Create a minimal test article."""
    
    raw_article = RawArticle(
        id=f"test-{title.lower().replace(' ', '-')}",
        title=title,
        content=content,
        url="https://example.com/test",
        source_id="test_source",
        source_type="rss",
        published_date="2025-06-23T08:00:00Z"
    )
    
    # Create more realistic test summary points (avoiding template-like content)
    if "OpenAI" in title:
        summary_points = [
            "OpenAIが次世代言語モデルGPT-5を発表しました。従来比50%の性能向上を実現。",
            "マルチモーダル機能が強化され、動画理解・生成が可能になります。",
            "企業向けAPIは2025年Q3から段階的提供開始予定です。"
        ]
    elif "Google" in title:
        summary_points = [
            "GoogleのGeminiが大幅アップデート。企業向け機能を強化し、APIも改善。",
            "新たなGemini 2.5 Proが発表され、推論能力が大幅に向上しました。",
            "開発者向けのツールチェーンも同時にリリースされました。"
        ]
    else:
        summary_points = [
            "Microsoftが追加で10億ドルのAI研究投資を発表。クラウドサービス強化。",
            "Azure OpenAI Serviceの機能拡張により、企業導入が加速する見込み。",
            "2025年内に新たなAIワークフローツールをリリース予定です。"
        ]
    
    summary = SummaryOutput(
        summary_points=summary_points,
        confidence_score=0.8,
        source_reliability="high"
    )
    
    filtered_article = FilteredArticle(
        raw_article=raw_article,
        filter_reason="AI relevance met",
        ai_relevance_score=0.9
    )
    
    summarized_article = SummarizedArticle(
        filtered_article=filtered_article,
        summary=summary,
        processing_time_seconds=0.5
    )
    
    # Create duplicate check result
    duplicate_check = DuplicateCheckResult(
        is_duplicate=False,
        method="fast_screening",
        processing_time_seconds=0.1
    )
    
    # Create final summary from the summary points
    final_summary = " ".join(summary.summary_points[:2])  # Use first 2 points
    
    return ProcessedArticle(
        summarized_article=summarized_article,
        duplicate_check=duplicate_check,
        final_summary=final_summary,
        citations=[],
        is_update=False
    )

async def test_newsletter_generation():
    """Test basic newsletter generation."""
    
    print("Creating test articles...")
    
    test_articles = [
        create_test_article(
            "OpenAI GPT-5発表", 
            "OpenAIが次世代言語モデルGPT-5を発表しました。従来比50%性能向上を実現。"
        ),
        create_test_article(
            "Google Gemini アップデート",
            "GoogleのGeminiが大幅アップデート。企業向け機能を強化し、APIも改善。"
        ),
        create_test_article(
            "Microsoft AI投資拡大",
            "Microsoftが追加で10億ドルのAI研究投資を発表。クラウドサービス強化。"
        )
    ]
    
    print(f"✅ Created {len(test_articles)} test articles")
    
    # Test newsletter generation
    try:
        generator = NewsletterGenerator()
        print("✅ NewsletterGenerator initialized")
        
        newsletter = await generator.generate_newsletter(
            articles=test_articles,
            edition="daily",
            quality_threshold=0.1  # Very low threshold for testing
        )
        
        print("✅ Newsletter generation completed")
        print(f"   - Title: {newsletter.title}")
        print(f"   - Articles included: {len(newsletter.articles)}")
        print(f"   - Word count: {newsletter.word_count}")
        
        if newsletter.metadata and "output_file" in newsletter.metadata:
            print(f"   - Output file: {newsletter.metadata['output_file']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Newsletter generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing newsletter generation...")
    success = asyncio.run(test_newsletter_generation())
    
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed!")
        sys.exit(1)