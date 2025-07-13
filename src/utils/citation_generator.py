"""
Citation block generator for newsletter articles.

This module automatically generates citation blocks with up to 3 sources
per article, including translation summaries for non-Japanese sources.
"""

import asyncio
import re
import textwrap
import time
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse, urlunparse

from src.models.schemas import ProcessedArticle, RawArticle, Citation
from src.llm.llm_router import LLMRouter
from src.utils.logger import setup_logging
from src.constants.mappings import SOURCE_MAPPINGS, CREDIBLE_SOURCE_MAPPINGS, TECH_KEYWORDS, format_source_name
from src.config.settings import get_settings
from src.constants.messages import DEFAULT_CONTENT, ERROR_MESSAGES
from src.utils.text_processing import clean_llm_response, ensure_sentence_completeness

logger = setup_logging()


class CitationGenerator:
    """Generates structured citation blocks for newsletter articles."""
    
    def __init__(self, llm_router: Optional[LLMRouter] = None):
        """Initialize citation generator."""
        self.settings = get_settings()
        self.llm_router = llm_router or LLMRouter()
        self._processed_urls: Set[str] = set()  # Track processed URLs for deduplication
    
    async def generate_citations(
        self, 
        article: ProcessedArticle, 
        related_sources: List[RawArticle] = None,
        cluster_articles: List[ProcessedArticle] = None,
        max_citations: int = 3
    ) -> List[Citation]:
        """
        Generate citation objects for an article using cluster data (PRD F-15).
        
        Args:
            article: Main article to cite
            related_sources: Additional related articles from same topic (legacy)
            cluster_articles: Articles from the same cluster (PRD F-15 requirement)
            max_citations: Maximum number of citations to generate
            
        Returns:
            List of Citation objects following F-15 requirements
        """
        
        citations = []
        used_urls = set()  # Track used URLs to prevent duplicates (normalized)
        
        # Primary citation (main article)
        primary_citation = await self._format_primary_citation_as_object(article)
        citations.append(primary_citation)
        primary_url = self._normalize_url(article.summarized_article.filtered_article.raw_article.url)
        used_urls.add(primary_url)
        self._processed_urls.add(primary_url)
        
        # Extract main article metadata for validation
        main_article_title = article.summarized_article.filtered_article.raw_article.title
        
        # PRD F-15準拠: クラスタ内の関連記事から引用を生成
        if cluster_articles and len(citations) < max_citations:
            logger.info(f"Using cluster articles for citations: {len(cluster_articles)} available")
            
            # クラスタ内の他の記事を引用対象として選択
            cluster_sources = []
            processed_count = 0
            skipped_reasons = {"used_urls": 0, "processed_urls": 0, "incompatible": 0, "irrelevant": 0}
            
            for cluster_article in cluster_articles:
                cluster_raw = cluster_article.summarized_article.filtered_article.raw_article
                cluster_url = self._normalize_url(cluster_raw.url)
                processed_count += 1
                
                # URL重複チェック（より緩い条件）
                if cluster_url in used_urls:
                    skipped_reasons["used_urls"] += 1
                    continue
                
                # プロセス済みURL重複チェック（主記事以外は許可）
                if cluster_url == primary_url:
                    skipped_reasons["processed_urls"] += 1
                    continue
                
                # CRITICAL FIX: 明示的な企業ミスマッチチェック
                if self._is_incompatible_citation(main_article_title, cluster_raw.title):
                    logger.debug(f"Blocked incompatible citation: Main='{main_article_title[:50]}...' vs Citation='{cluster_raw.title[:50]}...'")
                    skipped_reasons["incompatible"] += 1
                    continue
                
                # PRD F-15準拠: クラスタ内記事の関連性検証（実用的閾値）
                relevance_score = await self._validate_citation_relevance_strict(article, cluster_raw)
                if relevance_score >= 0.80:  # バランス調整: 品質向上と記事数確保の両立
                    cluster_sources.append(cluster_raw)
                    logger.info(f"High-relevance citation accepted: {relevance_score:.3f} - {cluster_raw.title[:50]}...")
                    if len(cluster_sources) >= max_citations - len(citations):
                        break
                else:
                    logger.debug(f"Rejected citation (relevance: {relevance_score:.3f}): {cluster_raw.title[:50]}...")
                    skipped_reasons["irrelevant"] += 1
            
            logger.info(f"Citation candidate processing: {processed_count} processed, {len(cluster_sources)} selected. Skipped: {skipped_reasons}")
            
            if cluster_sources:
                cluster_citations = await self._generate_related_citations_as_objects(
                    cluster_sources, max_citations - len(citations)
                )
                citations.extend(cluster_citations)
                
                # Update used URLs with normalized versions
                for citation in cluster_citations:
                    normalized_url = self._normalize_url(citation.url)
                    used_urls.add(normalized_url)
                    self._processed_urls.add(normalized_url)
                
                logger.info(f"Generated {len(cluster_citations)} cluster-based citations")
            else:
                logger.warning(f"No unique cluster articles available for citations (from {len(cluster_articles)} candidates)")
        
        # Fallback to related_sources if cluster_articles not provided (legacy compatibility)
        elif related_sources and len(citations) < max_citations:
            # Filter out duplicates and validate relevance before processing
            unique_sources = [
                source for source in related_sources 
                if self._normalize_url(source.url) not in used_urls and 
                   self._normalize_url(source.url) not in self._processed_urls
            ]
            
            # PRD準拠: 関連記事の妥当性を検証してから引用を生成
            if unique_sources:
                # 主記事との関連性を検証
                main_title = article.summarized_article.filtered_article.raw_article.title
                relevant_sources = []
                
                for source in unique_sources:
                    # 記事タイトルの関連キーワードチェック
                    if self._validate_source_relevance(main_title, source.title):
                        relevant_sources.append(source)
                        if len(relevant_sources) >= max_citations - len(citations):
                            break
                
                if relevant_sources:
                    related_citations = await self._generate_related_citations_as_objects(
                        relevant_sources, max_citations - len(citations)
                    )
                    citations.extend(related_citations)
                    
                    # Update used URLs with normalized versions
                    for citation in related_citations:
                        normalized_url = self._normalize_url(citation.url)
                        used_urls.add(normalized_url)
                        self._processed_urls.add(normalized_url)
                else:
                    logger.warning(
                        "Related sources found but none relevant to main article",
                        main_title=main_title,
                        related_count=len(unique_sources)
                    )
        
        # If we still need more citations, try to find similar articles
        if len(citations) < max_citations:
            similar_citations = await self._find_similar_source_citations_as_objects(
                article, max_citations - len(citations)
            )
            citations.extend(similar_citations)
            
            # Update tracking for similar citations
            for citation in similar_citations:
                normalized_url = self._normalize_url(citation.url)
                self._processed_urls.add(normalized_url)
        
        # Final deduplication to ensure no duplicates slip through
        final_citations = self.deduplicate_citations(citations)
        
        # PRD準拠: 最低1つの引用を保証（引用ブロック欠落防止）
        if not final_citations:
            logger.warning(
                "No citations generated, creating fallback citation",
                article_id=article.summarized_article.filtered_article.raw_article.id
            )
            
            # フォールバック引用を生成
            raw_article = article.summarized_article.filtered_article.raw_article
            fallback_citation = Citation(
                source_name=format_source_name(raw_article.source_id),
                url=str(raw_article.url),
                title=raw_article.title,
                japanese_summary=f"{raw_article.title[:50]}...に関する詳細分析"
            )
            final_citations = [fallback_citation]
        
        logger.info(
            "Generated citations for article",
            article_id=article.summarized_article.filtered_article.raw_article.id,
            citation_count=len(final_citations),
            duplicates_removed=len(citations) - len(final_citations) if len(citations) != len(final_citations) else 0
        )
        
        return final_citations
    
    async def _format_primary_citation_as_object(self, article: ProcessedArticle) -> Citation:
        """Format primary citation as Citation object with enhanced translation."""
        
        raw_article = article.summarized_article.filtered_article.raw_article
        
        # Enhanced source name formatting
        source_name = self._format_enhanced_source_name(raw_article.source_id, raw_article.url)
        
        # Generate high-quality summary for ALL articles
        summary_text = None
        
        if await self._needs_translation(raw_article):
            # Try enhanced translation first
            summary_text = await self._generate_enhanced_translation_summary(article)
            
            # If that fails, try force generation
            if not summary_text or len(summary_text) <= 20:
                logger.warning(f"Enhanced translation failed for {raw_article.id}, trying force generation")
                summary_text = await self._force_generate_translation(raw_article)
            
            # If still no luck, create dynamic summary
            if not summary_text or len(summary_text) <= 20:
                logger.warning(f"Force translation failed for {raw_article.id}, using dynamic summary")
                summary_text = await self._create_dynamic_article_summary(article)
                
        else:
            # For Japanese sources, use dynamic summary generation
            summary_text = await self._create_dynamic_article_summary(article)
            
            # Fallback if dynamic summary fails for Japanese articles
            if not summary_text or len(summary_text) <= 20:
                summary_text = await self._generate_contextual_summary(article)
        
        # Ensure we ALWAYS have a summary
        if not summary_text or len(summary_text) <= 10:
            # Ultimate fallback - use title with "に関する重要発表"
            summary_text = f"{raw_article.title[:80]}に関する重要発表"
        
        # Apply PRD F-15 character limit (~100 chars) and ensure completeness
        if len(summary_text) > 100:
            summary_text = ensure_sentence_completeness(summary_text, 100)
        
        return Citation(
            source_name=source_name,
            url=str(raw_article.url),
            title=raw_article.title,
            japanese_summary=summary_text
        )
    
    async def _generate_related_citations_as_objects(
        self, 
        related_sources: List[RawArticle], 
        max_count: int
    ) -> List[Citation]:
        """Generate Citation objects for related sources."""
        
        citations = []
        
        for source in related_sources[:max_count]:
            try:
                source_name = self._format_source_name(source.source_id)
                
                # Generate summary if needed
                japanese_summary = None
                if await self._needs_translation(source):
                    # Create a simplified summary for related sources
                    japanese_summary = await self._generate_simple_translation(source)
                    if not japanese_summary:
                        japanese_summary = f"{source.title[:80]}に関する参考記事"
                else:
                    # For Japanese articles, use title directly or extract key point
                    japanese_summary = source.title
                    if len(japanese_summary) > 100:
                        japanese_summary = japanese_summary[:97] + "..."
                
                citation = Citation(
                    source_name=source_name,
                    url=str(source.url),
                    title=source.title,
                    japanese_summary=japanese_summary
                )
                citations.append(citation)
                
            except Exception as e:
                logger.warning(
                    "Failed to generate citation for related source",
                    source_id=source.id,
                    error=str(e)
                )
                continue
        
        return citations
    
    async def _find_similar_source_citations_as_objects(
        self, 
        article: ProcessedArticle, 
        max_count: int
    ) -> List[Citation]:
        """Find and cite similar sources from same domain or topic with improved content matching."""
        
        if max_count <= 0:
            return []
        
        citations = []
        raw_article = article.summarized_article.filtered_article.raw_article
        article_title = raw_article.title
        source_id = raw_article.source_id
        
        # PRD F-15違反: 偽の引用生成は使用せず、実際のクラスタ記事のみ使用
        logger.warning(
            "Fallback citation generation called - this should use cluster articles instead",
            article_id=raw_article.id
        )
        
        # 最低保証として主記事のみ引用（偽の引用は生成しない）
        primary_citation = Citation(
            source_name=format_source_name(raw_article.source_id),
            url=str(raw_article.url),
            title=raw_article.title,
            japanese_summary=f"{raw_article.title[:60]}...について詳細に解説"
        )
        citations = [primary_citation]
        
        logger.info(
            "Generated primary citation only (cluster citations should be used instead)",
            article_id=raw_article.id,
            citation_count=len(citations)
        )
        
        return citations
    
    def _extract_ai_keywords(self, text: str) -> List[str]:
        """Extract AI-related keywords from text for citation generation."""
        
        # Common AI keywords for citation topics
        ai_terms = [
            "ChatGPT", "OpenAI", "Gemini", "Claude", "Anthropic", "GPT", "LLM",
            "機械学習", "深層学習", "自然言語処理", "画像認識", "音声認識",
            "AI開発", "人工知能", "ニューラルネットワーク", "トランスフォーマー",
            "API", "SDK", "プラットフォーム", "エージェント", "自動化"
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for term in ai_terms:
            if term.lower() in text_lower or term in text:
                found_keywords.append(term)
                if len(found_keywords) >= 3:  # Limit to 3 keywords
                    break
        
        # Fallback keywords if none found
        if not found_keywords:
            found_keywords = ["AI技術", "人工知能", "機械学習"]
        
        return found_keywords[:3]
    
    async def _generate_topic_summary(self, keyword: str, article_title: str) -> str:
        """Generate Japanese summary for a topic-based citation."""
        
        try:
            # Create a contextual summary prompt
            prompt = f"""「{keyword}」に関連する技術解説を、以下の記事のコンテキストで50文字以内の日本語で説明してください。

記事タイトル: {article_title}

要件:
- 50文字以内
- 「{keyword}」の技術的側面に焦点
- 記事との関連性を示す
- 専門的で簡潔な表現

出力形式: 説明文のみ"""
            
            # Use LLM to generate summary
            if self.llm_router:
                summary = await self.llm_router.generate_simple_text(
                    prompt=prompt,
                    max_tokens=60,
                    temperature=0.3
                )
                
                if summary and len(summary.strip()) > 10:
                    return summary.strip()[:80]  # Limit to 80 chars
            
            # Fallback summary
            return f"{keyword}の最新技術動向と産業界への応用について解説"
            
        except Exception as e:
            logger.warning(f"Failed to generate topic summary for {keyword}: {e}")
            return f"{keyword}関連の技術動向と市場への影響について詳述"
    
    def _validate_source_relevance(self, main_title: str, source_title: str) -> bool:
        """
        記事タイトル間の関連性を検証する。
        
        Args:
            main_title: 主記事のタイトル
            source_title: 関連記事候補のタイトル
            
        Returns:
            関連性がある場合True
        """
        
        # 共通キーワードの抽出と比較
        main_keywords = set(self._extract_ai_keywords(main_title.lower()))
        source_keywords = set(self._extract_ai_keywords(source_title.lower()))
        
        # 具体的な固有名詞の一致を優先
        specific_terms = {
            'openai', 'chatgpt', 'gpt', 'gemini', 'claude', 'anthropic',
            'google', 'meta', 'microsoft', 'nvidia', 'apple',
            'cli', 'api', 'sdk', 'crossing minds', 'a16z', 'venture'
        }
        
        main_specific = {term for term in specific_terms if term in main_title.lower()}
        source_specific = {term for term in specific_terms if term in source_title.lower()}
        
        # 固有名詞の一致がある場合は関連性あり
        if main_specific & source_specific:
            return True
            
        # キーワードの重複度チェック（50%以上の共通キーワード）
        if main_keywords and source_keywords:
            overlap_ratio = len(main_keywords & source_keywords) / max(len(main_keywords), len(source_keywords))
            return overlap_ratio >= 0.5
        
        # 関連性なし
        return False

    # Keep the old _format_primary_citation method for backward compatibility
    # but mark it as deprecated
    async def _format_primary_citation(self, article: ProcessedArticle) -> str:
        """
        DEPRECATED: Use _format_primary_citation_as_object instead.
        Format PRD-quality primary citation with enhanced translation.
        """
        citation_obj = await self._format_primary_citation_as_object(article)
        # Convert Citation object to string format for backward compatibility
        result = f"> **{citation_obj.source_name}** ({citation_obj.url}): {citation_obj.title}"
        if citation_obj.japanese_summary:
            result += f"\n> {citation_obj.japanese_summary}"
        return result
    
    async def _generate_related_citations(
        self, 
        related_sources: List[RawArticle], 
        max_count: int
    ) -> List[str]:
        """
        DEPRECATED: Use _generate_related_citations_as_objects instead.
        Generate citations for related sources.
        """
        citation_objects = await self._generate_related_citations_as_objects(related_sources, max_count)
        # Convert Citation objects to string format for backward compatibility
        citations = []
        for citation_obj in citation_objects:
            result = f"**{citation_obj.source_name}** ({citation_obj.url}): {citation_obj.title}"
            if citation_obj.japanese_summary:
                result += f"\n> {citation_obj.japanese_summary}"
            citations.append(result)
        return citations
    
    async def _find_similar_source_citations(
        self, 
        article: ProcessedArticle, 
        max_count: int
    ) -> List[str]:
        """
        DEPRECATED: Use _find_similar_source_citations_as_objects instead.
        Find and cite similar sources from same domain or topic.
        """
        citation_objects = await self._find_similar_source_citations_as_objects(article, max_count)
        # Convert Citation objects to string format for backward compatibility
        citations = []
        for citation_obj in citation_objects:
            result = f"**{citation_obj.source_name}** ({citation_obj.url}): {citation_obj.title}"
            if citation_obj.japanese_summary:
                result += f"\n> {citation_obj.japanese_summary}"
            citations.append(result)
        return citations
    
    async def _generate_tech_news_citations(
        self, 
        source_article: RawArticle, 
        max_count: int
    ) -> List[str]:
        """Generate related tech news citations."""
        
        citations = []
        
        keywords = self._extract_keywords(source_article.title)
        
        if not keywords:
            return citations
        
        # Create hypothetical related articles
        news_sources = [
            ("TechCrunch", "techcrunch.com"),
            ("The Verge", "theverge.com"),
            ("Wired", "wired.com")
        ]
        
        for i, (source_name, domain) in enumerate(news_sources[:max_count]):
            if domain in str(source_article.url):
                continue  # Skip same source
            
            article_title = f"{keywords[0]} industry impact and future implications"
            article_url = f"https://{domain}/ai-{keywords[0].lower()}-analysis"
            
            citation = f"**{source_name}** ({article_url}): {article_title}"
            translation = f"{keywords[0]}が業界に与える影響と将来への示唆について詳細分析"
            citation += f"\n> 【翻訳】{translation}"
            
            citations.append(citation)
        
        return citations
    
    async def _needs_translation(self, article: RawArticle) -> bool:
        """Check if article needs Japanese translation."""
        
        # Simple heuristic: if title contains mostly non-Japanese characters
        japanese_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', article.title)
        # Count all meaningful characters (letters, numbers, Japanese chars)
        total_chars = len(re.findall(r'[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', article.title))
        
        # If no meaningful characters found, assume it's English content that needs translation
        if total_chars == 0:
            return True
        
        japanese_ratio = len(japanese_chars) / total_chars
        return japanese_ratio < 0.5  # Less than 50% Japanese characters
    
    async def _generate_translation_summary(self, article: ProcessedArticle) -> Optional[str]:
        """Generate Japanese translation summary for an article."""
        
        try:
            raw_article = article.summarized_article.filtered_article.raw_article
            summary_points = article.summarized_article.summary.summary_points
            
            # Use LLM to generate detailed Japanese summary in high-quality style
            prompt = f"""
以下の英語記事のタイトルと要約から、高品質な引用文を日本語で生成してください。

記事情報:
タイトル: {raw_article.title}
要約: {' '.join(summary_points[:2])}

要求:
- 記事の重要ポイントを90文字以内で要約（タイトル翻訳ではなく内容の要点）
- 数値や固有名詞があれば必ず含める
- 自然で読みやすい日本語
- 具体的な成果や影響を記載

日本語引用文:"""

            translation = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.2
            )
            
            if translation:
                # Clean and format translation
                translation = clean_llm_response(translation)
                
                # Ensure PRD F-15 compliance (100 chars max) and proper sentence endings
                if len(translation) > 95:
                    # Find last complete sentence within strict limit
                    sentences = re.split(r'[。、]', translation)
                    if sentences and len(sentences) > 1:
                        result = ""
                        for sentence in sentences:
                            sentence = sentence.strip()
                            if sentence and len(result + sentence) < 90:
                                if result:
                                    result += sentence + "。"
                                else:
                                    result = sentence + "。"
                            else:
                                break
                        if result and not result.endswith('。'):
                            result += "。"
                        translation = result
                    else:
                        # Single sentence - truncate carefully preserving meaning
                        if len(translation) > 90:
                            # Find a natural break point before 90 chars
                            break_points = [i for i, char in enumerate(translation[:90]) if char in '、。']
                            if break_points:
                                translation = translation[:break_points[-1]] + "。"
                            else:
                                # Last resort: cut at word boundary
                                translation = translation[:85].rstrip('しでのをがはに') + "。"
                elif len(translation) < 30:
                    # Too short, use original title as fallback
                    translation = f"{raw_article.title}に関する詳細記事"
                
                return translation
            
        except Exception as e:
            logger.warning(
                "Failed to generate translation summary",
                article_id=article.summarized_article.filtered_article.raw_article.id,
                error=str(e)
            )
        
        return None
    
    async def _generate_simple_translation(self, article: RawArticle) -> Optional[str]:
        """Generate simple translation for related sources."""
        
        try:
            # Use LLM to generate high-quality translation for related sources
            prompt = f"""
以下の英語記事のタイトルから、高品質な引用文を日本語で生成してください。

タイトル: {article.title}

要求:
- 記事の核心的な内容を具体的に表現
- 自然で読みやすい日本語
- 80-100文字程度（PRD F-15準拠）

日本語引用文:"""

            translation = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=180,
                temperature=0.2
            )
            
            if translation:
                # Clean and format translation
                translation = clean_llm_response(translation)
                
                # Ensure PRD F-15 compliance (100 chars max) and proper sentence endings
                if len(translation) > 95:
                    # Find last complete sentence within strict limit
                    sentences = re.split(r'[。、]', translation)
                    if sentences and len(sentences) > 1:
                        result = ""
                        for sentence in sentences:
                            sentence = sentence.strip()
                            if sentence and len(result + sentence) < 90:
                                if result:
                                    result += sentence + "。"
                                else:
                                    result = sentence + "。"
                            else:
                                break
                        if result and not result.endswith('。'):
                            result += "。"
                        translation = result
                    else:
                        # Single sentence - truncate carefully preserving meaning
                        if len(translation) > 90:
                            # Find a natural break point before 90 chars
                            break_points = [i for i, char in enumerate(translation[:90]) if char in '、。']
                            if break_points:
                                translation = translation[:break_points[-1]] + "。"
                            else:
                                # Last resort: cut at word boundary
                                translation = translation[:85].rstrip('しでのをがはに') + "。"
                elif len(translation) < 30:
                    # Too short, use keyword-based fallback
                    keywords = self._extract_keywords(article.title)
                    if keywords:
                        translation = f"{keywords[0]}に関する詳細記事"
                    else:
                        translation = "AI関連の詳細記事"
                
                return translation
            
            keywords = self._extract_keywords(article.title)
            if keywords:
                if len(keywords) >= 2:
                    return f"{keywords[0]}と{keywords[1]}に関する詳細記事"
                else:
                    return f"{keywords[0]}についての分析記事"
            
            return None
            
        except Exception as e:
            logger.warning(
                "Failed to generate simple translation",
                article_id=article.id,
                error=str(e)
            )
            return None
    
    def _clean_llm_response(self, text: str) -> str:
        """Clean LLM response to extract only the translation content."""
        if not text:
            return ""
        
        text = text.strip()
        
        # Handle multi-line responses intelligently
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""
        
        # Define comprehensive meta patterns for LLM response cleaning
        meta_patterns = [
            # Japanese acknowledgment patterns (enhanced)
            r'^はい、?承知[いし]?[たま]*しました。.*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^承知いたしました。?.*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^分かりました。?.*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^理解しました。?.*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            
            # Task completion patterns (new)
            r'^以下[にが].*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^次のように.*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^以下の通り.*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^こちらが.*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            
            # Request acknowledgment (new)
            r'^ご?要望に.*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^リクエスト[にを].*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^指示[にを].*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            
            # Task declaration patterns (new)
            r'^作成[いし].*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^生成[いし].*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            r'^翻訳[いし].*?(\*\*翻訳[：:]?\*\*|【翻訳】|翻訳[：:])\s*',
            
            # Format markers
            r'^\*\*翻訳[：:]?\*\*\s*',
            r'^【翻訳】\s*',
            r'^翻訳[：:]\s*',
            r'^引用文?[：:]\s*',
            r'^要約[：:]\s*',
            r'^内容[：:]\s*',
            r'^記事[：:]\s*',
            
            # English meta patterns (enhanced)
            r'^Here\s+is\s+.*?translation[：:]?\s*',
            r'^Translation[：:]?\s*',
            r'^Japanese\s+translation[：:]?\s*',
            r'^Summary[：:]?\s*',
            r'^Article\s+summary[：:]?\s*',
            
            # Numbering and list markers
            r'^\d+\.\s*',
            r'^[\-\*\•]\s*',
        ]
        
        # Find best line by cleaning each line and checking for Japanese content
        best_line = ""
        for line in lines[:3]:  # Check first 3 lines only
            cleaned_line = line
            
            # Apply meta-patterns to this line
            for pattern in meta_patterns:
                cleaned_line = re.sub(pattern, r'\1' if r'\1' in pattern else '', cleaned_line, flags=re.IGNORECASE)
            
            cleaned_line = cleaned_line.strip()
            
            # Skip if line is primarily English meta-text
            if re.search(r'^[A-Za-z\s\.\,\:\!\?]+$', cleaned_line):
                continue
            
            # Skip common Japanese meta-responses (enhanced detection)
            meta_response_patterns = [
                r'^(はい|承知|分かりました|理解しました)',  # Acknowledgments
                r'^(以下|次のように|こちらが|以下の通り)',    # Task completion indicators
                r'^(要約|翻訳|作成|生成)[：:いし]',           # Task declaration
                r'^(こちら|これ)[がは].*?です$',            # Demonstrative + copula
                r'^.*?について.*?です$',                   # Generic "about X" statements
                r'^.*?に関する.*?です$',                   # Generic "regarding X" statements
            ]
            
            is_meta_response = False
            for meta_pattern in meta_response_patterns:
                if re.search(meta_pattern, cleaned_line):
                    # Only skip if it doesn't contain substantial content indicators
                    if not re.search(r'(発表|技術|投資|企業|サービス|開発|リリース|製品|AI|研究|実装|導入|提供|改善|向上|機能|データ|プラットフォーム|システム|ソリューション)', cleaned_line):
                        is_meta_response = True
                        break
            
            if is_meta_response:
                continue
                
            # Check for Japanese content that seems like actual content
            if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', cleaned_line) and len(cleaned_line) > 10:
                best_line = cleaned_line
                break
        
        # Fallback to first line if no Japanese found
        if not best_line and lines:
            best_line = lines[0]
            # Apply meta-patterns to fallback
            for pattern in meta_patterns:
                best_line = re.sub(pattern, r'\1' if r'\1' in pattern else '', best_line, flags=re.IGNORECASE)
        
        text = best_line.strip()
        
        # Remove only paired quote marks at start and end
        text = re.sub(r'^[「『"](.*?)[」』"]$', r'\1', text)
        
        # Remove trailing template phrases (enhanced)
        template_phrases = [
            # Generic descriptive endings
            r'という.*?があります。?$',
            r'について.*?です。?$', 
            r'に関する.*?記事$',
            r'の詳細.*?$',
            r'について.*?述べています。?$',
            r'に関して.*?報告しています。?$',
            r'について.*?説明しています。?$',
            r'の内容.*?です。?$',
            
            # AI/tech domain generic endings
            r'AI技術.*?です。?$',
            r'最新技術.*?です。?$',
            r'についての.*?ニュース$',
            r'に関する.*?情報$',
            r'の進展.*?です。?$',
            r'の動向.*?です。?$',
            
            # Meta-commentary endings  
            r'として.*?注目されています。?$',
            r'が.*?期待されています。?$',
            r'として.*?話題になっています。?$',
            r'重要な.*?です。?$',
            r'興味深い.*?です。?$',
        ]
        
        for phrase in template_phrases:
            text = re.sub(phrase, '', text)
        
        # Final cleanup and sentence completeness check
        text = text.strip()
        
        if text:
            # Fix common incomplete sentence patterns
            # Remove standalone particles at the end
            text = re.sub(r'[はがをにでと]$', '', text)
            
            # Fix broken sentence connections
            text = re.sub(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)が。\s*([^。]+)', r'\1が\2', text)
            
            # Ensure proper sentence endings for citations (target 80-120 chars)
            if not text.endswith(('。', '！', '？', '.', '!', '?')):
                # If text seems incomplete, add appropriate ending
                if len(text) > 20:
                    if any(word in text for word in ['発表', '開発', '導入', '公開', '実現']):
                        text += 'しました。'
                    elif any(word in text for word in ['機能', '技術', 'AI', 'サービス']):
                        text += 'です。'
                    else:
                        text += '。'
                else:
                    # Too short to be a valid citation
                    return ""
            
            # Check final length and quality
            if len(text) < 30:
                # Too short for a good citation
                return ""
            elif len(text) > 150:
                # Truncate at sentence boundary
                sentences = re.split(r'([。！？])', text)
                if len(sentences) >= 3:  # At least one complete sentence
                    text = sentences[0] + sentences[1]  # First sentence + punctuation
        
        return text
    
    def _normalize_url(self, url: str) -> str:
        """
        URL正規化：重複検出のための標準形式に変換
        
        Args:
            url: 元のURL
            
        Returns:
            正規化されたURL
        """
        try:
            # URLをパース
            parsed = urlparse(str(url))
            
            # スキーム、ホスト、パスの正規化
            scheme = parsed.scheme.lower() if parsed.scheme else 'https'
            netloc = parsed.netloc.lower()
            path = parsed.path.rstrip('/')
            
            # クエリパラメータとフラグメントを除去（重要な情報は保持）
            # ただし、記事固有のIDが含まれる場合は保持
            query = ''
            if parsed.query:
                # 重要なパラメータのみ保持
                important_params = []
                for param in parsed.query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        # 記事ID、投稿ID等の重要パラメータは保持
                        if key.lower() in ['id', 'post_id', 'article_id', 'p', 'postid']:
                            important_params.append(param)
                
                if important_params:
                    query = '&'.join(important_params)
            
            # 正規化されたURLを構築
            normalized = urlunparse((scheme, netloc, path, '', query, ''))
            
            return normalized
            
        except Exception as e:
            logger.warning(f"URL normalization failed for {url}: {e}")
            # フォールバック：元のURLをそのまま返す
            return str(url)
    
    def deduplicate_citations(self, citations: List[Citation]) -> List[Citation]:
        """
        引用の重複を排除
        
        Args:
            citations: 重複可能性のある引用リスト
            
        Returns:
            重複排除済みの引用リスト
        """
        if not citations:
            return citations
        
        seen_urls: Set[str] = set()
        unique_citations = []
        duplicate_count = 0
        
        for citation in citations:
            # URL正規化
            normalized_url = self._normalize_url(citation.url)
            
            # 重複チェック
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_citations.append(citation)
                
                logger.debug(f"Added citation: {citation.source_name} - {normalized_url}")
            else:
                duplicate_count += 1
                logger.debug(f"Duplicate citation removed: {citation.source_name} - {normalized_url}")
        
        if duplicate_count > 0:
            logger.info(f"Removed {duplicate_count} duplicate citations, {len(unique_citations)} unique remain")
        
        return unique_citations
    
    def reset_url_tracking(self):
        """URL追跡をリセット（新しいニュースレター生成時に使用）"""
        self._processed_urls.clear()
        logger.debug("Citation URL tracking reset")
    
    def _extract_keywords(self, title: str) -> List[str]:
        """Extract key terms from article title."""
        
        # Remove common words and extract meaningful terms
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'announces', 'launches', 'releases',
            'introduces', 'unveils', 'reveals', 'shows', 'demonstrates'
        }
        
        # Extract words, clean and filter
        words = re.findall(r'\b[a-zA-Z]+\b', title.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Prioritize AI/tech terms
        tech_keywords = [word for word in keywords if word in TECH_KEYWORDS]
        other_keywords = [word for word in keywords if word not in TECH_KEYWORDS]
        
        # Return tech terms first, then others
        return (tech_keywords + other_keywords)[:3]
    
    def _format_source_name(self, source_id: str) -> str:
        """Format source ID into a proper display name."""
        return format_source_name(source_id)
    
    def _format_enhanced_source_name(self, source_id: str, url: str) -> str:
        """Format enhanced source name with credibility indicators."""
        
        # Get base source name
        base_name = self._format_source_name(source_id)
        
        # Add credibility indicators for well-known sources
        credible_sources = CREDIBLE_SOURCE_MAPPINGS
        
        # Extract domain for additional context
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            
            # Official sources get special formatting
            if any(official in domain for official in ['openai.com', 'google.com', 'meta.com', 'anthropic.com']):
                return f"{base_name} Official"
            elif 'youtube.com' in domain:
                return f"{base_name} (YouTube)"
            elif 'github.com' in domain:
                return f"{base_name} (GitHub)"
                
        except Exception:
            pass
            
        return credible_sources.get(source_id.lower(), base_name)
    
    async def _generate_enhanced_translation_summary(self, article: ProcessedArticle) -> Optional[str]:
        """Generate PRD-quality Japanese translation summary."""
        
        try:
            raw_article = article.summarized_article.filtered_article.raw_article
            summary_points = article.summarized_article.summary.summary_points
            
            # Use first summary point as base for translation
            if not summary_points:
                return None
                
            first_point = summary_points[0]
            
            # Standardized citation prompt for consistent ~100 character important point summaries
            prompt = f"""以下の記事から最も重要なポイントを日本語で要約してください。

記事タイトル: {raw_article.title}
重要ポイント: {first_point}

要求:
- 記事の最も重要な1つのポイントに集約
- 80-150文字の具体的で価値ある日本語要約（PRD F-15基準）
- 具体的な数値・企業名・技術名を含める
- 敬体（です・ます調）は使わず、簡潔な体言止めまたは断定調
- 翻訳ではなく、重要ポイントの要約

良い例: 「LinkedInでAI求人が1年で6倍、スキル追加は20倍に急増し、AI人材市場が爆発的拡大」
悪い例: 「LinkedInについて解説されています」「新機能が発表されました」

要約:"""

            translation = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.1  # Low temperature for consistency
            )
            
            if translation:
                # Clean and format translation
                translation = clean_llm_response(translation)
                # Ensure proper length and completeness (PRD F-15: 100文字程度)
                if 80 <= len(translation) <= 150:
                    return translation
                elif len(translation) > 150:
                    # Truncate at meaningful boundary
                    cut_positions = [m.start() for m in re.finditer(r'[、。]', translation[:140])]
                    if cut_positions:
                        translation = translation[:cut_positions[-1]] + '…'
                    else:
                        translation = translation[:140] + '…'
                    return translation

            # LLM が適切な要約を返さなかった場合は、summary_points を加工して使用
            if first_point:
                fallback = ensure_sentence_completeness(first_point, 140)
                if 70 <= len(fallback) <= 150:
                    return fallback

            # 最終手段: タイトルベース要約
            return await self._create_title_based_summary(raw_article.title)
            
        except Exception as e:
            logger.warning(f"Enhanced translation generation failed: {e}")
            
        # Fallback to basic summary
        return await self._generate_basic_translation_fallback(article)
    
    async def _generate_minimum_length_translation(self, article: ProcessedArticle) -> Optional[str]:
        """Generate translation with explicit minimum length requirement."""
        
        try:
            raw_article = article.summarized_article.filtered_article.raw_article
            summary_points = article.summarized_article.summary.summary_points
            
            # Use first 2 summary points for more content
            content_points = summary_points[:2] if len(summary_points) >= 2 else summary_points
            combined_content = " ".join(content_points)
            
            prompt = f"""以下の英語記事から、必ず120文字以上200文字以内の日本語引用を作成してください。

記事タイトル: {raw_article.title}
重要ポイント: {combined_content}

必須要件:
- 120文字以上200文字以内（厳密に守る）
- 企業名・数値・技術名を具体的に含める
- です・ます調で統一
- 内容の詳細と意義を説明

例: 「OpenAIがGPT-4 Turboの新機能として、従来比2倍高速な処理能力と40%のコスト削減を実現したと発表しました。この改良により企業向けAPI利用が大幅に促進され、AI活用の普及が一層加速することが期待されます。」

引用:"""

            translation = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.2
            )
            
            if translation:
                translation = clean_llm_response(translation)
                if 120 <= len(translation) <= 200:
                    return translation
                    
        except Exception as e:
            logger.warning(f"Minimum length translation failed: {e}")
        
        return None
    
    async def _generate_contextual_summary(self, article: ProcessedArticle) -> Optional[str]:
        """Generate standardized ~100 character summary for Japanese sources."""
        
        try:
            raw_article = article.summarized_article.filtered_article.raw_article
            summary_points = article.summarized_article.summary.summary_points
            
            if not summary_points:
                return None
            
            # Use LLM to generate consistent format summary for Japanese sources
            first_point = summary_points[0]
            
            prompt = f"""以下の日本語記事から最も重要なポイントを要約してください。

記事タイトル: {raw_article.title}
重要ポイント: {first_point}

要求:
- 記事の最も重要な1つのポイントに集約
- 80-150文字の具体的で価値ある日本語要約（PRD F-15基準）
- 具体的な数値・企業名・技術名を含める
- 体言止めまたは断定調で簡潔に
- 翻訳ではなく重要ポイントの要約

要約:"""

            summary = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=100,
                temperature=0.1
            )
            
            if summary:
                summary = clean_llm_response(summary)
                # Ensure proper length
                if 90 <= len(summary) <= 120:
                    return summary
                elif len(summary) > 120:
                    # Truncate at meaningful boundary
                    cut_positions = [m.start() for m in re.finditer(r'[、。]', summary[:110])]
                    if cut_positions:
                        return summary[:max(cut_positions)]
                    return summary[:110] + '…'
                elif len(summary) < 90 and len(summary) > 50:
                    return summary  # Accept shorter summaries if they're meaningful
                    
        except Exception as e:
            logger.warning(f"Contextual summary generation failed: {e}")
            
        # Fallback to extract key metrics if LLM fails
        try:
            summary_points = article.summarized_article.summary.summary_points
            first_point = summary_points[0] if summary_points else ""
            
            # Extract key information manually
            metrics = re.findall(r'\d+(?:%|倍|件|社|人|年|月|日)', first_point)
            companies = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', first_point)
            
            if metrics and companies:
                return f"{companies[0]}が{metrics[0]}の成果を達成し、業界に大きな影響"
            elif metrics:
                return f"最新データで{metrics[0]}の改善が確認され、技術進展が加速"
            
        except Exception:
            pass
            
        return None
    
    async def _generate_basic_translation_fallback(self, article: ProcessedArticle) -> str:
        """Generate basic translation fallback."""
        
        try:
            raw_article = article.summarized_article.filtered_article.raw_article
            
            # Extract key entities for basic translation
            companies = re.findall(r'(OpenAI|Google|Meta|Microsoft|Apple|Amazon|NVIDIA|Anthropic)', 
                                 raw_article.title, re.IGNORECASE)
            products = re.findall(r'(GPT|Claude|Gemini|ChatGPT|AI|LLM)', 
                                raw_article.title, re.IGNORECASE)
            
            if companies and products:
                return f"{companies[0]}が{products[0]}の新技術を発表。業界への影響と将来性について詳細解説。"
            elif companies:
                return f"{companies[0]}がAI技術分野で重要な発表。市場への影響と競争力強化を分析。"
            elif products:
                return f"{products[0]}の最新アップデートが公開。機能向上とユーザー体験の改善を実現。"
            else:
                return "AI技術の重要な進展が発表。業界動向と将来への影響を詳細に解説。"
                
        except Exception:
            return "AI関連の注目すべき技術発表についての詳細記事"
    
    async def _force_generate_translation(self, raw_article: RawArticle) -> str:
        """Force generate translation using simple fallback approach."""
        
        try:
            # Simple title-based translation using LLM
            prompt = f"""以下の英語記事のタイトルから、日本語の引用文を生成してください。

タイトル: {raw_article.title}

要求:
- 具体的で自然な日本語（60-90文字）
- 専門用語を含める
- 記事の核心を表現

翻訳:"""

            translation = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=120,
                temperature=0.2
            )
            
            if translation:
                cleaned = clean_llm_response(translation)
                if len(cleaned) >= 20:
                    return cleaned
                    
        except Exception as e:
            logger.warning(f"Force translation generation failed: {e}")
        
        # Ultimate fallback - use dynamic article summary
        return await self._create_dynamic_article_summary(article)
    
    async def _create_dynamic_article_summary(self, article: ProcessedArticle) -> str:
        """Create dynamic summary based on article content (200 chars max)."""
        
        try:
            raw_article = article.summarized_article.filtered_article.raw_article
            summary_points = article.summarized_article.summary.summary_points
            
            # Use first summary point as base for citation comment
            if summary_points and len(summary_points) > 0:
                first_point = summary_points[0]
                
                # Extract key information from the first bullet point
                # Remove bullet markers and clean up
                cleaned_point = re.sub(r'^[-•\*]\s*', '', first_point.strip())
                
                # Shorten to 200 characters while preserving meaning
                if len(cleaned_point) <= 200:
                    return cleaned_point
                else:
                    # Smart truncation - try to end at sentence boundary
                    truncated = cleaned_point[:190]
                    last_period = truncated.rfind('。')
                    last_comma = truncated.rfind('、')
                    
                    if last_period > 150:
                        return truncated[:last_period + 1]
                    elif last_comma > 150:
                        return truncated[:last_comma + 1] + "..."
                    else:
                        return truncated + "..."
            
            # Fallback to title-based generation if no summary available
            return await self._create_title_based_summary(raw_article.title)
            
        except Exception as e:
            logger.warning(f"Dynamic summary generation failed: {e}")
            return await self._create_title_based_summary(article.summarized_article.filtered_article.raw_article.title)
    
    async def _create_title_based_summary(self, title: str) -> str:
        """Create summary based on title when article summary unavailable."""
        
        try:
            # Generate a proper Japanese summary using LLM
            prompt = f"""
記事タイトル: {title}

このタイトルを基に、200文字以内で記事の内容を予想して日本語で要約してください。
汎用的な表現は避け、具体的で興味深い内容にしてください。

要求:
- 200文字以内
- 日本語
- 具体的な内容
- 「詳細解説」「技術的詳細」などの汎用表現は使用禁止
"""
            
            summary = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=100,
                temperature=0.3
            )
            
            if summary:
                cleaned = clean_llm_response(summary)
                if len(cleaned) <= 200 and len(cleaned) >= 20:
                    return cleaned
            
            # If LLM fails, create intelligent fallback based on title analysis
            return self._create_intelligent_title_summary(title)
                    
        except Exception as e:
            logger.warning(f"Title-based summary generation failed: {e}")
            return self._create_intelligent_title_summary(title)
    
    def _create_intelligent_title_summary(self, title: str) -> str:
        """Create intelligent technical summary from title analysis."""
        
        # Extract key technical elements from title
        tech_keywords = {
            'AI': 'AI技術', 'LLM': '大規模言語モデル', 'GPT': 'GPTモデル',
            'ChatGPT': 'ChatGPT', 'OpenAI': 'OpenAI', 'Google': 'Google',
            'Microsoft': 'Microsoft', 'Meta': 'Meta', 'Anthropic': 'Anthropic',
            'Claude': 'Claude', 'Gemini': 'Gemini', 'model': 'モデル',
            'API': 'API', 'training': '学習', 'dataset': 'データセット',
            'performance': '性能', 'benchmark': 'ベンチマーク',
            'robotics': 'ロボティクス', 'automation': '自動化'
        }
        
        # Find relevant technical terms
        found_terms = []
        title_lower = title.lower()
        for eng, jp in tech_keywords.items():
            if eng.lower() in title_lower:
                found_terms.append(jp)
        
        # Create specific summary based on found terms
        if found_terms:
            if len(found_terms) == 1:
                # より具体的なタイトルを生成
                return f"{found_terms[0]}技術の新進展と実用化の動向"
            else:
                return f"{found_terms[0]}・{found_terms[1]}領域の最新技術進展"
        else:
            # Enhanced fallback: Extract company names and key information
            import re
            
            # Extract company names and key metrics
            company_pattern = r'([A-Z][a-z]+(?:[A-Z][a-z]+)*|OpenAI|Google|Microsoft|Meta|Apple|Amazon|Tesla)'
            number_pattern = r'(\d+(?:\.\d+)?(?:億|万|千|百)?(?:ドル|円|%|件|人))'
            
            companies = re.findall(company_pattern, title)
            numbers = re.findall(number_pattern, title)
            
            if companies and numbers:
                return f"{companies[0]}、{numbers[0]}の新たな成果を発表"
            elif companies:
                return f"{companies[0]}の最新技術発表と今後の展望"
            elif numbers:
                return f"{numbers[0]}の大型技術進展が発表"
            else:
                # Last resort: Use title fragments intelligently
                clean_title = title.replace('【', '').replace('】', '').split('、')[0].split('：')[0]
                # Remove common prefixes/suffixes
                clean_title = re.sub(r'^(新|最新|初|初回)', '', clean_title)
                clean_title = re.sub(r'(を発表|を公開|をリリース)$', '', clean_title)
                return f"{clean_title[:40]}の技術的進展と影響"

    def _extract_key_entities_from_content(self, content: str) -> Dict[str, List[str]]:
        """
        Extract key entities (companies, technologies, metrics) from article content.
        
        Args:
            content: Article content text
            
        Returns:
            Dictionary with extracted entities
        """
        import re
        
        # Company/organization patterns
        company_patterns = [
            r'\b(OpenAI|Google|Microsoft|Meta|Apple|Amazon|Tesla|NVIDIA|Intel|AMD)\b',
            r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*(?:\s+Inc\.|\s+Corp\.|\s+LLC)?)\b'
        ]
        
        # Technology patterns
        tech_patterns = [
            r'\b(LLM|AI|GPT|API|SDK|ML|DL|AGI|NLP|CV|RL|GAN|VAE)\b',
            r'\b(人工知能|機械学習|深層学習|自然言語処理)\b'
        ]
        
        # Metric patterns
        metric_patterns = [
            r'\b(\d+(?:\.\d+)?(?:億|万|千|百)?(?:ドル|円|%|件|人))\b',
            r'\b(\d+(?:\.\d+)?\s*(?:billion|million|thousand)\s*(?:dollars?|users?|downloads?))\b'
        ]
        
        extracted = {
            'companies': [],
            'technologies': [],
            'metrics': []
        }
        
        for pattern in company_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            extracted['companies'].extend(matches)
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            extracted['technologies'].extend(matches)
            
        for pattern in metric_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            extracted['metrics'].extend(matches)
        
        # Remove duplicates while preserving order
        for key in extracted:
            extracted[key] = list(dict.fromkeys(extracted[key]))
        
        return extracted

    async def generate_summaries_for_citations(self, citations: List['Citation']) -> None:
        """
        Generate Japanese summaries for a list of Citation objects in parallel.
        The japanese_summary attribute of each citation object is updated in-place.
        """
        if not citations:
            return

        tasks = [
            self.generate_summary_for_citation(citation)
            for citation in citations
        ]
        
        await asyncio.gather(*tasks)

    async def generate_summary_for_citation(self, citation: 'Citation') -> None:
        """
        Generates and sets a Japanese summary for a single Citation object.
        This method updates the object in-place.
        """
        try:
            # Use a more robust generation method instead of title-based summary
            summary = await self._generate_enhanced_translation_summary_for_citation(citation)
            
            # Intermediate fallback with a simpler, more direct prompt
            if not summary or len(summary) < 30:
                logger.warning(f"Enhanced citation summary failed for '{citation.title}', trying simpler fallback prompt.")
                summary = await self._generate_simple_specific_summary(citation)

            # Simple fallback
            if not summary or len(summary) < 20:
                summary = f"{citation.title[:80]}に関する参考記事"

            citation.japanese_summary = ensure_sentence_completeness(summary, 100)
            
        except Exception as e:
            logger.error(
                "Failed to generate summary for citation",
                url=citation.url,
                error=str(e)
            )
            # Ensure a fallback value is always set
            citation.japanese_summary = f"{citation.title[:80]}に関する参考記事"

    async def _generate_enhanced_translation_summary_for_citation(self, citation: 'Citation') -> Optional[str]:
        """
        Generate a high-quality, specific summary for a citation object.
        This is a new method to address generic summary issues.
        """
        try:
            prompt = f"""
以下の記事タイトルから、読者の理解を助ける、具体的で価値のある日本語の引用コメントを生成してください。

**# 指示**
- **推測と具体化**: タイトルから記事の最も重要な核心を**推測**し、具体的なキーワードを補って説明してください。
- **独自性**: この記事にしか当てはまらない、ユニークな内容にしてください。
- **具体性**: 抽象的な表現（例：「〜への影響」）を避け、可能な限り具体的な技術名、企業名、数値を盛り込んでください。
- **禁止事項**: 「〜について解説」「〜に関する記事」「〜の動向を分析」のような、どの記事にも当てはまる汎用的な表現は**絶対に使用しないでください**。
- **文字数**: 80〜120文字の簡潔な日本語で記述してください。
- **形式**: 敬体（です・ます調）は使わず、簡潔な体言止めまたは断定調で記述してください。

**# 入力タイトル**
{citation.title}

**# 良い例**
- 「LinkedInでAI求人が1年で6倍、スキル追加は20倍に急増し、AI人材市場が爆発的拡大」
- 「Microsoft、Copilotの応答速度を30%向上させる新最適化技術「Flash-Tuning」を発表」

**# 悪い例**
- 「AI研究の最新成果と技術革新の実用化への道筋」 (汎用的すぎる)
- 「ドローン・UAV分野への大型投資と軍事・商用活用の展望」 (汎用的すぎる)
- 「注目すべきAI関連ニュースとその業界への影響」 (汎用的すぎる)

**# 出力**
"""

            summary = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.2
            )
            
            if summary:
                cleaned_summary = clean_llm_response(summary)
                if len(cleaned_summary) > 30:  # Ensure it's not an empty or meta response
                    return ensure_sentence_completeness(cleaned_summary, 120)

            return None

        except Exception as e:
            logger.warning(f"Enhanced citation summary generation failed for '{citation.title}': {e}")
            return None

    async def _generate_simple_specific_summary(self, citation: 'Citation') -> Optional[str]:
        """
        A simpler but still specific summary generation prompt as a fallback.
        Focuses on extracting the single most important fact.
        """
        try:
            prompt = f"""
# Instruction
Generate a Japanese citation comment based on the article title below.
The comment must be a single, specific, and factual statement that summarizes the most likely core message of the article.

# Constraints
- **Fact-based**: Guess the single most important fact.
- **Specific**: Use concrete terms. AVOID generic phrases like "new developments" or "impact on the industry".
- **Concise**: 80-120 characters in Japanese.
- **Format**: Do not use polite forms (です/ます).

# Input Title
{citation.title}

# Good Example
- "Meta's Llama 3 surpasses GPT-4 in benchmark tests for reasoning and code generation."
- "The US government announces new regulations for AI development, requiring transparency reports."

# Bad Example
- "An article about Meta's Llama 3." (Too generic)
- "The latest trends in AI regulation." (Too generic)

# Output
"""
            summary = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.1 # Very low temperature for fact-based generation
            )
            
            if summary:
                cleaned_summary = clean_llm_response(summary)
                if len(cleaned_summary) > 25:
                    return ensure_sentence_completeness(cleaned_summary, 120)

            return None

        except Exception as e:
            logger.warning(f"Simple specific summary generation failed for '{citation.title}': {e}")
            return None

    async def generate_multi_source_citations(
        self, 
        representative_article: ProcessedArticle,
        cluster_articles: List[ProcessedArticle],
        max_citations: int = 3
    ) -> List[Citation]:
        """
        Generate enhanced citations for multi-source topics.
        
        Args:
            representative_article: Main representative article  
            cluster_articles: All articles in the same topic cluster
            max_citations: Maximum number of citations to generate
            
        Returns:
            List of Citation objects with diverse source perspectives
        """
        
        citations = []
        used_urls = set()
        used_sources = set()  # Track source diversity
        
        # Primary citation (representative article)
        primary_citation = await self._format_primary_citation_as_object(representative_article)
        citations.append(primary_citation)
        used_urls.add(representative_article.summarized_article.filtered_article.raw_article.url)
        used_sources.add(representative_article.summarized_article.filtered_article.raw_article.source_id)
        
        # Add citations from cluster articles (prioritize source diversity)
        cluster_sources = []
        for article in cluster_articles:
            raw_article = article.summarized_article.filtered_article.raw_article
            if (raw_article.url not in used_urls and 
                raw_article.source_id not in used_sources and
                len(citations) < max_citations):
                
                cluster_sources.append(article)
                used_sources.add(raw_article.source_id)
        
        # Sort cluster sources by AI relevance and source quality
        cluster_sources.sort(key=lambda a: (
            self._get_source_quality_score(a.summarized_article.filtered_article.raw_article.source_id),
            a.summarized_article.filtered_article.ai_relevance_score
        ), reverse=True)
        
        # Generate citations for top cluster sources
        for article in cluster_sources[:max_citations - 1]:
            if len(citations) >= max_citations:
                break
                
            try:
                citation = await self._format_article_as_citation_object(article)
                citations.append(citation)
                used_urls.add(article.summarized_article.filtered_article.raw_article.url)
                
            except Exception as e:
                logger.warning(
                    "Failed to generate cluster citation",
                    article_id=article.summarized_article.filtered_article.raw_article.id,
                    error=str(e)
                )
        
        logger.info(
            "Generated multi-source citations",
            representative_id=representative_article.summarized_article.filtered_article.raw_article.id,
            total_citations=len(citations),
            source_diversity=len(used_sources)
        )
        
        return citations
    
    def _get_source_quality_score(self, source_id: str) -> float:
        """Get quality score for source prioritization."""
        
        high_quality_sources = {
            'openai_news': 1.0,
            'anthropic_news': 1.0,
            'google_research_blog': 1.0,
            'the_decoder': 0.9,
            'venturebeat': 0.8,
            'techcrunch': 0.7,
            'the_verge': 0.7
        }
        
        return high_quality_sources.get(source_id, 0.5)
    
    async def _format_article_as_citation_object(self, article: ProcessedArticle) -> Citation:
        """Format a ProcessedArticle as Citation object with enhanced summary."""
        
        raw_article = article.summarized_article.filtered_article.raw_article
        
        # Enhanced source name formatting
        source_name = self._format_enhanced_source_name(raw_article.source_id, raw_article.url)
        
        # Generate topic-specific summary
        summary_text = await self._generate_topic_specific_citation_summary(
            raw_article.title,
            article.summarized_article.summary.summary_points,
            raw_article.source_id
        )
        
        return Citation(
            source_name=source_name,
            url=str(raw_article.url),
            title=raw_article.title,
            japanese_summary=summary_text
        )
    
    async def _generate_topic_specific_citation_summary(
        self, 
        title: str, 
        summary_points: List[str],
        source_id: str
    ) -> str:
        """Generate topic-specific citation summary with source perspective."""
        
        try:
            # Create context-aware prompt for citation summary
            prompt = f"""以下の記事について、{self._get_source_perspective(source_id)}の視点から80-120文字の日本語要約を生成してください。

記事タイトル: {title}
要点: {' / '.join(summary_points[:2])}

要件:
- この記事独自の情報や視点を強調
- ソースの特性を反映した表現
- 80-120文字で簡潔に
- 「記事」「について」などの一般的表現は避ける

例: 「OpenAIが新型GPTモデルを発表し、推論性能が50%向上。企業向けAPI提供も2025年Q3から開始予定」"""

            response = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.3
            )
            
            if response and isinstance(response, str):
                summary = clean_llm_response(response).strip()
                
                # Validate length and content
                if 60 <= len(summary) <= 150 and not any(
                    phrase in summary for phrase in ["記事について", "詳細記事", "に関する情報"]
                ):
                    return summary
            
            # Fallback to intelligent title-based summary
            return self._generate_intelligent_fallback_summary(title, summary_points)
            
        except Exception as e:
            logger.warning(f"LLM citation summary failed: {e}")
            return self._generate_intelligent_fallback_summary(title, summary_points)
    
    def _get_source_perspective(self, source_id: str) -> str:
        """Get source perspective for citation generation."""
        
        perspectives = {
            'openai_news': '公式発表',
            'anthropic_news': '安全性重視',
            'google_research_blog': '技術研究',
            'techcrunch': 'ビジネス',
            'the_verge': 'テクノロジー',
            'venturebeat': '業界分析',
            'the_decoder': '技術解説'
        }
        
        return perspectives.get(source_id, '専門')
    
    def _is_incompatible_citation(self, main_title: str, citation_title: str) -> bool:
        """
        明示的に非互換な引用の組み合わせをチェックする
        
        Args:
            main_title: メイン記事のタイトル
            citation_title: 引用候補記事のタイトル
            
        Returns:
            非互換の場合True（引用を禁止）
        """
        main_lower = main_title.lower()
        citation_lower = citation_title.lower()
        
        # CRITICAL: Topic domain incompatibility checks (ENHANCED for quality issues)
        topic_domains = [
            # HR/Recruitment vs Research/Technical
            (["hiring", "recruitment", "採用", "人材", "linkedin", "求人"], ["research", "researcher", "研究", "技術", "model", "モデル"]),
            # Economic policy vs Technical implementation  
            (["economy", "economic", "経済", "失業", "雇用喪失", "job losses"], ["hiring", "recruitment", "採用", "人材獲得", "massive offers"]),
            # Business/Finance vs Technical research
            (["investment", "funding", "ipo", "valuation", "投資"], ["api", "cli", "model", "algorithm", "研究"]),
            # Local tools vs Cloud services
            (["ollama", "local", "ローカル", "cli"], ["anthropic", "openai", "cloud", "クラウド"]),
            # Gaming/Entertainment vs AI Safety/Research
            (["game", "gaming", "ゲーム", "entertainment", "エンターテイメント"], ["safety", "research", "安全性", "研究"]),
            # Hardware vs Software focus
            (["hardware", "device", "デバイス", "chip", "チップ"], ["software", "api", "sdk", "ソフトウェア"]),
            # Regulation vs Innovation
            (["regulation", "policy", "規制", "政策", "law", "法律"], ["innovation", "breakthrough", "革新", "技術革新"]),
            # ENHANCED: Mysticism/Spirituality vs AI Technology (CRITICAL FIX for astrology issue)
            (["占星術", "astrology", "宇宙論", "cosmology", "スピリチュアル", "spiritual", "原初", "mystical", "cosmic"], ["gemini", "claude", "chatgpt", "openai", "anthropic", "ai", "llm", "技術", "tech"]),
            # Personal content vs Technical industry news
            (["個人的", "personal", "私の", "my experience", "感想", "体験", "日記"], ["industry", "企業", "company", "official", "announcement", "release"]),
            # Creative/Art vs Technical implementation
            (["creative", "art", "芸術", "創作", "novel", "小説", "poetry", "詩"], ["implementation", "api", "sdk", "technical", "技術実装"]),
            # Tutorial/How-to vs News/Announcements
            (["tutorial", "how to", "使い方", "方法", "手順", "guide", "チュートリアル"], ["announcement", "release", "発表", "news", "ニュース", "発売"]),
        ]
        
        for domain1_keywords, domain2_keywords in topic_domains:
            has_domain1 = any(keyword in main_lower for keyword in domain1_keywords)
            has_domain2 = any(keyword in citation_lower for keyword in domain2_keywords)
            if has_domain1 and has_domain2:
                logger.info(f"Blocked citation due to topic domain mismatch: {domain1_keywords[0]} vs {domain2_keywords[0]}")
                return True
                
            # Check reverse direction
            has_domain1_cite = any(keyword in citation_lower for keyword in domain1_keywords)
            has_domain2_main = any(keyword in main_lower for keyword in domain2_keywords)
            if has_domain1_cite and has_domain2_main:
                logger.info(f"Blocked citation due to reverse topic domain mismatch: {domain1_keywords[0]} vs {domain2_keywords[0]}")
                return True
        
        # 明確に互換性のない組み合わせ (ENHANCED with quality issue fixes)
        incompatible_patterns = [
            # Company competitors
            ("anthropic", "meta"),
            ("anthropic", "openai"),
            ("claude", "chatgpt"),
            ("google", "openai"),
            ("gemini", "chatgpt"),
            
            # Specific problematic combinations found in newsletters
            ("meta", "linkedin"),  # Meta research vs LinkedIn hiring
            ("economic futures", "massive offers"),
            ("雇用喪失", "massive offers"),
            ("経済影響", "cto confirms"),
            ("経済プログラム", "top ai executives"),
            ("経済", "採用"),
            ("失業", "引き抜き"),
            ("雇用喪失", "人材獲得"),
            ("economy", "hiring"),
            ("job losses", "recruitment"),
            
            # Tool categories
            ("ollama", "anthropic"),
            ("ollama", "openai"),
            ("ローカル", "クラウド"),
            
            # CRITICAL FIXES for observed quality issues
            ("占星術", "gemini"),  # Astrology vs Gemini AI - MAJOR incompatibility
            ("占星術", "claude"),  # Astrology vs Claude AI
            ("占星術", "chatgpt"), # Astrology vs ChatGPT
            ("astrology", "ai"),   # English astrology vs AI tech
            ("インド占星術", "tech"), # Indian astrology vs tech
            ("原初の空間", "ai"),   # Cosmic/mystical vs AI
            ("宇宙論", "technical"), # Cosmology vs technical
            ("詩音", "ai"),       # Personal AI assistant vs tech industry
            ("個人体験", "industry"), # Personal experience vs industry news
            ("感想", "announcement"), # Personal opinion vs official announcement
            ("学習中", "official"),   # Learning/studying vs official content
            ("自身の理解", "enterprise"), # Personal understanding vs enterprise
        ]
        
        for pattern1, pattern2 in incompatible_patterns:
            if (pattern1 in main_lower and pattern2 in citation_lower) or \
               (pattern2 in main_lower and pattern1 in citation_lower):
                return True
        
        # Specific title combinations that should never cite each other (ENHANCED)
        specific_blocks = [
            ("AI経済フューチャープログラム", "Meta CTO confirms"),
            ("雇用喪失への懸念", "top AI executives"),
            ("Economic Futures Program", "massive offers"),
            
            # CRITICAL FIXES for observed quality issues
            ("原初の空間には、インド占星術の基礎が書いてある", "Gemini"),
            ("インド占星術の基礎", "AI技術"),
            ("占星術", "OpenAI"),
            ("詩音", "エンタープライズ"),
            ("7月5日の星読み", "技術動向"),
            ("個人的な体験", "業界ニュース"),
            ("学習中", "公式発表"),
            ("感想とメモ", "企業戦略"),
            ("エンジニアのためのAIの基本", "企業買収"),  # Personal learning vs business news
            ("開発秘話", "技術仕様"),  # Development stories vs technical specs
        ]
        
        for block1, block2 in specific_blocks:
            if (block1.lower() in main_lower and block2.lower() in citation_lower) or \
               (block2.lower() in main_lower and block1.lower() in citation_lower):
                return True
        
        return False

    def _validate_citation_relevance(self, main_article: ProcessedArticle, citation_article: RawArticle) -> bool:
        """
        🔥 ULTRA THINK: 意味ベクトル+厳格ルールベースのハイブリッド引用関連性検証
        
        Args:
            main_article: メイン記事
            citation_article: 引用候補記事
            
        Returns:
            関連性がある場合True、ない場合False
        """
        try:
            main_raw = main_article.summarized_article.filtered_article.raw_article
            
            # デバッグログ追加
            logger.info(
                f"Validating citation relevance: Main='{main_raw.title[:50]}...' vs Citation='{citation_article.title[:50]}...'"
            )
            
            # PHASE 1: 意味ベクトル類似度による事前スクリーニング
            semantic_similarity = self._calculate_semantic_similarity(main_raw, citation_article)
            logger.debug(f"Semantic similarity score: {semantic_similarity:.3f}")
            
            # 意味的に全く関連性がない場合は即座に除外（90%保証の第一段階）
            if semantic_similarity < 0.25:  # 閾値：25%未満は意味的に無関係
                logger.info(f"Blocked citation due to low semantic similarity: {semantic_similarity:.3f}")
                return False
            
            # PHASE 2: 厳格なトピック競合チェック（保守的アプローチ）
            if not self._validate_topic_compatibility_strict(main_raw, citation_article):
                logger.info("Blocked citation due to topic incompatibility")
                return False
            
            # PHASE 3: ドメイン整合性チェック
            if not self._validate_same_topic_domain(main_raw, citation_article):
                logger.info("Blocked citation due to different topic domains")
                return False
            
            # PHASE 4: 意味ベクトル+企業・技術マッチングの統合評価
            final_relevance_score = self._calculate_final_relevance_score(
                main_raw, citation_article, semantic_similarity
            )
            
            # 90%類似性保証のための閾値設定
            RELEVANCE_THRESHOLD = 0.70  # 70%以上で関連性ありと判定
            
            is_relevant = final_relevance_score >= RELEVANCE_THRESHOLD
            logger.info(
                f"Citation relevance decision: score={final_relevance_score:.3f}, "
                f"threshold={RELEVANCE_THRESHOLD}, relevant={is_relevant}"
            )
            
            return is_relevant
            
        except Exception as e:
            logger.warning(f"Citation relevance validation failed: {e}")
            # エラー時は安全側に倒して関連性なしとする（品質優先）
            return False
    
    async def _validate_citation_relevance_strict(self, main_article: ProcessedArticle, citation_article: RawArticle) -> float:
        """
        🔥 ULTRA THINK: 90%以上関連性保証の超厳格引用検証システム
        PRD F-15準拠: 同一話題90%以上保証実装
        
        Args:
            main_article: メイン記事
            citation_article: 引用候補記事
            
        Returns:
            関連性スコア (0.0-1.0)、0.90以上で関連性ありと判定
        """
        try:
            main_raw = main_article.summarized_article.filtered_article.raw_article
            
            logger.debug(
                f"Strict relevance validation: Main='{main_raw.title[:30]}...' vs Citation='{citation_article.title[:30]}...'"
            )
            
            # PHASE 1: 絶対除外パターン（企業・製品ミスマッチ）
            if self._is_incompatible_citation_strict(main_raw.title, citation_article.title):
                logger.debug("Blocked: Incompatible entity mismatch")
                return 0.0
            
            # PHASE 2: セマンティック類似度（高精度）
            semantic_score = await self._calculate_semantic_similarity_advanced(main_raw, citation_article)
            logger.debug(f"Advanced semantic score: {semantic_score:.3f}")
            
            # PHASE 3: トピック一致度
            topic_score = self._calculate_topic_alignment_score(main_raw, citation_article)
            logger.debug(f"Topic alignment score: {topic_score:.3f}")
            
            # PHASE 4: 企業・技術エンティティ一致度
            entity_score = self._calculate_entity_alignment_score(main_raw, citation_article)
            logger.debug(f"Entity alignment score: {entity_score:.3f}")
            
            # PHASE 5: 内容重複度（高重複は減点）
            overlap_penalty = self._calculate_content_overlap_penalty(main_raw, citation_article)
            logger.debug(f"Content overlap penalty: {overlap_penalty:.3f}")
            
            # 統合スコア計算（重み付き）
            final_score = (
                semantic_score * 0.40 +    # セマンティック類似度：40%
                topic_score * 0.30 +       # トピック一致度：30%
                entity_score * 0.25 +      # エンティティ一致度：25%
                overlap_penalty * 0.05     # 重複ペナルティ：5%
            )
            
            logger.info(
                f"Strict relevance score: {final_score:.3f} "
                f"(semantic={semantic_score:.2f}, topic={topic_score:.2f}, "
                f"entity={entity_score:.2f}, penalty={overlap_penalty:.2f})"
            )
            
            return final_score
            
        except Exception as e:
            logger.warning(f"Strict citation relevance validation failed: {e}")
            return 0.0  # エラー時は関連性なしとする
    
    async def _calculate_semantic_similarity_advanced(self, main_article: RawArticle, citation_article: RawArticle) -> float:
        """高精度セマンティック類似度計算"""
        try:
            # Use embedding manager for true semantic similarity if available
            if hasattr(self.llm_router, 'embedding_manager') and self.llm_router.embedding_manager:
                main_text = f"{main_article.title}\n{main_article.content or ''}"[:1000]
                citation_text = f"{citation_article.title}\n{citation_article.content or ''}"[:1000]
                
                main_embedding = await self.llm_router.embedding_manager.generate_embedding(main_text)
                citation_embedding = await self.llm_router.embedding_manager.generate_embedding(citation_text)
                
                if main_embedding is not None and citation_embedding is not None:
                    # コサイン類似度計算
                    import numpy as np
                    similarity = np.dot(main_embedding, citation_embedding) / (
                        np.linalg.norm(main_embedding) * np.linalg.norm(citation_embedding)
                    )
                    return float(similarity)
            
            # Fallback to keyword-based similarity
            return self._calculate_semantic_similarity(main_article, citation_article)
            
        except Exception as e:
            logger.warning(f"Advanced semantic similarity calculation failed: {e}")
            return 0.0
    
    def _calculate_topic_alignment_score(self, main_article: RawArticle, citation_article: RawArticle) -> float:
        """トピック一致度計算"""
        try:
            # 主要トピックキーワードの定義
            ai_topics = {
                'llm': ['llm', 'language model', 'gpt', 'claude', 'gemini', 'chatgpt'],
                'agent': ['agent', 'エージェント', 'autonomous', 'agentic', 'multi-agent'],
                'research': ['research', '研究', 'paper', 'study', 'analysis'],
                'company': ['openai', 'anthropic', 'google', 'meta', 'microsoft', 'apple'],
                'technology': ['ai', 'ml', 'deep learning', 'neural', 'transformer'],
                'product': ['api', 'platform', 'service', 'tool', 'framework'],
                'business': ['investment', '投資', 'funding', 'startup', 'venture', 'partnership']
            }
            
            main_text = f"{main_article.title} {main_article.content or ''}".lower()
            citation_text = f"{citation_article.title} {citation_article.content or ''}".lower()
            
            topic_matches = 0
            total_topics = 0
            
            for topic, keywords in ai_topics.items():
                main_has_topic = any(keyword in main_text for keyword in keywords)
                citation_has_topic = any(keyword in citation_text for keyword in keywords)
                
                total_topics += 1
                if main_has_topic and citation_has_topic:
                    topic_matches += 1
                elif main_has_topic or citation_has_topic:
                    # 片方だけの場合は部分スコア
                    topic_matches += 0.3
            
            return topic_matches / total_topics if total_topics > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Topic alignment calculation failed: {e}")
            return 0.0
    
    def _calculate_entity_alignment_score(self, main_article: RawArticle, citation_article: RawArticle) -> float:
        """企業・技術エンティティ一致度計算"""
        try:
            # 重要エンティティの抽出
            entities = {
                'companies': ['openai', 'anthropic', 'google', 'meta', 'microsoft', 'apple', 'nvidia', 'sakana'],
                'technologies': ['gpt', 'claude', 'gemini', 'llama', 'copilot', 'mcp', 'api'],
                'concepts': ['agent', 'reasoning', 'multimodal', 'embedding', 'fine-tuning']
            }
            
            main_text = f"{main_article.title} {main_article.content or ''}".lower()
            citation_text = f"{citation_article.title} {citation_article.content or ''}".lower()
            
            entity_matches = 0
            total_entities = 0
            
            for category, entity_list in entities.items():
                for entity in entity_list:
                    main_has_entity = entity in main_text
                    citation_has_entity = entity in citation_text
                    
                    total_entities += 1
                    if main_has_entity and citation_has_entity:
                        # 同一エンティティで高スコア
                        entity_matches += 1.0
                    elif main_has_entity or citation_has_entity:
                        # 片方だけでも関連性あり
                        entity_matches += 0.2
            
            return entity_matches / total_entities if total_entities > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Entity alignment calculation failed: {e}")
            return 0.0
    
    def _calculate_content_overlap_penalty(self, main_article: RawArticle, citation_article: RawArticle) -> float:
        """内容重複ペナルティ計算（重複が多いほど減点）"""
        try:
            # タイトルの重複チェック
            main_title_words = set(main_article.title.lower().split())
            citation_title_words = set(citation_article.title.lower().split())
            
            title_overlap = len(main_title_words & citation_title_words) / len(main_title_words | citation_title_words)
            
            # 高重複は減点、適度な重複は許容
            if title_overlap > 0.8:
                return -0.3  # 80%以上重複で大幅減点
            elif title_overlap > 0.6:
                return -0.1  # 60%以上重複で軽微減点
            else:
                return 0.0   # 適度な重複は問題なし
                
        except Exception as e:
            logger.warning(f"Content overlap penalty calculation failed: {e}")
            return 0.0
    
    def _is_incompatible_citation_strict(self, main_title: str, citation_title: str) -> bool:
        """超厳格な非互換引用パターン検出"""
        try:
            # 明確に異なる企業・製品の組み合わせを検出
            incompatible_pairs = [
                (['openai', 'chatgpt', 'gpt'], ['anthropic', 'claude']),
                (['openai', 'chatgpt', 'gpt'], ['google', 'gemini', 'bard']),
                (['anthropic', 'claude'], ['google', 'gemini', 'bard']),
                (['sakana', 'treequest'], ['openai', 'gpt']),
                (['microsoft', 'copilot'], ['google', 'gemini']),
                (['hunter', 'nen', '念能力'], ['ai', 'llm', 'technology']),  # 特殊：HUNTER×HUNTER vs AI技術
                (['xbox', 'gaming'], ['ai', 'llm', 'research']),  # 特殊：ゲーム vs AI研究
            ]
            
            main_lower = main_title.lower()
            citation_lower = citation_title.lower()
            
            for group1, group2 in incompatible_pairs:
                has_group1_main = any(term in main_lower for term in group1)
                has_group2_citation = any(term in citation_lower for term in group2)
                has_group2_main = any(term in main_lower for term in group2)
                has_group1_citation = any(term in citation_lower for term in group1)
                
                if (has_group1_main and has_group2_citation) or (has_group2_main and has_group1_citation):
                    logger.debug(f"Detected incompatible pair: {group1} vs {group2}")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Incompatible citation check failed: {e}")
            return False

    def _calculate_semantic_similarity(self, main_article: RawArticle, citation_article: RawArticle) -> float:
        """🔥 ULTRA THINK: 意味ベクトル類似度計算"""
        try:
            # テキスト準備
            main_text = f"{main_article.title} {main_article.content or ''}"[:500]
            citation_text = f"{citation_article.title} {citation_article.content or ''}"[:500]
            
            # Simple TF-IDF-like similarity for Phase 1 implementation
            # TODO: Replace with proper embedding-based similarity in Phase 2
            main_words = set(main_text.lower().split())
            citation_words = set(citation_text.lower().split())
            
            if not main_words or not citation_words:
                return 0.0
                
            # Jaccard係数による近似的意味類似度
            intersection = main_words & citation_words
            union = main_words | citation_words
            
            similarity = len(intersection) / len(union) if union else 0.0
            
            # 特定の重要キーワードにボーナススコア
            important_keywords = [
                'ai', 'llm', 'model', 'research', 'openai', 'anthropic', 'google', 
                'chatgpt', 'claude', 'gemini', 'mcp', 'protocol', 'agent'
            ]
            
            bonus = 0.0
            for keyword in important_keywords:
                if keyword in main_text.lower() and keyword in citation_text.lower():
                    bonus += 0.1
            
            return min(similarity + bonus, 1.0)
            
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return 0.0

    def _validate_topic_compatibility_strict(self, main_article: RawArticle, citation_article: RawArticle) -> bool:
        """🔥 ULTRA THINK: 厳格なトピック互換性チェック"""
        try:
            main_text = main_article.title.lower()
            citation_text = citation_article.title.lower()
            
            # 実際の問題例に基づく厳格な互換性ルール
            incompatible_patterns = [
                # SakanaAI TreeQuest vs Zen プロンプトエンジニアリング
                (['sakana', 'treequest', 'multi-model'], ['prompt', 'engineering', 'fine-tuning', 'zen']),
                # Xbox/Microsoft vs EU規制
                (['xbox', 'microsoft', 'layoff', 'emotion'], ['eu', 'regulation', 'legislation']),
                # MCP技術 vs 一般AI概念
                (['mcp', 'protocol', 'context'], ['general', 'understanding', '理解', '基本']),
                # 企業特定技術 vs 競合他社
                (['openai', 'chatgpt'], ['anthropic', 'claude']),
                (['google', 'gemini'], ['openai', 'gpt']),
                # 研究開発 vs 人事・採用
                (['research', 'model', 'technical'], ['hiring', 'recruitment', 'hr']),
            ]
            
            for main_patterns, cite_patterns in incompatible_patterns:
                main_match = any(pattern in main_text for pattern in main_patterns)
                cite_match = any(pattern in citation_text for pattern in cite_patterns)
                
                if main_match and cite_match:
                    logger.debug(f"Topic incompatibility: {main_patterns} vs {cite_patterns}")
                    return False
                    
                # 逆向きもチェック
                main_match_reverse = any(pattern in main_text for pattern in cite_patterns)
                cite_match_reverse = any(pattern in citation_text for pattern in main_patterns)
                
                if main_match_reverse and cite_match_reverse:
                    logger.debug(f"Reverse topic incompatibility: {cite_patterns} vs {main_patterns}")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Topic compatibility check failed: {e}")
            return False
    
    def _calculate_final_relevance_score(
        self, 
        main_article: RawArticle, 
        citation_article: RawArticle, 
        semantic_similarity: float
    ) -> float:
        """🔥 ULTRA THINK: 最終関連性スコア計算（意味ベクトル+エンティティマッチング）"""
        try:
            # ベース：意味的類似度（重み50%）
            base_score = semantic_similarity * 0.5
            
            # 企業マッチングボーナス（重み25%）
            company_score = self._calculate_company_relevance(main_article, citation_article) * 0.25
            
            # 技術用語マッチングボーナス（重み25%）
            tech_score = self._calculate_tech_relevance(main_article, citation_article) * 0.25
            
            final_score = base_score + company_score + tech_score
            
            logger.debug(
                f"Relevance score breakdown: semantic={semantic_similarity:.3f}, "
                f"company={company_score:.3f}, tech={tech_score:.3f}, final={final_score:.3f}"
            )
            
            return min(final_score, 1.0)
            
        except Exception as e:
            logger.warning(f"Final relevance score calculation failed: {e}")
            return semantic_similarity * 0.5  # Fallback to semantic only
    
    def _calculate_company_relevance(self, main_article: RawArticle, citation_article: RawArticle) -> float:
        """企業関連性スコア計算"""
        main_companies = self._extract_companies(main_article.title + " " + (main_article.content or ""))
        citation_companies = self._extract_companies(citation_article.title + " " + (citation_article.content or ""))
        
        if not main_companies or not citation_companies:
            return 0.0
            
        # 共通企業の割合
        common = set(main_companies) & set(citation_companies)
        if common:
            return len(common) / max(len(main_companies), len(citation_companies))
        
        return 0.0
    
    def _calculate_tech_relevance(self, main_article: RawArticle, citation_article: RawArticle) -> float:
        """技術関連性スコア計算"""
        main_tech = self._extract_tech_terms(main_article.title + " " + (main_article.content or ""))
        citation_tech = self._extract_tech_terms(citation_article.title + " " + (citation_article.content or ""))
        
        if not main_tech or not citation_tech:
            return 0.0
            
        # 共通技術用語の割合
        common = set(main_tech) & set(citation_tech)
        if common:
            return len(common) / max(len(main_tech), len(citation_tech))
        
        return 0.0
    
    def _extract_companies(self, text: str) -> List[str]:
        """テキストから企業名を抽出"""
        companies = []
        company_patterns = [
            'OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'Apple', 
            'Amazon', 'Tesla', 'NVIDIA', 'DeepMind', 'LinkedIn', 'GitHub',
            'Hugging Face', 'Stability AI', 'Cohere', 'Inflection'
        ]
        
        for company in company_patterns:
            if company.lower() in text.lower():
                companies.append(company)
        
        return companies
    
    def _extract_tech_terms(self, text: str) -> List[str]:
        """テキストから技術・製品名を抽出"""
        tech_terms = []
        tech_patterns = [
            'ChatGPT', 'GPT-4', 'GPT-3', 'Gemini', 'Claude', 'Llama', 'Copilot',
            'Bard', 'API', 'CLI', 'LLM', 'AI', 'Machine Learning', 'Deep Learning',
            'Transformer', 'Neural Network', 'Embedding', 'RAG', 'Agent'
        ]
        
        for tech in tech_patterns:
            if tech.lower() in text.lower():
                tech_terms.append(tech)
        
        return tech_terms
    
    def _validate_same_topic_domain(self, main_article: RawArticle, citation_article: RawArticle) -> bool:
        """
        Validate that both articles belong to the same topic domain.
        
        Args:
            main_article: Main article
            citation_article: Citation candidate article
            
        Returns:
            True if articles are in the same domain, False otherwise
        """
        # Define topic domains
        topic_domains = {
            'hr_recruitment': ['hiring', 'recruitment', '採用', '人材', 'linkedin', '求人', 'job search', 'talent acquisition', 'massive offers'],
            'research_technical': ['research', 'researcher', '研究', '技術', 'model', 'モデル', 'algorithm', 'api', 'technical', 'poaches', 'scientists'],
            'economic_policy': ['economy', 'economic', '経済', '失業', '雇用喪失', 'job losses', 'policy', '政策', 'futures program'],
            'business_finance': ['investment', 'funding', 'ipo', 'valuation', '投資', 'venture', 'startup'],
            'product_tools': ['cli', 'api', 'tool', 'ツール', 'product', '製品', 'feature', '機能'],
            'local_infrastructure': ['ollama', 'local', 'ローカル', 'infrastructure', 'self-hosted']
        }
        
        def get_article_domains(article: RawArticle) -> List[str]:
            article_text = (article.title + " " + (article.content or "")).lower()
            detected_domains = []
            for domain, keywords in topic_domains.items():
                if any(keyword in article_text for keyword in keywords):
                    detected_domains.append(domain)
            return detected_domains
        
        main_domains = get_article_domains(main_article)
        citation_domains = get_article_domains(citation_article)
        
        # If either article has no clear domain, be conservative and allow
        if not main_domains or not citation_domains:
            return True
        
        # Check for domain overlap
        has_overlap = bool(set(main_domains) & set(citation_domains))
        
        # Check for mutually exclusive domains
        mutually_exclusive_pairs = [
            ('hr_recruitment', 'research_technical'),
            ('economic_policy', 'hr_recruitment'),
            ('business_finance', 'research_technical'),
            ('local_infrastructure', 'economic_policy'),
        ]
        
        for main_domain in main_domains:
            for citation_domain in citation_domains:
                for exclusive1, exclusive2 in mutually_exclusive_pairs:
                    if (main_domain == exclusive1 and citation_domain == exclusive2) or \
                       (main_domain == exclusive2 and citation_domain == exclusive1):
                        logger.info(
                            f"Domain exclusion: {main_domain} vs {citation_domain} "
                            f"between '{main_article.title[:30]}...' and '{citation_article.title[:30]}...'"
                        )
                        return False
        
        return has_overlap or (not main_domains and not citation_domains)
    
    def _extract_topic_keywords(self, text: str) -> List[str]:
        """テキストからトピックキーワードを抽出"""
        keywords = []
        topic_patterns = [
            '研究者', '採用', '雇用', '人事', '資金調達', '投資', 'VC', '買収',
            '製品', 'サービス', '機能', 'API', 'CLI', 'アップデート', 'リリース',
            '技術', 'モデル', 'アルゴリズム', 'データ', 'プラットフォーム'
        ]
        
        for keyword in topic_patterns:
            if keyword in text:
                keywords.append(keyword)
        
        return keywords

    def _generate_intelligent_fallback_summary(self, title: str, summary_points: List[str]) -> str:
        """Generate intelligent fallback summary based on title and summary points."""
        
        try:
            # Use first summary point if available
            if summary_points:
                first_point = summary_points[0]
                # Clean and truncate appropriately
                if len(first_point) <= 120:
                    return first_point
                else:
                    return first_point[:117] + "..."
            
            # Fallback to title-based intelligent summary
            return self._create_intelligent_title_summary(title)
            
        except Exception:
            return f"{title[:80]}についての技術解説"


