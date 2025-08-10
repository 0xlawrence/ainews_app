"""
Lead text generation and paragraph processing for newsletters.

This module handles the generation of engaging lead text sections that introduce
the newsletter content, including LLM-based generation with validation and fallbacks.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from src.models.schemas import ProcessedArticle
    from src.config.settings import get_settings
    from src.utils.text_processing import truncate_at_sentence_boundary
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

logger = logging.getLogger(__name__)


class LeadGenerator:
    """Generates newsletter lead text and manages paragraph processing."""
    
    def __init__(self, llm_router=None):
        """Initialize lead generator.
        
        Args:
            llm_router: Optional LLM router for advanced lead generation
        """
        self.llm_router = llm_router
        if HAS_DEPENDENCIES:
            self.settings = get_settings()
        else:
            self.settings = None
        
        logger.info("Lead Generator initialized")
    
    async def generate_lead_text(
        self,
        articles: List['ProcessedArticle'],
        edition: str = "daily"
    ) -> Dict[str, Any]:
        """
        Generate engaging lead text for newsletter.

        Args:
            articles: List of processed articles
            edition: Newsletter edition type

        Returns:
            Dictionary with title and paragraphs for lead text
        """
        if not articles:
            return self._generate_default_lead_text(edition)

        # Extract key themes from articles
        themes = self._extract_key_themes(articles)
        
        # Try LLM-based generation first if available
        if self.llm_router:
            try:
                llm_lead_text = await self._generate_llm_lead_text_with_retry(articles, edition)
                if llm_lead_text and llm_lead_text.get('lead_paragraphs'):
                    # Convert LLM format to template-expected format
                    lead_paragraphs = llm_lead_text['lead_paragraphs']

                    # Generate title from first paragraph or articles
                    title = self._generate_lead_title_from_articles(articles, edition)

                    formatted_lead_text = {
                        "title": title,
                        "paragraphs": lead_paragraphs
                    }

                    logger.info(f"LLM lead text generated successfully: {len(lead_paragraphs)} paragraphs")
                    return formatted_lead_text
                else:
                    logger.warning("LLM lead text generation returned empty or invalid result")
            except Exception as e:
                logger.warning(f"LLM lead text generation failed, falling back to template: {e}")
        else:
            logger.info("LLM router not available, using template-based lead text")

        # Fallback to template-based generation
        update_count = sum(1 for article in articles if getattr(article, 'is_update', False))

        # Generate specific lead text directly from articles
        paragraphs = self._generate_specific_lead_paragraphs(articles, edition)
        if not paragraphs:
            # Final fallback
            if edition == "daily":
                paragraphs = [
                    "本日は注目すべきAI関連ニュースを厳選してお届けします。",
                    "企業の新技術発表から研究開発の成果まで、重要な動向をまとめました。",
                    "それでは各トピックの詳細を見ていきましょう。"
                ]
            else:
                # Weekly edition: Fixed 3-sentence structure
                paragraphs = [
                    f"今週は{len(articles)}件のAI関連ニュースを厳選しました。",
                    "技術動向からビジネス活用まで幅広くカバーしています。",
                    "それでは週刊まとめをご覧ください。",
                ]

        # Generate specific title (avoiding generic expressions)
        if themes:
            # Prioritize company/technology names for more specific titles
            specific_titles = self._generate_specific_theme_title(themes, articles)
            title = specific_titles or f"{themes[0]}による技術発表"
        else:
            # Last resort still includes specific content
            title = self._generate_fallback_specific_title(articles)

        # Ensure title ends properly (remove "。", "です", etc.)
        title = re.sub(r"[。.!?ですます]+$", "", title)

        return {
            "title": title,
            "paragraphs": paragraphs,
        }

    async def _generate_llm_lead_text(
        self,
        articles: List['ProcessedArticle'],
        edition: str
    ) -> Optional[Dict[str, Any]]:
        """Generate high-quality lead text using LLM based on article content."""

        # Prepare structured input for LLM
        article_summaries = []

        for i, article in enumerate(articles[:10]):  # Use up to 10 articles for context
            try:
                if (article.summarized_article and
                    article.summarized_article.summary and
                    article.summarized_article.summary.summary_points):

                    summary_points = article.summarized_article.summary.summary_points
                    title = article.japanese_title or article.summarized_article.filtered_article.raw_article.title

                    # Extract key info for structured prompt
                    companies = self._extract_companies(summary_points[0], title) if summary_points else []

                    article_summaries.append({
                        "title": title,
                        "key_points": summary_points[:2],  # First 2 points
                        "companies": companies,
                        "is_update": getattr(article, 'is_update', False)
                    })

            except Exception as e:
                logger.warning(f"Failed to process article {i} for LLM lead text: {e}")
                continue

        if not article_summaries:
            return None

        # Create structured prompt for LLM
        prompt = self._create_lead_text_prompt(article_summaries, edition)

        # Generate lead text using LLM
        try:
            lead_text_response = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=700,  # Increased from 500 to 700 to prevent truncation
                temperature=0.2,  # Low temperature for consistency
            )
        except Exception as e:
            logger.warning(f"LLM call failed in lead text generation: {e}")
            return None

        if not lead_text_response:
            return None

        # Parse LLM response into title and paragraphs
        return self._parse_llm_lead_text_response(lead_text_response)

    def _create_lead_text_prompt(
        self,
        article_summaries: List[Dict],
        edition: str
    ) -> str:
        """Create structured prompt for LLM lead text generation."""

        # Build simple article context without complex JSON
        context_lines = []
        for i, summary in enumerate(article_summaries[:5], 1):  # Limit to top 5
            companies_str = "、".join(summary['companies'][:2]) if summary['companies'] else "AI企業"
            key_point = summary['key_points'][0] if summary['key_points'] else summary['title']
            update_str = " (続報)" if summary.get('is_update', False) else ""

            context_lines.append(f"{i}. {summary['title']}{update_str}")
            if companies_str and companies_str != "AI企業":
                context_lines.append(f"   関連企業: {companies_str}")
            context_lines.append(f"   要点: {key_point[:100]}...")
            context_lines.append("")

        context = "\n".join(context_lines)

        prompt = f"""あなたはプロのニュースライターです。以下のAIニュース要約を基に、一般読者にも分かりやすい魅力的なニュースレターの導入文を生成してください。

