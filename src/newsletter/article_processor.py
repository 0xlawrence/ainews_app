"""
Article processing and context analysis for newsletters.

This module handles context analysis, sequel detection, multi-source consolidation,
quality filtering, and deduplication of newsletter articles.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_ML_DEPENDENCIES = True
except ImportError:
    HAS_ML_DEPENDENCIES = False

try:
    from src.models.schemas import ProcessedArticle, Citation
    from src.config.settings import get_settings
    from src.utils.embedding_manager import EmbeddingManager
    from src.utils.supabase_client import get_recent_contextual_articles
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

logger = logging.getLogger(__name__)


class ArticleProcessor:
    """Handles article processing, context analysis, and quality filtering."""
    
    def __init__(self, llm_router=None, citation_generator=None):
        """Initialize article processor.
        
        Args:
            llm_router: Optional LLM router for context analysis
            citation_generator: Optional citation generator for multi-source articles
        """
        self.llm_router = llm_router
        self.citation_generator = citation_generator
        if HAS_DEPENDENCIES:
            self.settings = get_settings()
        else:
            self.settings = None
        
        logger.info("Article Processor initialized")
    
    async def apply_context_analysis(self, articles: List['ProcessedArticle']) -> List['ProcessedArticle']:
        """
        Apply context analysis based on PRD F-16.
        Respects workflow's existing context analysis instead of overriding it.
        """
        try:
            # Check if articles already have workflow context analysis results
            workflow_analyzed_count = sum(
                1 for article in articles
                if hasattr(article, 'context_analysis') and article.context_analysis is not None
            )

            if workflow_analyzed_count > 0:
                logger.info(
                    f"Found {workflow_analyzed_count}/{len(articles)} articles with workflow context analysis, "
                    "respecting existing analysis and skipping secondary context analysis"
                )
                # Workflow has already done proper context analysis, don't override it
                return articles

            # Only run secondary analysis if workflow hasn't done it
            logger.info("No workflow context analysis found, running fallback context analysis")

            if not HAS_ML_DEPENDENCIES:
                logger.warning("ML dependencies not available, skipping context analysis")
                return articles

            # Get recent articles from Supabase
            past_articles = await get_recent_contextual_articles(days_back=7, limit=1000)

            if not past_articles:
                logger.info("No past articles found for context analysis.")
                return articles

            # Initialize embedding manager
            embedding_manager = EmbeddingManager()

            # Prepare past articles for similarity comparison
            past_embeddings = []
            past_article_map = {}

            for article_data in past_articles:
                if article_data.get('embedding'):
                    article_id = article_data['article_id']
                    embedding = article_data['embedding']

                    # Convert embedding to numpy array if it's a string
                    if isinstance(embedding, str):
                        try:
                            embedding = json.loads(embedding)
                        except:
                            try:
                                embedding = eval(embedding)
                            except:
                                logger.warning(f"Failed to parse embedding for article {article_id}")
                                continue

                    try:
                        embedding_array = np.array(embedding, dtype=np.float32)
                        # Normalize for cosine similarity
                        embedding_array = embedding_array / np.linalg.norm(embedding_array)
                        past_embeddings.append(embedding_array)
                        past_article_map[article_id] = article_data
                    except Exception as e:
                        logger.warning(f"Failed to process embedding for article {article_id}: {e}")
                        continue

            if not past_embeddings:
                logger.info("No valid embeddings found in past articles for context analysis.")
                return articles

            # Create a matrix of past embeddings for efficient search
            past_embedding_matrix = np.array(past_embeddings)
            past_article_ids = list(past_article_map.keys())

            # Process each current article (only those without workflow analysis)
            updates_found = 0
            for article in articles:
                # Skip if workflow already analyzed this article
                if hasattr(article, 'context_analysis') and article.context_analysis is not None:
                    continue

                try:
                    current_text = f"{article.summarized_article.filtered_article.raw_article.title} {' '.join(article.summarized_article.summary.summary_points)}"
                    current_embedding = await embedding_manager.get_embedding(current_text)

                    if current_embedding is None:
                        continue

                    # Normalize current embedding
                    current_embedding = current_embedding / np.linalg.norm(current_embedding)

                    # Find similar past articles
                    similarities = cosine_similarity(current_embedding.reshape(1, -1), past_embedding_matrix)[0]

                    # Get top 3 most similar articles
                    top_indices = np.argsort(similarities)[-3:][::-1]

                    for i in top_indices:
                        similarity_score = similarities[i]
                        # Very high threshold to reduce false positives
                        if similarity_score > 0.95:  # Very high threshold - only near-identical content
                            past_article_id = past_article_ids[i]
                            past_article_data = past_article_map[past_article_id]

                            logger.info(
                                f"Found potential sequel for '{article.summarized_article.filtered_article.raw_article.title[:50]}...' "
                                f"(score: {similarity_score:.2f}) with '{past_article_data['title'][:50]}...'"
                            )

                            # Use LLM to confirm if it's an update with stricter criteria
                            decision = await self._confirm_update_with_llm(article, past_article_data)

                            if decision == "UPDATE":
                                article.is_update = True
                                article.previous_article_url = past_article_data.get('source_url', '')
                                updates_found += 1

                                logger.info(
                                    "Confirmed fallback UPDATE - emoji handled in integrated title generation",
                                    extra={"article_id": article.summarized_article.filtered_article.raw_article.id}
                                )

                                logger.info(f"Confirmed fallback UPDATE for article {article.summarized_article.filtered_article.raw_article.id}")
                                # Once confirmed, no need to check other past articles
                                break
                except Exception as e:
                    logger.warning(f"Failed to analyze context for article: {e}")
                    continue

            if updates_found > 0:
                logger.info(f"Fallback context analysis completed: found {updates_found} update articles")

            return articles

        except Exception as e:
            logger.error(f"Context analysis failed: {e}", exc_info=True)
            return articles  # Return original articles on failure

    async def _confirm_update_with_llm(self, current_article: 'ProcessedArticle', past_article: Dict) -> str:
        """Use LLM to confirm if the current article is an update to the past one."""
        try:
            current_title = current_article.summarized_article.filtered_article.raw_article.title
            current_summary = " ".join(current_article.summarized_article.summary.summary_points)

            past_title = past_article.get('title', '')
            past_summary = past_article.get('content_summary', '')

            prompt = f"""
            You are an expert news analyst. Compare the "current news" with the "past news" and decide if the current news is a TRUE UPDATE.

            # Current News
            Title: {current_title}
            Summary: {current_summary}

            # Past News
            Title: {past_title}
            Summary: {past_summary}

            # Decision Rules
            Return "UPDATE" ONLY if the current news is:
            1. A continuation of the EXACT SAME story/event
            2. New developments in the EXACT SAME project/product
            3. Follow-up results or consequences of the past news

            Return "UNRELATED" if they are:
            - Different stories about the same company
            - Different products/services
            - General industry news

            Respond with only one word: "UPDATE" or "UNRELATED".
            """

            if self.llm_router:
                response = await self.llm_router.generate_simple_text(
                    prompt=prompt,
                    max_tokens=5,
                    temperature=0.0
                )

                decision = response.strip().upper()
                if decision in ["UPDATE", "UNRELATED"]:
                    return decision
                # If LLM returns something else, be conservative
                return "UNRELATED"

            return "UNRELATED"  # Default to unrelated if LLM fails - be conservative

        except Exception as e:
            logger.warning(f"LLM update confirmation failed: {e}")
            return "UNRELATED"

    async def consolidate_multi_source_articles(self, articles: List['ProcessedArticle']) -> List['ProcessedArticle']:
        """Consolidate temporary multi/related article lists into proper citation data.

        The clustering stage may store helper lists (`_multi_articles_tmp`, `_related_articles_tmp`) on
        individual `ProcessedArticle` instances so that we can later attach richer citation
        information. This helper walks through the provided articles, generates the corresponding
        `Citation` objects (using `CitationGenerator` when available), persists them to the
        article, and finally removes the temporary attributes to avoid unintended side-effects.

        Args:
            articles: List of `ProcessedArticle` objects coming from the workflow.

        Returns:
            The same list with citation information consolidated.
        """

        if not articles:
            return articles

        # If citation generator failed to initialise, just strip helper attributes and return.
        if not self.citation_generator:
            for art in articles:
                for tmp_attr in ("_multi_articles_tmp", "_related_articles_tmp"):
                    if hasattr(art, tmp_attr):
                        delattr(art, tmp_attr)
            return articles

        # Helper to deduplicate citations by URL while preserving order
        def _dedup_citations(citations_list):
            seen = set()
            unique = []
            for cit in citations_list:
                url = getattr(cit, "url", None)
                if url and url not in seen:
                    seen.add(url)
                    unique.append(cit)
            return unique

        for article in articles:
            try:
                # Handle multi-source representative articles
                if hasattr(article, "_multi_articles_tmp") and not getattr(article, 'is_multi_source_enhanced', False):
                    cluster_articles = getattr(article, "_multi_articles_tmp", [])

                    # Generate enhanced summary from multiple sources
                    enhanced_summary = await self._generate_multi_source_summary(
                        representative_article=article,
                        cluster_articles=cluster_articles
                    )

                    # Replace the summary with multi-source enhanced version
                    if enhanced_summary:
                        article.summarized_article.summary.summary_points = enhanced_summary

                    # Generate up to 3 citations including the representative itself
                    citations = await self.citation_generator.generate_multi_source_citations(
                        representative_article=article,
                        cluster_articles=cluster_articles,
                        max_citations=3,
                    )

                    # Persist citations and metadata
                    article.citations = _dedup_citations(citations)
                    article.is_multi_source_enhanced = True

                    # Preserve list of source URLs for transparency
                    article.source_urls = [
                        art.summarized_article.filtered_article.raw_article.url for art in cluster_articles
                    ]

                    # Clean up temporary attribute
                    delattr(article, "_multi_articles_tmp")

                # Handle single articles that have a few "related" articles for extra citations
                if hasattr(article, "_related_articles_tmp"):
                    related_articles = getattr(article, "_related_articles_tmp", [])

                    # Merge with any existing citations while obeying the 3-citation limit
                    existing_citations = list(article.citations) if hasattr(article, 'citations') and article.citations else []

                    additional_citations = await self.citation_generator.generate_citations(
                        article=article,
                        related_sources=[ra.summarized_article.filtered_article.raw_article for ra in related_articles],
                        max_citations=max(0, 3 - len(existing_citations)),
                    )

                    article.citations = _dedup_citations(existing_citations + additional_citations)

                    delattr(article, "_related_articles_tmp")

            except Exception as e:
                logger.warning(f"Failed consolidating multi-source citations: {str(e)}")

        return articles

    async def _generate_multi_source_summary(
        self,
        representative_article: 'ProcessedArticle',
        cluster_articles: List['ProcessedArticle']
    ) -> Optional[List[str]]:
        """Generate comprehensive summary from multiple sources on the same topic."""

        if not self.llm_router or not cluster_articles:
            return None

        try:
            # Collect information from all sources
            source_summaries = []
            rep_raw = representative_article.summarized_article.filtered_article.raw_article

            # Add representative article info
            source_summaries.append({
                "source": rep_raw.source_id,
                "title": rep_raw.title,
                "summary": representative_article.summarized_article.summary.summary_points,
                "content": rep_raw.content[:500] if rep_raw.content else ""
            })

            # Add cluster articles info (limit to top 2 for token management)
            for article in cluster_articles[:2]:
                raw = article.summarized_article.filtered_article.raw_article
                if raw.url != rep_raw.url:  # Avoid duplicates
                    source_summaries.append({
                        "source": raw.source_id,
                        "title": raw.title,
                        "summary": article.summarized_article.summary.summary_points,
                        "content": raw.content[:500] if raw.content else ""
                    })

            # Create comprehensive prompt
            sources_text = ""
            for i, source in enumerate(source_summaries, 1):
                sources_text += f"\n【ソース{i}: {source['source']}】\n"
                sources_text += f"タイトル: {source['title']}\n"
                sources_text += f"要約: {' / '.join(source['summary'][:2])}\n"
                if source['content']:
                    sources_text += f"内容抜粋: {source['content'][:200]}...\n"

            prompt = f"""複数のニュースソースから同一トピックについて報じられた情報を統合し、包括的な要約を生成してください。