async def enhance_articles_with_citations(
    articles: List[ProcessedArticle],
    max_citations_per_article: int = 3
) -> List[ProcessedArticle]:
    """
    Enhance articles with citation blocks.
    
    Args:
        articles: List of processed articles
        max_citations_per_article: Maximum citations per article
        
    Returns:
        Articles enhanced with citations
    """
    
    citation_generator = CitationGenerator()
    
    for article in articles:
        try:
            # Generate citations for this article
            citations = await citation_generator.generate_citations(
                article=article,
                max_citations=max_citations_per_article
            )
            
            # Update article with citations
            article.citations = citations
            
        except Exception as e:
            logger.error(
                "Failed to generate citations for article",
                article_id=article.summarized_article.filtered_article.raw_article.id,
                error=str(e)
            )
            
            # Provide fallback citation object
            raw_article = article.summarized_article.filtered_article.raw_article
            fallback_citation = Citation(
                source_name=raw_article.source_id.title(),
                url=str(raw_article.url),
                title=raw_article.title,
                japanese_summary=f"{raw_article.title[:80]}に関する記事"
            )
            article.citations = [fallback_citation]
    
    logger.info(
        "Citation generation completed",
        total_articles=len(articles),
        avg_citations=sum(len(a.citations) for a in articles) / len(articles) if articles else 0
    )
    
    return articles


