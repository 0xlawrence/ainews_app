#!/usr/bin/env python3
"""
Test newsletter generation with mock data.

This script demonstrates the newsletter generation process
without requiring external APIs or dependencies.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from models.schemas import (
        RawArticle, FilteredArticle, SummaryOutput, 
        SummarizedArticle, ProcessedArticle
    )
    from templates import daily_newsletter
    from jinja2 import Template
    
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Imports not available: {e}")
    IMPORTS_AVAILABLE = False


def create_mock_articles():
    """Create mock articles for testing."""
    
    mock_articles = [
        {
            "id": "article_1",
            "title": "OpenAI Releases GPT-5 with Advanced Reasoning Capabilities",
            "url": "https://openai.com/blog/gpt-5-announcement",
            "published_date": datetime.now(),
            "content": "OpenAI has announced the release of GPT-5, featuring significant improvements in reasoning, mathematics, and multimodal understanding. The new model demonstrates breakthrough performance on complex reasoning tasks and scientific problem-solving.",
            "source_id": "openai_news",
            "source_type": "rss"
        },
        {
            "id": "article_2", 
            "title": "Google DeepMind Introduces Gemini Ultra 2.0",
            "url": "https://deepmind.google/blog/gemini-ultra-2",
            "published_date": datetime.now(),
            "content": "Google DeepMind has unveiled Gemini Ultra 2.0, a next-generation AI model that excels in multimodal understanding and can process video, audio, and text simultaneously with unprecedented accuracy.",
            "source_id": "google_research_blog",
            "source_type": "rss"
        },
        {
            "id": "article_3",
            "title": "Anthropic Claude 4 Achieves New Safety Benchmarks",
            "url": "https://anthropic.com/claude-4-safety",
            "published_date": datetime.now(), 
            "content": "Anthropic has released Claude 4, which sets new standards for AI safety and alignment. The model demonstrates improved helpfulness while maintaining strong safety guardrails and reducing harmful outputs.",
            "source_id": "anthropic_news",
            "source_type": "rss"
        }
    ]
    
    return mock_articles


def create_mock_processed_articles():
    """Create mock processed articles with summaries."""
    
    processed_articles = []
    
    # Article 1: OpenAI GPT-5
    raw_article_1 = {
        "id": "article_1",
        "title": "OpenAI Releases GPT-5 with Advanced Reasoning Capabilities", 
        "url": "https://openai.com/blog/gpt-5-announcement",
        "published_date": datetime.now(),
        "content": "OpenAI announces GPT-5 with breakthrough reasoning...",
        "source_id": "openai_news",
        "source_type": "rss"
    }
    
    summary_points_1 = [
        "OpenAI社がGPT-5を正式発表し、推論能力と数学的問題解決で大幅な性能向上を実現しました",
        "マルチモーダル理解機能が強化され、複雑な科学的問題に対する解答精度が50%向上しています", 
        "企業向けAPIは2025年第2四半期から段階的に提供開始され、月額200ドルからの予定です",
        "研究機関との協力により、医療診断と材料科学分野での実用化が期待されています"
    ]
    
    # Article 2: Google Gemini Ultra 2.0  
    summary_points_2 = [
        "Google DeepMind社がGemini Ultra 2.0を発表し、動画・音声・テキストの同時処理を実現しました",
        "従来比3倍の処理速度で複雑なマルチモーダルタスクを実行可能になっています",
        "YouTube動画の内容理解と要約生成機能が大幅に改善され、教育分野での活用が進んでいます",
        "Google Cloudサービスに2025年3月から統合予定で、開発者向けAPIも同時提供されます"
    ]
    
    # Article 3: Anthropic Claude 4
    summary_points_3 = [
        "Anthropic社がClaude 4を発表し、AI安全性の新たなベンチマークを確立しました",
        "有害なコンテンツ生成率を90%削減しつつ、実用性能は従来比20%向上を達成しています",
        "Constitutional AIの進化により、自己学習による価値観の修正機能を実装しています",
        "企業向けカスタマーサポートでの導入が進み、満足度95%以上を記録しています"
    ]
    
    articles_data = [
        {
            "raw_article": raw_article_1,
            "summary_points": summary_points_1,
            "source_name": "OpenAI News",
            "citations": [
                "**OpenAI News** (https://openai.com/blog/gpt-5-announcement): OpenAI Releases GPT-5 with Advanced Reasoning Capabilities",
                "**TechCrunch** (https://techcrunch.com/gpt5-analysis): GPT-5 represents breakthrough in AI reasoning capabilities",
                "**The Verge** (https://theverge.com/openai-gpt5-review): Early tests show significant improvements in mathematical problem solving"
            ],
            "is_update": False
        },
        {
            "raw_article": {
                "id": "article_2",
                "title": "Google DeepMind Introduces Gemini Ultra 2.0",
                "url": "https://deepmind.google/blog/gemini-ultra-2", 
                "published_date": datetime.now(),
                "content": "Google DeepMind unveils Gemini Ultra 2.0...",
                "source_id": "google_research_blog",
                "source_type": "rss"
            },
            "summary_points": summary_points_2,
            "source_name": "Google Research Blog",
            "citations": [
                "**Google Research Blog** (https://deepmind.google/blog/gemini-ultra-2): Google DeepMind Introduces Gemini Ultra 2.0",
                "**AI Research Channel** (https://youtube.com/watch?v=example1): Gemini Ultra 2.0 Multimodal Demo and Technical Deep Dive"
            ],
            "is_update": False
        },
        {
            "raw_article": {
                "id": "article_3", 
                "title": "Anthropic Claude 4 Achieves New Safety Benchmarks",
                "url": "https://anthropic.com/claude-4-safety",
                "published_date": datetime.now(),
                "content": "Anthropic releases Claude 4 with improved safety...",
                "source_id": "anthropic_news", 
                "source_type": "rss"
            },
            "summary_points": summary_points_3,
            "source_name": "Anthropic News",
            "citations": [
                "**Anthropic News** (https://anthropic.com/claude-4-safety): Anthropic Claude 4 Achieves New Safety Benchmarks"
            ],
            "is_update": True  # This is marked as an update
        }
    ]
    
    return articles_data


def generate_mock_newsletter():
    """Generate a mock newsletter with test data."""
    
    print("🧪 Generating Mock Newsletter")
    print("=" * 50)
    
    # Create mock articles
    articles_data = create_mock_processed_articles()
    
    # Generate lead text
    lead_text = {
        "title": "AI業界の三大巨頭が次世代モデルを相次いで発表：激化する技術競争の最新動向",
        "paragraphs": [
            "OpenAI、Google DeepMind、Anthropicの三大AI企業が、2024年末から2025年初頭にかけて次世代AIモデルを相次いで発表しました。",
            "",
            "OpenAIのGPT-5は推論能力で大幅な向上を実現し、Google DeepMindのGemini Ultra 2.0はマルチモーダル処理で新境地を開拓。一方、AnthropicのClaude 4は安全性の新基準を確立しています。",
            "",
            "各社の技術的差別化が明確になる中、企業向けAPI提供や実用化スケジュールも本格化しており、AI業界の競争は新たな段階に入っています。"
        ]
    }
    
    # Current date
    current_date = datetime.now()
    
    # Processing summary
    processing_summary = {
        "articles_processed": 15,
        "articles_final": 3,
        "processing_time_seconds": 127.5,
        "success_rate": 95.2
    }
    
    # Generation timestamp
    generation_timestamp = current_date.strftime("%Y年%m月%d日 %H:%M")
    
    # Newsletter template (simplified)
    template_content = """# {{ date.strftime('%Y年%m月%d日') }} AI NEWS TLDR