情報源:{sources_text}

要求:
- 4つの要約ポイントを生成
- 各ポイントは具体的な数値・企業名・技術名を含む
- 複数ソースの視点を総合した包括的な内容
- 最新の動向と影響を明確に説明
- 各ポイント40-60文字程度

要約ポイント:"""

            response = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=400,
                temperature=0.3
            )

            if response:
                # Parse response into bullet points
                lines = response.strip().split('\n')
                summary_points = []

                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('要約ポイント'):
                        # Remove bullet markers and numbering
                        line = re.sub(r'^[•\-\*\d\.\)]\s*', '', line)
                        if len(line) > 10:  # Filter out very short lines
                            summary_points.append(line)

                if len(summary_points) >= 3:
                    logger.info(
                        f"Generated multi-source summary: representative_id={rep_raw.id}, "
                        f"sources_count={len(source_summaries)}, points_generated={len(summary_points)}"
                    )
                    return summary_points[:4]  # Return max 4 points

            return None

        except Exception as e:
            logger.error(
                f"Failed to generate multi-source summary: "
                f"representative_id={representative_article.summarized_article.filtered_article.raw_article.id}, "
                f"error={str(e)}"
            )
            return None

    def filter_articles_by_quality(
        self,
        articles: List['ProcessedArticle'],
        quality_threshold: float = 0.35,
    ) -> List['ProcessedArticle']:
        """Filter articles whose AI 関連度 (relevance score) >= threshold.

        If an article is missing `ai_relevance_score`, it is kept to avoid
        accidental loss of content during early development phases.
        The resulting list is sorted by relevance score (desc).
        """

        if not articles:
            return []

        def _score(art: 'ProcessedArticle') -> float:
            try:
                base_score = art.summarized_article.filtered_article.ai_relevance_score

                # Add priority boost for official sources and filter low quality
                try:
                    source_priority = getattr(art.summarized_article.filtered_article.raw_article, 'source_priority', 3)
                    if source_priority == 1:  # Official releases
                        base_score += 0.4  # Very strong boost for official sources
                    elif source_priority == 2:  # Newsletters
                        base_score += 0.2  # Strong boost for newsletters
                    elif source_priority == 4:  # Japanese/blog sources
                        # Apply penalty unless score is very high
                        if base_score < 0.7:
                            base_score *= 0.8  # Reduce score for lower-quality sources
                    # Cap at 1.0
                    base_score = min(base_score, 1.0)
                except Exception:
                    pass

                return base_score
            except Exception:
                return 0.5  # neutral default

        filtered = [a for a in articles if _score(a) >= quality_threshold]

        # Always ensure at least one article remains to avoid empty newsletter
        if not filtered:
            filtered = articles[:]

        return sorted(filtered, key=_score, reverse=True)

    def deduplicate_articles(self, articles: List['ProcessedArticle']) -> List['ProcessedArticle']:
        """Remove articles flagged as duplicates or with identical raw IDs."""

        unique_articles = []
        seen_ids = set()
        duplicate_flagged = 0
        id_duplicates = 0

        for art in articles:
            try:
                raw_id = art.summarized_article.filtered_article.raw_article.id
            except Exception:
                raw_id = None

            # Skip if duplicate checker marked it or ID seen already
            is_dup_flag = False
            try:
                is_dup_flag = getattr(art.duplicate_check, "is_duplicate", False)
            except Exception:
                pass

            if is_dup_flag:
                duplicate_flagged += 1
                try:
                    title = art.summarized_article.filtered_article.raw_article.title[:50]
                    logger.debug(f"Article flagged as duplicate: {title}...")
                except:
                    logger.debug("Article flagged as duplicate (title unavailable)")
                continue

            if raw_id and raw_id in seen_ids:
                id_duplicates += 1
                logger.debug(f"Article with duplicate ID: {raw_id}")
                continue

            unique_articles.append(art)
            if raw_id:
                seen_ids.add(raw_id)

        logger.info(
            f"Deduplication summary: total_input={len(articles)}, unique_output={len(unique_articles)}, "
            f"duplicate_flagged={duplicate_flagged}, id_duplicates={id_duplicates}"
        )

        return unique_articles

    def improve_japanese_quality(self, text: str) -> str:
        """
        Improve Japanese text quality by removing inappropriate expressions
        and enhancing naturalness (addresses quality issues found in newsletters).

        Args:
            text: Original text to improve

        Returns:
            Improved text with better quality and naturalness
        """
        if not text or not text.strip():
            return text

        improved_text = text.strip()

        # 1. Remove redundant/verbose expressions
        redundant_patterns = [
            (r'この記事では[、]?', ''),
            (r'記事では[、]?', ''),
            (r'(?:記事|内容)によると[、]?', ''),
            (r'記事の著者は[、]?', ''),
            (r'記事の中で[、]?', ''),
            (r'について言及[しされ](?:て(?:い)?ます?)?[、。]?', 'を発表'),
            (r'について触れて(?:い)?ます?[、。]?', 'を説明'),
            (r'に(?:ついて|関して)詳しく(?:述べ|説明)[しされ](?:て(?:い)?ます?)?[、。]?', 'を詳述'),
            (r'(?:上記|以下)の[、]?', ''),
            (r'提供された情報[によると]?[、]?', ''),
            (r'記事内容[はで][、]?', ''),
        ]

        for pattern, replacement in redundant_patterns:
            improved_text = re.sub(pattern, replacement, improved_text)

        # 2. Remove negative/uncertain expressions
        negative_patterns = [
            (r'(?:記事内容|情報)は断片的で[、]?', ''),
            (r'具体的な(?:説明|内容|詳細)(?:は)?(?:ありません|不明|なし)[、。]?', ''),
            (r'詳細(?:は)?(?:不明|明らかでない)[、。]?', ''),
            (r'情報が(?:少ない|不足)[、。]?', ''),
            (r'不明確な[、]?', ''),
            (r'(?:はっきりと|明確に)(?:は)?(?:述べられて)?いません[、。]?', ''),
        ]

        for pattern, replacement in negative_patterns:
            improved_text = re.sub(pattern, replacement, improved_text)

        # 3. Remove personal name references (but keep company/product names)
        personal_name_patterns = [
            (r'kzzzm氏?(?:による|が|は|の)?[、]?', ''),
            (r'kzzzmさん(?:による|が|は|の)?[、]?', ''),
            (r'(?:著者|筆者|執筆者)(?:の)?(?:kzzzm)?(?:氏|さん)?(?:による|が|は|の)?[、]?', ''),
            (r'ニック・ターリー氏(?:による|が|は|の)?[、]?', 'OpenAI責任者'),
            (r'ターリー氏(?:による|が|は|の)?[、]?', 'OpenAI幹部'),
        ]

        for pattern, replacement in personal_name_patterns:
            improved_text = re.sub(pattern, replacement, improved_text)

        # 4. Fix repetitive "〜しています" patterns and improve naturalness
        repetitive_patterns = [
            # Fix excessive "〜しています" usage with varied expressions
            (r'しています([、。]?\s*.*?)しています', r'しており\1します'),
            (r'ています([、。]?\s*.*?)ています', r'ており\1ます'),
            (r'されています([、。]?\s*.*?)されています', r'され\1ました'),
            (r'ております([、。]?\s*.*?)ております', r'ており\1ます'),

            # Vary verb forms for naturalness - convert stiff "しています" to more varied forms
            (r'発表しています', '発表した'),
            (r'開発しています', '開発中'),
            (r'提供しています', '提供'),
            (r'実施しています', '実施'),
            (r'導入しています', '導入'),
            (r'計画しています', '計画'),
            (r'検討しています', '検討中'),
            (r'進めています', '推進中'),
            (r'取り組んでいます', '取り組み中'),
            (r'展開しています', '展開'),
            (r'運営しています', '運営'),
            (r'継続しています', '継続'),

            # Replace formal passive forms with active ones
            (r'行われています', '実施'),
            (r'進められています', '進行中'),
            (r'実現されています', '実現'),
            (r'強化されています', '強化'),
        ]

        for pattern, replacement in repetitive_patterns:
            improved_text = re.sub(pattern, replacement, improved_text)

        # 5. Improve sentence flow and naturalness
        flow_improvements = [
            # Convert verbose reporting to direct statements
            (r'(?:と|を)発表(?:し|され)(?:て(?:い)?(?:ます|ました))[、。]?', 'を発表'),
            (r'(?:と|を)明らか(?:に)?(?:し|され)(?:て(?:い)?(?:ます|ました))[、。]?', 'を明確化'),
            (r'(?:と|を)説明(?:し|され)(?:て(?:い)?(?:ます|ました))[、。]?', 'を説明'),
            (r'(?:と|を)報告(?:し|され)(?:て(?:い)?(?:ます|ました))[、。]?', 'を報告'),

            # Remove meta-references
            (r'記事(?:の|では?)?[、]?', ''),
            (r'(?:このような|こうした)[、]?', ''),
            (r'同(?:記事|内容)[、]?', ''),

            # Improve conjunctions and reduce monotony
            (r'[、。]\s*また[、]?', '、'),
            (r'[、。]\s*さらに[、]?', '。一方、'),
            (r'[、。]\s*加えて[、]?', '。また、'),
        ]

        for pattern, replacement in flow_improvements:
            improved_text = re.sub(pattern, replacement, improved_text)

        # 6. Final cleanup
        cleanup_patterns = [
            (r'\s+', ' '),  # Multiple spaces to single space
            (r'[、。]\s*[、。]', '。'),  # Multiple punctuation
            (r'^[、。]+', ''),  # Leading punctuation
            (r'[、。]+$', '。'),  # Ensure proper ending
        ]

        for pattern, replacement in cleanup_patterns:
            improved_text = re.sub(pattern, replacement, improved_text)

        return improved_text.strip()

    async def process_articles_pipeline(
        self,
        articles: List['ProcessedArticle'],
        quality_threshold: float = 0.25,
        enable_context_analysis: bool = True,
        enable_multi_source: bool = True
    ) -> List['ProcessedArticle']:
        """
        Complete article processing pipeline with all operations.

        Args:
            articles: Input articles to process
            quality_threshold: Quality threshold for filtering
            enable_context_analysis: Whether to run context analysis
            enable_multi_source: Whether to consolidate multi-source articles

        Returns:
            Processed and filtered articles
        """
        if not articles:
            return []

        logger.info(f"Starting article processing pipeline with {len(articles)} articles")

        processed_articles = articles[:]

        # Step 1: Apply context analysis (sequel detection) if enabled
        if enable_context_analysis:
            logger.info("Step 1: Applying context analysis...")
            processed_articles = await self.apply_context_analysis(processed_articles)

        # Step 2: Consolidate multi-source articles if enabled
        if enable_multi_source:
            logger.info("Step 2: Consolidating multi-source articles...")
            processed_articles = await self.consolidate_multi_source_articles(processed_articles)

        # Step 3: Filter articles by quality
        logger.info("Step 3: Filtering articles by quality...")
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            min_articles_target = getattr(settings.processing, 'min_articles_target', 10)
            # 上限は設定になければ min+2 を安全側デフォルト
            max_articles_target = getattr(settings.workflow, 'max_newsletter_articles', min_articles_target + 2)
        except Exception:
            min_articles_target = 10
            max_articles_target = 12

        filtered_articles = self.filter_articles_by_quality(processed_articles, quality_threshold)

        # Dynamic threshold adjustment if we don't have enough articles
        original_threshold = quality_threshold
        adjustment_attempts = 0
        max_attempts = 3

        while len(filtered_articles) < min_articles_target and adjustment_attempts < max_attempts:
            # Gradually lower threshold to capture more articles
            quality_threshold *= 0.9  # Reduce by 10% each iteration
            adjustment_attempts += 1

            logger.info(
                f"Insufficient articles ({len(filtered_articles)}), adjusting quality threshold: "
                f"{original_threshold if adjustment_attempts == 1 else quality_threshold / 0.9:.3f} → {quality_threshold:.3f}"
            )

            # Re-filter with new threshold
            filtered_articles = self.filter_articles_by_quality(processed_articles, quality_threshold)

            # Break if we have enough articles or hit minimum viable threshold
            if len(filtered_articles) >= min_articles_target or quality_threshold < 0.15:
                break

        # Step 4: Apply deduplication
        logger.info("Step 4: Applying deduplication...")
        pre_dedup_count = len(filtered_articles)
        filtered_articles = self.deduplicate_articles(filtered_articles)
        post_dedup_count = len(filtered_articles)

        logger.info(
            f"Deduplication completed: {pre_dedup_count} → {post_dedup_count} "
            f"({pre_dedup_count - post_dedup_count} removed)"
        )

        # Final check - if still insufficient after deduplication, try one more relaxed filter
        if len(filtered_articles) < min_articles_target and quality_threshold > 0.1:
            logger.warning(
                f"Still insufficient articles after deduplication ({len(filtered_articles)}), "
                "applying emergency threshold relaxation"
            )

            # Emergency threshold for minimum viable newsletter
            emergency_threshold = max(0.1, quality_threshold * 0.7)
            emergency_filtered = self.filter_articles_by_quality(processed_articles, emergency_threshold)
            emergency_deduped = self.deduplicate_articles(emergency_filtered)

            if len(emergency_deduped) > len(filtered_articles):
                filtered_articles = emergency_deduped
                quality_threshold = emergency_threshold

        # Step 5: Limit articles to max target if we have too many
        if len(filtered_articles) > max_articles_target:
            filtered_articles = filtered_articles[:max_articles_target]
            logger.info(f"Limited articles to maximum target: {max_articles_target}")

        logger.info(
            f"Article processing pipeline completed: {len(articles)} → {len(filtered_articles)} "
            f"({len(articles) - len(filtered_articles)} removed, final threshold: {quality_threshold:.3f})"
        )

        return filtered_articles