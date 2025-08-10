"""
Context analysis system for article relationships.

This module implements the contextual analysis that determines whether
articles are duplicates, updates, or independent content.
"""

import json
from pathlib import Path
from typing import Union

import yaml

from src.llm.llm_router import LLMRouter
from src.models.schemas import ContextAnalysisResult, RelatedArticleReference, SummarizedArticle
from src.utils.embedding_manager import EmbeddingManager
from src.utils.logger import setup_logging

logger = setup_logging()


class ContextAnalyzer:
    """Analyzes contextual relationships between articles."""

    def __init__(
        self,
        embedding_manager: Union[EmbeddingManager, None] = None,
        llm_router: Union[LLMRouter, None] = None,
        prompts_dir: str = "src/prompts"
    ):
        """
        Initialize context analyzer.

        Args:
            embedding_manager: Embedding manager for similarity search
            llm_router: LLM router for context analysis
            prompts_dir: Directory containing prompt templates
        """
        self.embedding_manager = embedding_manager
        self.llm_router = llm_router or LLMRouter()
        self.prompts_dir = Path(prompts_dir)

        # Load prompts
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        """Load context analysis prompts from YAML."""

        try:
            prompts_file = self.prompts_dir / "context_analysis.yaml"

            if not prompts_file.exists():
                logger.warning(f"Prompts file not found: {prompts_file}")
                return self._get_default_prompts()

            with open(prompts_file, encoding='utf-8') as f:
                prompts = yaml.safe_load(f)

            logger.debug("Loaded context analysis prompts")
            return prompts

        except Exception as e:
            logger.error("Failed to load prompts", error=str(e))
            return self._get_default_prompts()

    def _get_default_prompts(self) -> dict:
        """Get default prompts if file loading fails."""

        return {
            "context_analysis_prompt": """
            今回のニュース: {current_title}
            過去の類似ニュース: {past_related_news}

            判定してください:
            - SKIP: 重複
            - UPDATE: 続報
            - KEEP: 独立記事

            JSON形式で回答:
            {"decision": "SKIP|UPDATE|KEEP", "reasoning": "理由", "confidence_score": 0.85}
            """,
            "system_prompt": "あなたはAIニュース記事の文脈分析専門家です。"
        }

    async def analyze_context(
        self,
        current_article: SummarizedArticle,
        max_similar_articles: int = 5,
        similarity_threshold: float = 0.7
    ) -> ContextAnalysisResult:
        """
        Analyze context of current article against past articles.

        Args:
            current_article: Article to analyze
            max_similar_articles: Maximum similar articles to consider
            similarity_threshold: Minimum similarity for comparison

        Returns:
            ContextAnalysisResult with decision and reasoning
        """

        try:
            article_id = current_article.filtered_article.raw_article.id
            article_title = current_article.filtered_article.raw_article.title

            logger.info(
                "Starting context analysis",
                article_id=article_id,
                article_title=article_title[:50] + "..." if len(article_title) > 50 else article_title,
                similarity_threshold=similarity_threshold,
                max_similar_articles=max_similar_articles
            )

            # Find similar past articles
            similar_articles = []

            if self.embedding_manager:
                similar_articles = await self.embedding_manager.search_similar_articles(
                    query_article=current_article,
                    top_k=max_similar_articles,
                    similarity_threshold=similarity_threshold
                )

                logger.info(
                    "Similar articles search completed",
                    article_id=article_id,
                    found_count=len(similar_articles),
                    similarity_scores=[round(a["similarity_score"], 3) for a in similar_articles[:3]]
                )
            else:
                logger.warning("Embedding manager not available for context analysis", article_id=article_id)

            if not similar_articles:
                # No similar articles found - treat as independent
                return ContextAnalysisResult(
                    decision="KEEP",
                    reasoning="過去に類似記事が見つからないため、独立した新しい記事として判定",
                    contextual_summary=None,
                    references=[],
                    similarity_score=0.0
                )

            # Analyze relationship using LLM
            analysis_result = await self._llm_context_analysis(
                current_article, similar_articles
            )

            logger.info(
                "Context analysis completed",
                article_id=current_article.filtered_article.raw_article.id,
                decision=analysis_result.decision,
                similar_articles_count=len(similar_articles),
                max_similarity=similar_articles[0]["similarity_score"] if similar_articles else 0
            )

            return analysis_result

        except Exception as e:
            logger.error(
                "Context analysis failed",
                article_id=current_article.filtered_article.raw_article.id,
                error=str(e)
            )

            # Fallback to KEEP decision
            return ContextAnalysisResult(
                decision="KEEP",
                reasoning=f"文脈分析エラーのため独立記事として処理: {str(e)}",
                contextual_summary=None,
                references=[],
                similarity_score=0.0
            )

    async def _llm_context_analysis(
        self,
        current_article: SummarizedArticle,
        similar_articles: list[dict]
    ) -> ContextAnalysisResult:
        """Use LLM to analyze article relationships."""

        try:
            raw_article = current_article.filtered_article.raw_article
            article_id = raw_article.id

            logger.info(
                "Starting LLM context analysis",
                article_id=article_id,
                similar_articles_count=len(similar_articles),
                max_similarity=similar_articles[0]["similarity_score"] if similar_articles else 0
            )

            # Prepare current article info
            current_info = {
                "title": raw_article.title,
                "content": raw_article.content[:1000],  # Limit for prompt
                "summary": " ".join(current_article.summary.summary_points),
                "date": raw_article.published_date.strftime("%Y-%m-%d")
            }

            # Prepare similar articles info
            past_news_text = ""
            reference_objects = []

            for i, article in enumerate(similar_articles):
                past_news_text += f"\n{i+1}. **{article['title']}**\n"
                past_news_text += f"   日付: {article['published_date'][:10]}\n"
                past_news_text += f"   類似度: {article['similarity_score']:.3f}\n"
                past_news_text += f"   要約: {article['content_summary'][:200]}...\n"

                # Create RelatedArticleReference object with full metadata
                from datetime import datetime

                # Try multiple URL field names to ensure we get a valid URL
                url = (article.get('source_url') or
                       article.get('url') or
                       article.get('link') or
                       article.get('source', {}).get('url') or
                       '')

                # Handle datetime parsing safely
                try:
                    if isinstance(article['published_date'], str):
                        pub_date = datetime.fromisoformat(article['published_date'].replace('Z', '+00:00'))
                    else:
                        pub_date = article['published_date']
                except (ValueError, KeyError):
                    pub_date = datetime.now()

                # Generate Japanese title if available
                japanese_title = article.get('japanese_title')
                if not japanese_title and await self._needs_translation(article['title']):
                    japanese_title = await self._generate_simple_japanese_title(article['title'])

                # Ensure URL is not empty
                if not url or url == '' or url == 'None':
                    # Try to construct specific URL from article metadata first
                    article_title_slug = self._generate_url_slug(article['title'])
                    source_id = article.get('source_id', 'unknown').lower()

                    if 'techcrunch' in source_id:
                        # Try to create a more specific TechCrunch search URL
                        url = f"https://techcrunch.com/search/{article['article_id']}"
                    elif 'zenn' in source_id:
                        # Try to create more specific Zenn URLs based on content
                        if article_title_slug:
                            url = f"https://zenn.dev/search?q={article_title_slug[:50]}"
                        else:
                            url = "https://zenn.dev/topics/ai"
                    elif 'github' in source_id:
                        url = f"https://github.com/search?q={article_title_slug[:50]}&type=repositories"
                    elif 'youtube' in source_id:
                        url = f"https://www.youtube.com/results?search_query={article_title_slug[:50]}"
                    elif 'reddit' in source_id:
                        url = f"https://www.reddit.com/search/?q={article_title_slug[:50]}"
                    else:
                        # More descriptive anchor fallback
                        url = f"#{article['article_id']}"

                ref_obj = RelatedArticleReference(
                    article_id=article['article_id'],
                    title=article['title'],
                    japanese_title=japanese_title,
                    url=url,
                    published_date=pub_date,
                    similarity_score=article['similarity_score']
                )
                reference_objects.append(ref_obj)

            # Create analysis prompt
            prompt = self.prompts["context_analysis_prompt"].format(
                current_title=current_info["title"],
                current_content=current_info["content"],
                current_summary=current_info["summary"],
                current_date=current_info["date"],
                past_related_news=past_news_text
            )

            logger.debug(
                "Context analysis prompt prepared",
                article_id=article_id,
                prompt_length=len(prompt),
                similar_articles_in_prompt=len(similar_articles)
            )

            # Use LLM router for analysis
            system_prompt = self.prompts.get("system_prompt", "")

            # Create a temporary summary output structure for LLM router
            # We'll parse the JSON response manually
            try:
                response = await self._call_llm_for_context_analysis(
                    system_prompt, prompt
                )

                logger.info(
                    "LLM context analysis response received",
                    article_id=article_id,
                    response_length=len(response) if response else 0
                )

                # Parse LLM response
                analysis_data = self._parse_llm_response(response)

                # CRITICAL: Validate SKIP decisions to prevent over-filtering
                # PRD F-5 requires 10 articles, so SKIP must be extremely conservative
                max_similarity = similar_articles[0]["similarity_score"] if similar_articles else 0.0
                decision = analysis_data.get("decision", "KEEP")

                # Override inappropriate SKIP decisions
                if decision == "SKIP" and max_similarity < 0.998:  # 99.8% threshold per prompt
                    # If LLM says SKIP but similarity < 99.8%, override to UPDATE or KEEP
                    if max_similarity > 0.75:
                        decision = "UPDATE"
                        analysis_data["reasoning"] = f"LLMのSKIP判定を修正：類似度{max_similarity:.3f}では続報として処理が適切"
                        logger.info(
                            "Overrode inappropriate SKIP decision to UPDATE",
                            article_id=article_id,
                            similarity=max_similarity,
                            original_reasoning=analysis_data.get("reasoning", "")
                        )
                    else:
                        decision = "KEEP"
                        analysis_data["reasoning"] = f"LLMのSKIP判定を修正：類似度{max_similarity:.3f}では独立記事として処理が適切"
                        logger.info(
                            "Overrode inappropriate SKIP decision to KEEP",
                            article_id=article_id,
                            similarity=max_similarity,
                            original_reasoning=analysis_data.get("reasoning", "")
                        )

                # Create result with validated decision
                result = ContextAnalysisResult(
                    decision=decision,
                    reasoning=analysis_data.get("reasoning", "LLM分析完了"),
                    contextual_summary=analysis_data.get("contextual_summary"),
                    references=reference_objects[:3],  # Limit references
                    similarity_score=max_similarity
                )

                logger.info(
                    "LLM context analysis completed",
                    article_id=article_id,
                    final_decision=result.decision,
                    reasoning_length=len(result.reasoning) if result.reasoning else 0,
                    has_contextual_summary=bool(result.contextual_summary),
                    references_count=len(result.references)
                )

                return result

            except Exception as llm_error:
                logger.error("LLM context analysis failed", error=str(llm_error))

                # F-16 UPDATE detection reconstruction - improved thresholds for reliable 🆙 emoji assignment
                max_similarity = similar_articles[0]["similarity_score"] if similar_articles else 0.0

                # 現実的な閾値に調整（TODO_plan 準拠）
                if max_similarity > 0.98:  # 98%+ similarity = SKIP (virtually identical)
                    decision = "SKIP"
                    reasoning = f"極めて高い類似度（{max_similarity:.3f}）により重複と判定"
                elif max_similarity > 0.90:  # 90%+ similarity = UPDATE
                    decision = "UPDATE"
                    reasoning = f"極めて高い類似度（{max_similarity:.3f}）により明確な続報と判定 - 🆙絵文字付与"
                else:
                    decision = "KEEP"
                    reasoning = f"類似度（{max_similarity:.3f}）により独立記事と判定"

                return ContextAnalysisResult(
                    decision=decision,
                    reasoning=reasoning,
                    contextual_summary=None,
                    references=reference_objects[:3],
                    similarity_score=max_similarity
                )

        except Exception as e:
            logger.error("LLM context analysis error", error=str(e))

            return ContextAnalysisResult(
                decision="KEEP",
                reasoning="分析エラーのため独立記事として処理",
                contextual_summary=None,
                references=[],
                similarity_score=0.0
            )

    async def _call_llm_for_context_analysis(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """Call LLM for context analysis."""

        # Use a simpler approach for context analysis
        # since we need JSON response rather than structured summary
        from langchain_core.messages import HumanMessage, SystemMessage

        # Try each model in fallback order (primary + fallback models)
        all_models = self.llm_router.primary_models + self.llm_router.fallback_models
        for model_name in all_models:
            try:
                client = self.llm_router._get_client(model_name)

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]

                response = await client.ainvoke(messages)
                return response.content

            except Exception as e:
                logger.warning(f"Model {model_name} failed for context analysis", error=str(e))
                continue

        raise Exception("All LLM models failed for context analysis")

    def _parse_llm_response(self, response: str) -> dict:
        """Parse LLM JSON response."""

        try:
            # Try to extract JSON from response
            response = response.strip()

            # Find JSON in response (in case there's extra text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                # Validate required fields
                if "decision" not in data:
                    data["decision"] = "KEEP"
                if "reasoning" not in data:
                    data["reasoning"] = "分析完了"
                if "confidence_score" not in data:
                    data["confidence_score"] = 0.5

                return data
            else:
                logger.warning("No JSON found in LLM response")
                return {"decision": "KEEP", "reasoning": "JSON解析失敗"}

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response", error=str(e))
            return {"decision": "KEEP", "reasoning": "JSON解析エラー"}
        except Exception as e:
            logger.error("Unexpected error parsing LLM response", error=str(e))
            return {"decision": "KEEP", "reasoning": "解析エラー"}

    async def _needs_translation(self, title: str) -> bool:
        """Check if title needs Japanese translation."""
        import re

        # Simple heuristic: if title contains mostly non-Japanese characters
        japanese_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', title)
        total_chars = len(re.findall(r'[a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', title))

        if total_chars == 0:
            return True

        japanese_ratio = len(japanese_chars) / total_chars
        return japanese_ratio < 0.5  # Less than 50% Japanese characters

    async def _generate_simple_japanese_title(self, title: str) -> Union[str, None]:
        """Generate simple Japanese title translation."""
        try:
            if not self.llm_router:
                return None

            prompt = f"""以下の英語記事タイトルを日本語に翻訳してください。

タイトル: {title}

要求:
- 自然で読みやすい日本語
- 50文字以内
- 専門用語を適切に翻訳

翻訳:"""

            translation = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=100,
                temperature=0.2
            )

            if translation:
                # Clean response
                translation = translation.strip()
                # Remove common prefixes
                import re
                translation = re.sub(r'^(翻訳[：:]?\s*|日本語[：:]?\s*)', '', translation)
                translation = translation.strip('"\'「」')

                if len(translation) > 3 and len(translation) <= 60:
                    return translation

        except Exception as e:
            logger.warning(f"Failed to generate Japanese title translation: {e}")

        return None

    def _generate_url_slug(self, title: str) -> str:
        """Generate URL-friendly slug from article title."""
        import re
        import urllib.parse

        if not title:
            return ""

        # Remove common prefixes and suffixes
        title = re.sub(r'^(【[^】]*】|\\[.*?\\]|\d+[\.\)]\s*)', '', title)
        title = re.sub(r'(🆙|[\u2600-\u26FF\u2700-\u27BF])', '', title)  # Remove emojis

        # Extract key terms (company names, tech terms, etc.)
        # Look for capitalized words, quoted terms, and key phrases
        key_terms = []

        # Extract quoted terms
        quoted_terms = re.findall(r'[「『"\'](.*?)[」』"\']', title)
        key_terms.extend(quoted_terms)

        # Extract English tech terms and company names
        english_terms = re.findall(r'\\b[A-Z][a-zA-Z]*(?:[A-Z][a-zA-Z]*)*\\b', title)
        key_terms.extend(english_terms)

        # Extract Japanese tech terms
        tech_terms = re.findall(r'(?:AI|LLM|API|CLI|GPU|CPU|SDK|開発|技術|システム|ツール|プラットフォーム)', title)
        key_terms.extend(tech_terms)

        # If we have key terms, use them
        if key_terms:
            # Take the most relevant terms (first 3)
            selected_terms = key_terms[:3]
            slug = ' '.join(selected_terms)
        else:
            # Fallback to first few words
            words = title.split()[:4]
            slug = ' '.join(words)

        # URL encode for search queries
        slug = urllib.parse.quote_plus(slug)
        return slug


async def analyze_article_context(
    article: SummarizedArticle,
    embedding_manager: Union[EmbeddingManager, None] = None,
    llm_router: Union[LLMRouter, None] = None
) -> ContextAnalysisResult:
    """
    Convenience function to analyze article context.

    Args:
        article: Article to analyze
        embedding_manager: Optional embedding manager
        llm_router: Optional LLM router

    Returns:
        ContextAnalysisResult
    """

    analyzer = ContextAnalyzer(embedding_manager, llm_router)
    return await analyzer.analyze_context(article)
