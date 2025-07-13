#!/usr/bin/env python3
"""
Generate a test newsletter with real image processing to demonstrate functionality.

This creates a working newsletter with real YouTube thumbnails saved locally.
"""

import sys
import os
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def create_test_newsletter_with_real_images():
    """Create a test newsletter with real images."""
    try:
        from src.utils.image_fetcher import ImageFetcher
        from jinja2 import Environment, FileSystemLoader
        
        print("🚀 Creating Test Newsletter with Real Images")
        print("=" * 55)
        
        # Initialize image fetcher
        fetcher = ImageFetcher()
        
        # Test articles with real URLs
        test_articles = [
            {
                "title": "🤖 AI Agents Weekly: DeepSWE, Cursor 1.2, Evaluating Multi-Agent Systems",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll for testing
                "japanese_title": "🆙 AIエージェント週報：DeepSWE、Cursor 1.2、マルチエージェント評価など",
                "summary_points": [
                    "DeepSWE-Previewが強化学習でコーディングタスクのSOTA達成、SWE-Bench-VerifiedでPass@1 42.2%を記録",
                    "Cursor 1.2がAI統合型エディタとして開発効率を大幅向上、リアルタイムコード補完機能を強化",
                    "マルチエージェントシステムの評価フレームワークが確立され、協調型AI開発の標準化が進展"
                ],
                "source": "AI Newsletter Saravia"
            },
            {
                "title": "How to Sell AI Consulting at High Margins",
                "url": "https://nextword.substack.com/p/how-to-sell-ai-consulting-at-high",
                "japanese_title": "OpenAI、年間1000万ドル顧客へAIコンサル拡大、2025年6月までに120億ドル収益へ",
                "summary_points": [
                    "OpenAIは年間1000万ドル以上の戦略的顧客向けコンサルティングサービスを拡大、長期的な市場浸透戦略を推進",
                    "多くのAIコンサル企業がマージン確保に苦戦する中、OpenAIが高マージンサービスビジネスの新モデルを構築",
                    "エンタープライズAI採用の爆発的増加により、OpenAIの年間収益は2025年6月までに120億ドル到達見込み"
                ],
                "source": "NextWord AI"
            },
            {
                "title": "Context Engineering Guide",
                "url": "https://nlp.elvissaravia.com/p/context-engineering-guide",
                "japanese_title": "LLMコンテキストエンジニアリング完全ガイド",
                "summary_points": [
                    "プロンプトエンジニアリングが「コンテキストエンジニアリング」として再定義され、LLM精度最大化の重要プロセスに",
                    "単純な質問投げかけとは異なり、LLMに最適知識を提供するための包括的アプローチとして確立",
                    "評価パイプラインなど正式手法を用いた効果測定が、開発者の必須スキルとして位置づけ"
                ],
                "source": "AI Newsletter Saravia"
            }
        ]
        
        # Process images for articles
        processed_articles = []
        temp_images = []  # Keep track of temp files
        
        print("\n📷 Processing images for articles...")
        
        for i, article in enumerate(test_articles):
            print(f"\n🧪 Processing article {i+1}: {article['title'][:50]}...")
            
            try:
                # Fetch image
                image_path = fetcher.get_image_from_url(
                    article['url'], 
                    article_id=f"test-article-{i+1}"
                )
                
                if image_path and image_path.exists():
                    file_size = image_path.stat().st_size
                    print(f"   ✅ Image fetched: {file_size:,} bytes")
                    
                    # Create a local URL for demonstration
                    local_image_url = f"./temp_images/article_{i+1}_{image_path.name}"
                    temp_images.append((image_path, local_image_url))
                    
                    # Add image metadata
                    article['image_url'] = local_image_url
                    article['image_metadata'] = {
                        "source_type": "youtube" if "youtube" in article['url'] else "ogp",
                        "dimensions": {"width": 600, "height": 400},  # Estimated
                        "file_size": file_size,
                        "local_path": str(image_path)
                    }
                    
                else:
                    print(f"   ❌ No image found")
                    article['image_url'] = None
                    article['image_metadata'] = None
                    
            except Exception as e:
                print(f"   ❌ Error processing image: {e}")
                article['image_url'] = None
                article['image_metadata'] = None
            
            processed_articles.append(article)
        
        # Create newsletter with Jinja2 template
        print(f"\n📝 Generating newsletter...")
        
        # Load template
        template_path = Path("src/templates/daily_newsletter.jinja2")
        if not template_path.exists():
            print(f"❌ Template not found: {template_path}")
            return False
        
        # Setup Jinja2 environment
        env = Environment(loader=FileSystemLoader('src/templates'))
        
        # Define custom filter
        def toc_format(value):
            if len(value) > 80:
                return value[:77] + "..."
            return value
        
        env.filters['toc_format'] = toc_format
        template = env.get_template('daily_newsletter.jinja2')
        
        # Transform articles to match template structure
        template_articles = []
        for article in processed_articles:
            template_article = {
                "japanese_title": article["japanese_title"],
                "image_url": article.get("image_url"),
                "image_metadata": article.get("image_metadata"),
                "summarized_article": {
                    "filtered_article": {
                        "raw_article": {
                            "url": article["url"]
                        }
                    },
                    "summary": {
                        "summary_points": article["summary_points"]
                    }
                },
                "citations": [{
                    "source_name": article["source"],
                    "url": article["url"],
                    "title": article["title"],
                    "japanese_summary": f"{article['source']}による詳細解説"
                }]
            }
            template_articles.append(template_article)
        
        # Prepare template data
        template_data = {
            "date": datetime.now(),
            "lead_text": {
                "title": "AI技術の最新動向と実践的活用",
                "paragraphs": [
                    "本日のニュースレターでは、AIエージェント技術の最新進展と企業での実践的活用例をお届けします。",
                    "実装された画像埋め込み機能により、視覚的により分かりやすい形で情報をお伝えしています。"
                ]
            },
            "articles": template_articles
        }
        
        # Render newsletter
        newsletter_content = template.render(**template_data)
        
        # Save newsletter
        output_path = Path("drafts/test/2025-07-06_real_images_newsletter.md")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(newsletter_content)
        
        print(f"✅ Newsletter created: {output_path}")
        
        # Create info about images
        print(f"\n📷 Image Information:")
        for i, (temp_path, local_url) in enumerate(temp_images):
            if temp_path.exists():
                file_size = temp_path.stat().st_size
                print(f"   Article {i+1}: {file_size:,} bytes at {temp_path}")
        
        print(f"\n🎉 Test newsletter with real images created successfully!")
        print(f"📄 Check the file: {output_path}")
        print(f"📷 Image files are temporarily stored and will be cleaned up")
        
        # Clean up temp files after a moment
        await asyncio.sleep(1)
        for temp_path, _ in temp_images:
            if temp_path.exists():
                temp_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test newsletter: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    success = await create_test_newsletter_with_real_images()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)