## リード文
{% if lead_text %}
### {{ lead_text.title }}

{% for paragraph in lead_text.paragraphs %}
{{ paragraph }}

{% endfor %}

それでは各トピックの詳細を見ていきましょう。
{% else %}
本日のAI関連ニュースをお届けします。
{% endif %}

## 目次
{% for i, article in articles %}
{{ i + 1 }}. [{{ article.raw_article.title }}](#{{ i + 1 }}-{{ article.raw_article.title | regex_replace('[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '-') | lower }}){% if article.is_update %} 🆙{% endif %}
{% endfor %}

---

{% for i, article in articles %}
## {{ i + 1 }}. {{ article.raw_article.title }}{% if article.is_update %} 🆙{% endif %}

{% for point in article.summary_points %}
- {{ point }}
{% endfor %}

{% for citation in article.citations %}
> {{ citation }}
{% endfor %}

{% if article.is_update %}
**📋 背景**: この記事は以前のClaude 3.5に関する報道の続報として、安全性能の大幅向上を報告しています
{% endif %}

---

{% endfor %}"""

    try:
        from jinja2 import Template
        
        # Create Jinja2 environment with custom filter
        from jinja2 import Environment
        
        def regex_replace(value, pattern, replacement):
            import re
            return re.sub(pattern, replacement, str(value))
        
        env = Environment()
        env.filters['regex_replace'] = regex_replace
        template = env.from_string(template_content)
        
        # Render newsletter
        newsletter_content = template.render(
            date=current_date,
            lead_text=lead_text,
            articles=articles_data,
            processing_summary=processing_summary,
            generation_timestamp=generation_timestamp
        )
        
        # Save to drafts directory
        drafts_dir = Path("drafts")
        drafts_dir.mkdir(exist_ok=True)
        
        output_file = drafts_dir / f"{current_date.strftime('%Y-%m-%d')}_newsletter.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(newsletter_content)
        
        print(f"✅ Newsletter generated successfully!")
        print(f"📄 Output file: {output_file}")
        print(f"📊 Articles included: {len(articles_data)}")
        print(f"📝 Content length: {len(newsletter_content)} characters")
        
        # Display preview
        print("\n" + "=" * 50)
        print("📖 NEWSLETTER PREVIEW")
        print("=" * 50)
        print(newsletter_content[:1000] + "...")
        
        return True
        
    except ImportError:
        print("❌ Jinja2 not available, generating simple text newsletter...")
        
        # Simple text-based newsletter
        simple_newsletter = f"""# {current_date.strftime('%Y年%m月%d日')} AI NEWS TLDR

## リード文
### AI業界の三大巨頭が次世代モデルを相次いで発表：激化する技術競争の最新動向

OpenAI、Google DeepMind、Anthropicの三大AI企業が、2024年末から2025年初頭にかけて次世代AIモデルを相次いで発表しました。

OpenAIのGPT-5は推論能力で大幅な向上を実現し、Google DeepMindのGemini Ultra 2.0はマルチモーダル処理で新境地を開拓。一方、AnthropicのClaude 4は安全性の新基準を確立しています。

各社の技術的差別化が明確になる中、企業向けAPI提供や実用化スケジュールも本格化しており、AI業界の競争は新たな段階に入っています。

それでは各トピックの詳細を見ていきましょう。

## 目次
1. [OpenAI Releases GPT-5 with Advanced Reasoning Capabilities](#1-openai-releases-gpt-5-with-advanced-reasoning-capabilities)
2. [Google DeepMind Introduces Gemini Ultra 2.0](#2-google-deepmind-introduces-gemini-ultra-20)
3. [Anthropic Claude 4 Achieves New Safety Benchmarks](#3-anthropic-claude-4-achieves-new-safety-benchmarks) 🆙

---

## 1. OpenAI Releases GPT-5 with Advanced Reasoning Capabilities

- OpenAI社がGPT-5を正式発表し、推論能力と数学的問題解決で大幅な性能向上を実現しました
- マルチモーダル理解機能が強化され、複雑な科学的問題に対する解答精度が50%向上しています
- 企業向けAPIは2025年第2四半期から段階的に提供開始され、月額200ドルからの予定です
- 研究機関との協力により、医療診断と材料科学分野での実用化が期待されています

> **OpenAI News** (https://openai.com/blog/gpt-5-announcement): OpenAI Releases GPT-5 with Advanced Reasoning Capabilities
> **TechCrunch** (https://techcrunch.com/gpt5-analysis): GPT-5 represents breakthrough in AI reasoning capabilities
> **The Verge** (https://theverge.com/openai-gpt5-review): Early tests show significant improvements in mathematical problem solving

---

## 2. Google DeepMind Introduces Gemini Ultra 2.0

- Google DeepMind社がGemini Ultra 2.0を発表し、動画・音声・テキストの同時処理を実現しました
- 従来比3倍の処理速度で複雑なマルチモーダルタスクを実行可能になっています
- YouTube動画の内容理解と要約生成機能が大幅に改善され、教育分野での活用が進んでいます
- Google Cloudサービスに2025年3月から統合予定で、開発者向けAPIも同時提供されます

> **Google Research Blog** (https://deepmind.google/blog/gemini-ultra-2): Google DeepMind Introduces Gemini Ultra 2.0
> **AI Research Channel** (https://youtube.com/watch?v=example1): Gemini Ultra 2.0 Multimodal Demo and Technical Deep Dive

---

## 3. Anthropic Claude 4 Achieves New Safety Benchmarks 🆙

- Anthropic社がClaude 4を発表し、AI安全性の新たなベンチマークを確立しました
- 有害なコンテンツ生成率を90%削減しつつ、実用性能は従来比20%向上を達成しています
- Constitutional AIの進化により、自己学習による価値観の修正機能を実装しています
- 企業向けカスタマーサポートでの導入が進み、満足度95%以上を記録しています

> **Anthropic News** (https://anthropic.com/claude-4-safety): Anthropic Claude 4 Achieves New Safety Benchmarks

**📋 背景**: この記事は以前のClaude 3.5に関する報道の続報として、安全性能の大幅向上を報告しています

---
"""
        
        # Save simple newsletter
        drafts_dir = Path("drafts")
        drafts_dir.mkdir(exist_ok=True)
        
        output_file = drafts_dir / f"{current_date.strftime('%Y-%m-%d')}_newsletter.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(simple_newsletter)
        
        print(f"✅ Simple newsletter generated successfully!")
        print(f"📄 Output file: {output_file}")
        print(f"📊 Articles included: {len(articles_data)}")
        print(f"📝 Content length: {len(simple_newsletter)} characters")
        
        return True


def main():
    """Main function to test newsletter generation."""
    
    print("🚀 AI News Newsletter Generator - Test Mode")
    print("=" * 60)
    print("")
    
    try:
        success = generate_mock_newsletter()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 Test completed successfully!")
            print("")
            print("📁 Check the 'drafts/' directory for the generated newsletter")
            print("🔍 This demonstrates the full newsletter generation pipeline with:")
            print("   • Structured article summaries in Japanese")
            print("   • Multiple citation sources per article") 
            print("   • Update indicators (🆙) for follow-up stories")
            print("   • Professional newsletter formatting")
            print("   • Lead text with context analysis")
            
        else:
            print("❌ Test failed")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()