【本日の主要記事】
{context}

【導入文の要件（一般読者向け簡潔版）】
- 3つの段落で構成
- 各段落は1文で、70-120文字（読みやすさ重視）
- 第1段落: 最も注目すべきニュースを分かりやすく紹介
- 第2段落: 他の重要な動きを日常生活への影響とともに説明
- 第3段落: これらの変化が私たちの未来にもたらす変化を予測

【厳格禁止事項】
- 専門用語の多用: 「API」「アルゴリズム」「フレームワーク」
- 抽象的表現: 「AI技術の進化」「業界の動向」「関連ニュース」
- 曖昧表現: 「様々な」「多くの」「いくつかの」「複数の企業」
- 冗長表現: 「〜について発表しました」「〜が明らかになりました」
- 不完全文: 「〜が。」「〜は。」等の助詞終わり

【必須要素（各段落に含める）】
- 具体的企業名（OpenAI、Google、Meta等）
- 身近な利用例（チャットボット、検索、翻訳等）
- 日常生活への影響（仕事効率化、学習支援、創作支援等）

【回答形式】
以下の形式で3つの段落を生成してください：

段落1: [第1文をここに記載]
段落2: [第2文をここに記載]
段落3: [第3文をここに記載]

JSONではなく、上記の形式で日本語の文章を直接生成してください。"""

        return prompt

    def _validate_lead_paragraph(self, paragraph: str) -> Tuple[bool, str]:
        """Validate lead paragraph grammar and structure."""

        if not paragraph or len(paragraph.strip()) < 10:
            return False, "段落が短すぎる"

        paragraph = paragraph.strip()

        # Incomplete sentence patterns
        incomplete_patterns = [
            (r'^[^。！？]*[がはをにで]。', "助詞の後に句点"),
            (r'[A-Za-z\u30A0-\u30FF\u3040-\u309F\u4E00-\u9FAF]+が。', "主語の後すぐに句点"),
            (r'[はがをに]$', "助詞で終わる文"),
            (r'[がはをにで]。\s*[^。！？]*$', "文中に不完全な句点")
        ]

        for pattern, reason in incomplete_patterns:
            if re.search(pattern, paragraph):
                return False, f"不完全な文: {reason}"

        # Check for redundant expressions
        if re.search(r'(?:されています|しています).*?(?:と発表|と報告|と説明)', paragraph):
            return False, "重複表現（〜していますと発表）"

        # Length check
        if len(paragraph) > 200:
            return False, "文が長すぎる（200文字超）"

        # Proper ending check
        proper_endings = ('です。', 'ます。', 'ました。', 'ています。', 'でした。', 'ません。')
        if not paragraph.endswith(proper_endings):
            return False, "適切な敬語で終わっていない"

        return True, "OK"

    async def _generate_llm_lead_text_with_retry(
        self, 
        articles: List['ProcessedArticle'], 
        edition: str, 
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Generate lead text with grammar validation and retry logic."""

        for attempt in range(max_retries):
            try:
                result = await self._generate_llm_lead_text(articles, edition)

                if not result or 'lead_paragraphs' not in result:
                    logger.warning(f"Lead text generation attempt {attempt + 1}: No valid response")
                    continue

                # Validate each paragraph
                valid_paragraphs = []
                for i, para in enumerate(result.get('lead_paragraphs', [])):
                    is_valid, reason = self._validate_lead_paragraph(para)
                    if is_valid:
                        valid_paragraphs.append(para)
                        logger.info(f"Lead paragraph {i+1} validated: {para[:50]}...")
                    else:
                        logger.warning(f"Invalid paragraph {i+1}: {reason} - {para[:50]}...")

                # Need at least 2 valid paragraphs
                if len(valid_paragraphs) >= 2:
                    # If less than 3, duplicate and modify the last paragraph
                    while len(valid_paragraphs) < 3:
                        if valid_paragraphs:
                            # Create outlook based on last paragraph
                            base_para = valid_paragraphs[-1]
                            if 'です。' in base_para:
                                expansion = "今後もこれらの動向が業界全体に与える影響に注目が集まります。"
                            else:
                                expansion = "これらの進展により、AI分野における競争と協力がさらに活発化すると予想されます。"
                            valid_paragraphs.append(expansion)
                        else:
                            break

                    result['lead_paragraphs'] = valid_paragraphs[:3]
                    logger.info(f"Lead text generation successful on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"Lead text generation attempt {attempt + 1}: Only {len(valid_paragraphs)} valid paragraphs")

            except Exception as e:
                logger.error(f"Lead text generation attempt {attempt + 1} failed: {e}")

        # All attempts failed - use safe fallback
        logger.warning("All lead text generation attempts failed, using fallback")
        return self._generate_safe_fallback_lead_text(articles)

    def _generate_safe_fallback_lead_text(self, articles: List['ProcessedArticle']) -> Dict[str, Any]:
        """Generate safe fallback: simple and reliable lead text."""

        # Count articles
        article_count = len(articles) if articles else 0

        # Extract major companies
        companies = set()
        for article in articles[:5]:
            if hasattr(article, 'summarized_article') and article.summarized_article:
                title = article.summarized_article.filtered_article.raw_article.title
                # Simple company name extraction
                for company in ['OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'Apple']:
                    if company in title:
                        companies.add(company)

        main_companies = list(companies)[:2]
        companies_str = "、".join(main_companies) if main_companies else "主要AI企業"

        # Generate grammatically reliable sentences
        fallback_paragraphs = [
            f"AI分野において{companies_str}を含む複数の企業が新たな取り組みを発表しました。",
            f"今回は{article_count}件のAI関連ニュースをお届けします。",
            "これらの動向は今後のAI技術の発展に大きな影響を与えることが予想されます。"
        ]

        return {
            'lead_paragraphs': fallback_paragraphs,
            'source': 'safe_fallback',
            'confidence': 0.5
        }

    def _parse_llm_lead_text_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for lead text generation."""

        if not response:
            raise ValueError("Empty response from LLM")

        try:
            # First, try to parse as plain text format (new format)
            lines = response.strip().split('\n')
            paragraphs = []

            for line in lines:
                line = line.strip()

                # Look for lines that start with "段落" or contain actual content
                if line.startswith('段落') and ':' in line:
                    # Extract the content after the colon
                    content = line.split(':', 1)[1].strip()
                    if content and len(content) > 20:
                        paragraphs.append(content)
                elif len(line) > 30 and any(line.endswith(ending) for ending in ['です。', 'ます。', 'ました。', 'ています。', 'でした。']):
                    # This looks like a complete sentence
                    paragraphs.append(line)

            # If we found paragraphs in plain text format, use them
            if len(paragraphs) >= 2:
                # Clean up each paragraph
                cleaned_paragraphs = []
                for para in paragraphs[:3]:  # Take up to 3 paragraphs
                    # Remove any remaining formatting artifacts
                    para = para.strip('[]「」')
                    para = re.sub(r'^\d+\.\s*', '', para)  # Remove numbering

                    # Validate and fix grammar
                    para = self._fix_paragraph_grammar(para)

                    if para and len(para) >= 30:
                        cleaned_paragraphs.append(para)

                if len(cleaned_paragraphs) >= 2:
                    # Ensure we have exactly 3 paragraphs
                    while len(cleaned_paragraphs) < 3:
                        cleaned_paragraphs.append(
                            "今後もAI技術の進化と産業への応用が加速することが期待されています。"
                        )

                    return {
                        'lead_paragraphs': cleaned_paragraphs[:3],
                        'source': 'plain_text_format',
                        'confidence': 0.8
                    }

            # Fallback: Try JSON parsing (legacy format)
            if '```json' in response:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    response = json_match.group(1)

            # Try to parse as JSON
            if response.strip().startswith('{'):
                data = json.loads(response)

                if 'lead_paragraphs' in data:
                    lead_paragraphs = data['lead_paragraphs']
                    if isinstance(lead_paragraphs, list) and len(lead_paragraphs) >= 2:
                        cleaned_paragraphs = []
                        for para in lead_paragraphs[:3]:
                            if isinstance(para, str) and len(para.strip()) > 10:
                                para = self._fix_paragraph_grammar(para.strip())
                                if para:
                                    cleaned_paragraphs.append(para)

                        if len(cleaned_paragraphs) >= 2:
                            while len(cleaned_paragraphs) < 3:
                                cleaned_paragraphs.append(
                                    "これらの技術動向が今後の市場形成に重要な影響を与えると考えられます。"
                                )

                            return {
                                'lead_paragraphs': cleaned_paragraphs[:3],
                                'source': 'json_format',
                                'confidence': data.get('confidence', 0.8)
                            }

            # Final fallback: Extract any good sentences from the response
            all_sentences = re.split(r'[。！？]', response)
            valid_sentences = []

            for sentence in all_sentences:
                sentence = sentence.strip()
                if len(sentence) > 30 and not any(skip in sentence.lower() for skip in ['json', '```', '段落', '形式']):
                    sentence = self._fix_paragraph_grammar(sentence)
                    if sentence:
                        valid_sentences.append(sentence)

            if len(valid_sentences) >= 2:
                return {
                    'lead_paragraphs': valid_sentences[:3],
                    'source': 'extracted_sentences',
                    'confidence': 0.6
                }

            raise ValueError("Could not extract valid lead text from LLM response")

        except Exception as e:
            logger.warning(f"Failed to parse LLM lead text response: {e}")
            raise

    def _fix_paragraph_grammar(self, para: str) -> str:
        """Fix common grammar issues in a paragraph."""

        if not para:
            return ""

        # Fix common LLM generation issues
        # 1. Remove duplicate sentence endings
        para = re.sub(r'([。！？])\1+', r'\1', para)

        # 2. Fix missing punctuation between sentences
        para = re.sub(r'([^\s。！？])([A-Z\u3042-\u3093\u30A2-\u30F3\u4E00-\u9FAF]{3,})', r'\1。\2', para)

        # 3. Fix overly long sentences (split at logical points)
        if len(para) > 120:
            # Split at conjunctions but keep them
            para = re.sub(r'([^\s。！？])(?:また|さらに|一方|なお|ただし|しかし)', r'\1。\2', para)

        # 4. Remove incomplete sentence patterns
        para = re.sub(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)が。\s*', '', para)
        para = re.sub(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)は。\s*', '', para)

        # 5. Fix missing particles before nouns
        para = re.sub(r'([、。])([A-Z][a-z]+)(?:が|は|を|に|で|と)', r'\1\2\3', para)
        para = re.sub(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)を。\s*', '', para)

        # Fix broken sentence connections
        para = re.sub(r'([A-Za-z]+)が。([^。]+)', r'\1が\2', para)
        para = re.sub(r'([A-Za-z]+)は。([^。]+)', r'\1は\2', para)

        # Remove sentences ending with particles
        if para.endswith(('は', 'が', 'を', 'に', 'で', 'と', 'から')):
            para = para[:-1].rstrip()

        # Ensure proper ending
        if para and not para.endswith(('。', '！', '？', '.', '!', '?')):
            if any(word in para for word in ['発表', '開始', '公開', '導入', '提供']):
                para += 'しました。'
            elif any(word in para for word in ['予定', '見込み', '計画', '方針']):
                para += 'です。'
            elif any(word in para for word in ['期待', '予想', '見通し']):
                para += 'されています。'
            else:
                para += '。'

        # Check length
        if len(para) > 200:
            # Truncate at sentence boundary
            sentences = re.split(r'([。！？])', para)
            if len(sentences) >= 3:
                para = sentences[0] + sentences[1]

        return para.strip()

    def truncate_paragraphs_to_limit(self, paragraphs: List[str], char_limit: int) -> List[str]:
        """Truncate paragraphs to fit within character limit while preserving sentence boundaries."""

        if not paragraphs:
            return paragraphs

        truncated = []
        total_chars = 0

        for paragraph in paragraphs:
            if total_chars + len(paragraph) <= char_limit:
                # Entire paragraph fits
                truncated.append(paragraph)
                total_chars += len(paragraph)
            else:
                # Need to truncate this paragraph
                remaining_chars = char_limit - total_chars
                if remaining_chars > 30:  # Only truncate if we have reasonable space
                    try:
                        # Use proper sentence boundary detection if available
                        if HAS_DEPENDENCIES:
                            truncated_para = truncate_at_sentence_boundary(paragraph, max_length=remaining_chars)
                        else:
                            # Fallback truncation
                            truncated_para = paragraph[:remaining_chars]
                            last_sentence_end = truncated_para.rfind('。')
                            if last_sentence_end > 20:
                                truncated_para = paragraph[:last_sentence_end + 1]
                            else:
                                truncated_para = paragraph[:remaining_chars - 1] + '…'
                        
                        if truncated_para and len(truncated_para) > 20:
                            truncated.append(truncated_para)
                        break
                    except Exception:
                        # Fallback to simple truncation
                        truncated_para = paragraph[:remaining_chars]
                        last_sentence_end = truncated_para.rfind('。')
                        if last_sentence_end > 20:
                            truncated_para = paragraph[:last_sentence_end + 1]
                        else:
                            truncated_para = paragraph[:remaining_chars - 1] + '…'
                        truncated.append(truncated_para)
                break  # Stop adding more paragraphs

        return truncated

    # Helper methods for theme and title generation

    def _extract_key_themes(self, articles: List['ProcessedArticle']) -> List[str]:
        """Extract key themes from articles for lead generation."""
        themes = []
        
        for article in articles[:5]:  # Check first 5 articles
            try:
                if (hasattr(article, 'summarized_article') and 
                    article.summarized_article and
                    hasattr(article.summarized_article, 'filtered_article') and
                    article.summarized_article.filtered_article and
                    hasattr(article.summarized_article.filtered_article, 'raw_article')):
                    
                    title = article.summarized_article.filtered_article.raw_article.title
                    # Extract company/tech themes
                    for theme in ['OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'GPT', 'LLM', 'AI']:
                        if theme in title and theme not in themes:
                            themes.append(theme)
                            if len(themes) >= 3:
                                break
            except Exception as e:
                logger.warning(f"Failed to extract themes from article: {e}")
                continue
        
        return themes

    def _extract_companies(self, text: str, title: str = "") -> List[str]:
        """Extract company names from text and title."""
        companies = []
        combined_text = f"{text} {title}"
        
        # Common AI companies
        company_patterns = [
            'OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'Apple',
            'Amazon', 'Tesla', 'NVIDIA', 'Adobe', 'IBM', 'Oracle'
        ]
        
        for company in company_patterns:
            if company in combined_text and company not in companies:
                companies.append(company)
        
        return companies

    def _generate_lead_title_from_articles(self, articles: List['ProcessedArticle'], edition: str) -> str:
        """Generate lead title from articles."""
        if not articles:
            return f"{datetime.now().strftime('%Y年%m月%d日')} AI NEWS TLDR"
        
        # Extract first company/theme
        themes = self._extract_key_themes(articles)
        if themes:
            return f"{themes[0]}関連発表など - AI NEWS TLDR"
        
        return f"{datetime.now().strftime('%Y年%m月%d日')} AI NEWS TLDR"

    def _generate_specific_lead_paragraphs(self, articles: List['ProcessedArticle'], edition: str) -> List[str]:
        """Generate specific lead paragraphs based on articles."""
        if not articles:
            return []
        
        # Simple paragraph generation based on article count and themes
        themes = self._extract_key_themes(articles)
        update_count = sum(1 for article in articles if getattr(article, 'is_update', False))
        
        paragraphs = []
        
        if themes:
            if len(themes) == 1:
                paragraphs.append(f"{themes[0]}から重要な発表があり、AI業界に大きな注目が集まっています。")
            else:
                companies_str = "、".join(themes[:2])
                paragraphs.append(f"{companies_str}をはじめとする企業から相次いで新たな取り組みが発表されました。")
        
        if update_count > 0:
            paragraphs.append(f"本日は{len(articles)}件のニュースをお届けし、そのうち{update_count}件は続報記事となっています。")
        else:
            paragraphs.append(f"今回は{len(articles)}件の最新AI関連ニュースをまとめました。")
        
        paragraphs.append("各企業の動向と技術革新の詳細をご覧ください。")
        
        return paragraphs

    def _generate_specific_theme_title(self, themes: List[str], articles: List['ProcessedArticle']) -> Optional[str]:
        """Generate specific theme-based title."""
        if not themes:
            return None
        
        # Create title based on primary theme
        primary_theme = themes[0]
        
        if len(themes) == 1:
            return f"{primary_theme}新技術発表"
        else:
            return f"{primary_theme}ら主要企業による技術革新"

    def _generate_fallback_specific_title(self, articles: List['ProcessedArticle']) -> str:
        """Generate fallback specific title."""
        if not articles:
            return "AI関連技術動向"
        
        # Count different types of content
        companies = set()
        for article in articles[:3]:
            try:
                if (hasattr(article, 'summarized_article') and 
                    article.summarized_article and
                    hasattr(article.summarized_article, 'filtered_article') and
                    article.summarized_article.filtered_article and
                    hasattr(article.summarized_article.filtered_article, 'raw_article')):
                    
                    title = article.summarized_article.filtered_article.raw_article.title
                    for company in ['OpenAI', 'Google', 'Meta', 'Microsoft']:
                        if company in title:
                            companies.add(company)
            except Exception:
                continue
        
        if companies:
            if len(companies) == 1:
                return f"{list(companies)[0]}技術発表"
            else:
                return f"{len(companies)}社による新技術発表"
        
        return "AI技術最新動向"

    def _generate_default_lead_text(self, edition: str) -> Dict[str, Any]:
        """Generate default lead text when no articles available."""
        if edition == "weekly":
            return {
                "title": "週刊AI NEWS TLDR",
                "paragraphs": [
                    "今週のAI関連ニュースをまとめました。",
                    "技術動向からビジネス活用まで幅広い情報をお届けします。",
                    "各トピックの詳細をご確認ください。"
                ]
            }
        else:
            return {
                "title": f"{datetime.now().strftime('%Y年%m月%d日')} AI NEWS TLDR",
                "paragraphs": [
                    "本日のAI関連ニュースをお届けします。",
                    "最新の技術動向と企業の取り組みをまとめました。",
                    "それでは各ニュースの詳細をご覧ください。"
                ]
            }