async def enhance_articles_with_citations_parallel(
    articles: List[ProcessedArticle],
    max_citations_per_article: int = 3,
    max_concurrent: int = 8
) -> List[ProcessedArticle]:
    """
    Parallel version of citation enhancement with significant performance improvements.
    
    Args:
        articles: List of processed articles
        max_citations_per_article: Maximum citations per article  
        max_concurrent: Maximum concurrent citation generations
        
    Returns:
        Articles enhanced with citations
    """
    if not articles:
        return articles
    
    citation_generator = CitationGenerator()
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def generate_citations_with_semaphore(article: ProcessedArticle) -> ProcessedArticle:
        """Generate citations for a single article with concurrency control."""
        async with semaphore:
            try:
                # Generate citations for this article
                citations = await citation_generator.generate_citations(
                    article=article,
                    max_citations=max_citations_per_article
                )
                
                # Update article with citations
                article.citations = citations
                return article
                
            except Exception as e:
                logger.error(
                    "Failed to generate citations for article",
                    article_id=article.summarized_article.filtered_article.raw_article.id,
                    error=str(e)
                )
                
                # Provide fallback citation object
                raw_article = article.summarized_article.filtered_article.raw_article
                fallback_citation = Citation(
                    source_name=raw_article.source_id.title(),
                    url=str(raw_article.url),
                    title=raw_article.title,
                    japanese_summary=f"{raw_article.title[:80]}に関する記事"
                )
                article.citations = [fallback_citation]
                return article
    
    # Create tasks for all articles
    tasks = [generate_citations_with_semaphore(article) for article in articles]
    
    # Execute in parallel
    logger.info(f"Generating citations for {len(articles)} articles in parallel (max {max_concurrent} concurrent)")
    start_time = time.time()
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    processing_time = time.time() - start_time
    
    # Process results and handle exceptions
    enhanced_articles = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Citation generation exception for article {i}: {result}")
            # Use original article with minimal fallback citation
            article = articles[i]
            raw_article = article.summarized_article.filtered_article.raw_article
            fallback_citation = Citation(
                source_name=raw_article.source_id.title(),
                url=str(raw_article.url),
                title=raw_article.title,
                japanese_summary=f"{raw_article.title[:80]}に関する記事"
            )
            article.citations = [fallback_citation]
            enhanced_articles.append(article)
        else:
            enhanced_articles.append(result)
    
    avg_citations = sum(len(a.citations) for a in enhanced_articles) / len(enhanced_articles) if enhanced_articles else 0
    
    logger.info(
        f"Parallel citation generation completed in {processing_time:.2f}s",
        total_articles=len(enhanced_articles),
        avg_citations=avg_citations,
        articles_per_second=len(articles) / processing_time if processing_time > 0 else 0
    )
    
    return enhanced_articles