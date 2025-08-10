"""
Newsletter generation utilities.

This module handles the generation of Markdown newsletters from processed articles.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Union

# Optional dependencies
try:
    import markdown  # type: ignore
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

try:
    import jinja2
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
    jinja2 = None

try:
    from src.models.schemas import Citation, NewsletterOutput, ProcessedArticle
    HAS_SCHEMAS = True
except ImportError:
    HAS_SCHEMAS = False

try:
    from src.utils.logger import setup_logging
    from src.utils.text_processing import remove_duplicate_patterns, fix_inappropriate_period_insertions, fix_particle_duplication
    logger = setup_logging()
    HAS_LOGGER = True
except ImportError:
    # Fallback logger
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    HAS_LOGGER = False

# Import text limits for title length constraints
try:
    from src.config.settings import get_settings
    HAS_TEXT_LIMITS = True
except ImportError:
    TEXT_LIMITS = {'title_short': 120}  # Fallback value for Japanese text
    HAS_TEXT_LIMITS = False

try:
    from src.llm.llm_router import LLMRouter
    from src.utils.citation_generator import CitationGenerator
    HAS_LLM_ROUTER = True
except ImportError:
    HAS_LLM_ROUTER = False
    LLMRouter = None

try:
    import numpy as np
    from numpy import ndarray
    from numpy.linalg import norm
    from sklearn.metrics.pairwise import cosine_similarity

    from src.models.schemas import NewsletterOutput, ProcessedArticle
    from src.utils.embedding_manager import EmbeddingManager
    from src.utils.logger import setup_logging
    from src.utils.supabase_client import SupabaseManager
    HAS_ADVANCED_FEATURES = True
except ImportError:
    HAS_ADVANCED_FEATURES = False

# Remove text_processing import dependency that was causing HAS_LLM_ROUTER to fail
# ensure_sentence_completeness is now defined as module-level function below


class NewsletterGenerator:
    """Generates Markdown newsletters from processed articles."""

    def __init__(self, templates_dir: str = "src/templates"):
        """
        Initialize newsletter generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        self.templates_dir = Path(templates_dir)
        self.settings = get_settings()

        if HAS_LLM_ROUTER:
            self.llm_router = LLMRouter()
        else:
            self.llm_router = None

        # Initialize citation generator for later use
        try:
            from src.utils.citation_generator import (
                CitationGenerator,  # local import to avoid circular refs
            )
            self.citation_generator = CitationGenerator(self.llm_router)
        except Exception:
            # In case CitationGenerator import fails (e.g. missing deps) fallback to None
            self.citation_generator = None

        # Setup Jinja2 environment (if available)
        if HAS_JINJA2 and jinja2:
            self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(self.templates_dir)),
                autoescape=False,  # We want raw markdown
                trim_blocks=False,
                lstrip_blocks=False,
                auto_reload=True,
                cache_size=0,
            )
            # Add custom filters
            self.jinja_env.filters['regex_replace'] = self._regex_replace_filter
            self.jinja_env.filters['slugify'] = self._slugify_filter
            self.jinja_env.filters['short_title'] = self._short_title_filter
            self.jinja_env.filters['toc_format'] = self._toc_format_filter
        else:
            self.jinja_env = None

    async def generate_newsletter(
        self,
        articles: list[ProcessedArticle],
        edition: str = "daily",
        processing_summary: dict = None,
        output_dir: str = "drafts",
        quality_threshold: float = 0.25
    ) -> NewsletterOutput:
        """
        Generate newsletter from processed articles.

        Args:
            articles: List of processed articles
            edition: Newsletter edition type
            processing_summary: Processing statistics
            output_dir: Output directory for generated files
            quality_threshold: Minimum quality score for inclusion (0.0-1.0)

        Returns:
            NewsletterOutput with generated content
        """

        if HAS_LOGGER:
            logger.info(
                "Starting newsletter generation",
                articles_count=len(articles),
                edition=edition,
                quality_threshold=quality_threshold
            )
        else:
            logger.info(
                f"Starting newsletter generation: {len(articles)} articles, edition={edition}, quality_threshold={quality_threshold}"
            )

        # Apply quality filtering with dynamic threshold adjustment for article count assurance
        min_articles_target = 7   # IMPROVED: 記事数を7-8記事に制限（品質重視）
        max_articles_target = 8   # IMPROVED: 上限を8記事に制限（読みやすさ重視）

        # [CRITICAL FIX] Apply context analysis FIRST, then consolidate multi-source articles
        # This ensures that workflow-provided clustering data (_multi_articles_tmp) is properly processed
        logger.info("Starting context analysis and multi-source consolidation...")

        # Step 1: Apply context analysis (sequel detection)
        articles = await self._apply_context_analysis(articles)

        # Step 2: Consolidate multi-source articles (handles workflow clustering results)
        articles = await self._consolidate_multi_source_articles(articles)

        filtered_articles = self._filter_articles_by_quality(articles, quality_threshold)

        # Dynamic threshold adjustment if we don't have enough articles
        original_threshold = quality_threshold
        adjustment_attempts = 0
        max_attempts = 3

        while len(filtered_articles) < min_articles_target and adjustment_attempts < max_attempts:
            # Gradually lower threshold to capture more articles
            quality_threshold *= 0.9  # Reduce by 10% each iteration
            adjustment_attempts += 1

            if HAS_LOGGER:
                logger.info(
                    "Insufficient articles, adjusting quality threshold",
                    current_count=len(filtered_articles),
                    target_minimum=min_articles_target,
                    old_threshold=original_threshold if adjustment_attempts == 1 else quality_threshold / 0.9,
                    new_threshold=quality_threshold,
                    attempt=adjustment_attempts
                )

            # Re-filter with new threshold
            filtered_articles = self._filter_articles_by_quality(articles, quality_threshold)

            # Break if we have enough articles or hit minimum viable threshold
            if len(filtered_articles) >= min_articles_target or quality_threshold < 0.15:
                break

        # Apply deduplication with detailed logging
        pre_dedup_count = len(filtered_articles)
        filtered_articles = self._deduplicate_articles(filtered_articles)
        post_dedup_count = len(filtered_articles)

        if HAS_LOGGER:
            logger.info(
                "Article deduplication completed",
                pre_dedup_count=pre_dedup_count,
                post_dedup_count=post_dedup_count,
                removed_duplicates=pre_dedup_count - post_dedup_count
            )

        # Final check - if still insufficient after deduplication, try one more relaxed filter
        if len(filtered_articles) < min_articles_target and quality_threshold > 0.1:
            if HAS_LOGGER:
                logger.warning(
                    "Still insufficient articles after deduplication, final threshold relaxation",
                    post_dedup_count=len(filtered_articles),
                    target_minimum=min_articles_target
                )

            # Emergency threshold for minimum viable newsletter
            emergency_threshold = max(0.1, quality_threshold * 0.7)
            emergency_filtered = self._filter_articles_by_quality(articles, emergency_threshold)
            emergency_deduped = self._deduplicate_articles(emergency_filtered)

            if len(emergency_deduped) > len(filtered_articles):
                filtered_articles = emergency_deduped
                quality_threshold = emergency_threshold

        # IMPROVED: Limit articles to max_articles_target if we have too many
        if len(filtered_articles) > max_articles_target:
            # Sort by quality score (if available) or keep original order
            filtered_articles = filtered_articles[:max_articles_target]
            if HAS_LOGGER:
                logger.info(
                    "Limited articles to maximum target",
                    limited_count=len(filtered_articles),
                    max_target=max_articles_target
                )

        if HAS_LOGGER:
            logger.info(
                "Quality filtering completed",
                original_count=len(articles),
                filtered_count=len(filtered_articles),
                removed_count=len(articles) - len(filtered_articles)
            )
        else:
            logger.info(f"Quality filtering completed: {len(articles)} -> {len(filtered_articles)} ({len(articles) - len(filtered_articles)} removed)")

        # Generate newsletter content
        newsletter_date = datetime.now()

        # Generate Japanese titles for each article in parallel
        async def process_single_article(article):
            # PRD F-15 COMPLIANCE: Generate citation-based summary if citations exist
            if (hasattr(article, 'citations') and article.citations and
                len(article.citations) > 0 and self.llm_router):

                raw_article = article.summarized_article.filtered_article.raw_article

                # Prepare citations for LLM
                citation_dicts = []
                for citation in article.citations[:3]:  # Max 3 citations per PRD F-15
                    citation_dict = {
                        'title': citation.title,
                        'url': citation.url,
                        'source_name': citation.source_name,
                        'japanese_summary': citation.japanese_summary
                    }
                    citation_dicts.append(citation_dict)

                logger.info(
                    "Regenerating summary with citation context (PRD F-15)",
                    article_id=raw_article.id,
                    citation_count=len(citation_dicts)
                )

                try:
                    # Generate new citation-based summary
                    enhanced_summary = await self.llm_router.generate_citation_based_summary(
                        article_title=raw_article.title,
                        article_content=raw_article.content,
                        article_url=str(raw_article.url),
                        source_name=raw_article.source_id,
                        citations=citation_dicts
                    )

                    # Replace the existing summary with enhanced version
                    article.summarized_article.summary = enhanced_summary

                    logger.info(
                        "Successfully enhanced summary with citations",
                        article_id=raw_article.id,
                        confidence_score=enhanced_summary.confidence_score
                    )

                except Exception as e:
                    logger.warning(
                        "Failed to generate citation-based summary, keeping original",
                        article_id=raw_article.id,
                        error=str(e)
                    )
                    # Keep original summary if enhancement fails

            # 🔥 ULTRA THINK FIX: 統合タイトル生成で【続報】+🆙重複を根本解決
            # Check UPDATE status BEFORE title generation to pass context
            has_update_flag = hasattr(article, 'is_update') and article.is_update
            raw_title_has_emoji = '🆙' in article.summarized_article.filtered_article.raw_article.title
            is_update_article = has_update_flag or raw_title_has_emoji

            # Store update context for later batch processing
            article._temp_is_update = is_update_article

            # Title generation moved to batch processing after this loop
            if (article.summarized_article and
                article.summarized_article.summary and
                article.summarized_article.summary.summary_points):
                article.summarized_article.summary.summary_points = self._cleanup_summary_points(
                    article.summarized_article.summary.summary_points
                )
                # Apply terminology normalization and quality checks to each summary point
                normalized_points = []
                for point in article.summarized_article.summary.summary_points:
                    # First normalize terminology
                    normalized_point = self._normalize_terminology(point)
                    # Then apply quality checks for natural Japanese
                    quality_checked_point = self._improve_japanese_quality(normalized_point)
                    normalized_points.append(quality_checked_point)
                article.summarized_article.summary.summary_points = normalized_points
                # Note: Removed _shorten_summary_points to preserve bullet content integrity per Lawrence's feedback
            return article

        # Process all articles in parallel for cleanup (title generation moved to batch processing below)
        tasks = [process_single_article(article) for article in filtered_articles]
        filtered_articles = await asyncio.gather(*tasks)
        
        # Batch Title Processing (Phase 3.2c optimization)
        await self._process_titles_in_batches(filtered_articles)

        # New Step: Generate Japanese summaries for all secondary citations in parallel
        citation_generator = CitationGenerator(self.llm_router)
        all_citations_to_summarize = []
        for article in filtered_articles:
            if article.citations:
                all_citations_to_summarize.extend(article.citations)

        if all_citations_to_summarize:
            logger.info(f"Generating Japanese summaries for {len(all_citations_to_summarize)} secondary citations...")
            await citation_generator.generate_summaries_for_citations(all_citations_to_summarize)
            logger.info("Finished generating summaries for secondary citations.")

        # Global citation uniqueness and Japanese summary enforcement (improve JP ratio and diversity)
        from urllib.parse import urlparse, urlunparse

        def _normalize_url_global(u: str) -> str:
            try:
                p = urlparse(str(u))
                return urlunparse((p.scheme.lower() or 'https', p.netloc.lower(), p.path.rstrip('/'), '', '', ''))
            except Exception:
                return str(u)

        seen_global_urls: set[str] = set()
        for article in filtered_articles:
            if not getattr(article, 'citations', None):
                continue
            unique: list = []
            for c in article.citations:
                if not getattr(c, 'japanese_summary', None):
                    continue
                norm = _normalize_url_global(getattr(c, 'url', ''))
                if not norm or norm in seen_global_urls:
                    continue
                seen_global_urls.add(norm)
                unique.append(c)
            # Limit to at most 1 citation per article to reduce URL footprint
            article.citations = unique[:1]

        # Generate lead text after all articles are processed
        lead_text = await self._generate_lead_text(filtered_articles, edition)

        # Prepare template context
        context = {
            "date": newsletter_date,
            "edition": edition,
            "articles": filtered_articles,
            "lead_text": lead_text,
            "processing_summary": processing_summary or {},
            "generation_timestamp": newsletter_date.strftime("%Y-%m-%d %H:%M:%S JST"),
            "word_count": 0,  # Will be calculated
        }

        # Render newsletter content ------------------------------------------------
        if self.jinja_env:
            # Use Jinja2 template rendering
            template_name = f"{edition}_newsletter.jinja2"

            try:
                template = self.jinja_env.get_template(template_name)
            except Exception:  # jinja2.TemplateNotFound 等
                if HAS_LOGGER:
                    logger.warning(
                        "Template not found, using default",
                        requested_template=template_name,
                        fallback="daily_newsletter.jinja2"
                    )
                try:
                    template = self.jinja_env.get_template("daily_newsletter.jinja2")
                except Exception:
                    # Fall back to basic markdown generation
                    if HAS_LOGGER:
                        logger.warning("Default template also not found, using basic markdown")
                    template = None
                    newsletter_content = self._generate_basic_markdown(context)
        else:
            template_name = "basic"
            template = None

        # Debug: Log UPDATE articles status before template rendering
        update_articles = [a for a in filtered_articles if getattr(a, 'is_update', False)]
        if update_articles:
            logger.info(
                f"Rendering template with {len(update_articles)} UPDATE articles",
                update_articles=[{
                    'id': a.summarized_article.filtered_article.raw_article.id,
                    'is_update': getattr(a, 'is_update', False),
                    'japanese_title': getattr(a, 'japanese_title', None),
                    'has_emoji': '🆙' in getattr(a, 'japanese_title', '') if getattr(a, 'japanese_title', None) else False
                } for a in update_articles]
            )

        # Render template (if available)
        if template:
            try:
                newsletter_content = template.render(**context)
            except Exception as e:
                if HAS_LOGGER:
                    logger.error(
                        "Template rendering failed",
                        template=template_name,
                        error=str(e)
                    )
                else:
                    logger.error(
                        f"Template rendering failed: template={template_name}, error={str(e)}"
                    )
                raise
        else:
            # Fallback: Generate basic markdown without template
            newsletter_content = self._generate_basic_markdown(context)

        # Collapse excessive blank lines (3+ -> 2)
        newsletter_content = re.sub(r"\n{3,}", "\n\n", newsletter_content)

        # Perform final quality validation on generated newsletter
        newsletter_content = self._validate_and_fix_newsletter_content(newsletter_content, filtered_articles)

        # Comprehensive quality check
        try:
            from src.utils.newsletter_quality_checker import check_newsletter_quality

            logger.info("Performing comprehensive quality check...")
            quality_report = await check_newsletter_quality(
                content=newsletter_content,
                metadata={
                    'edition': edition,
                    'article_count': len(filtered_articles),
                    'generation_timestamp': newsletter_date.isoformat()
                }
            )

            logger.info(
                f"Quality check completed: score={quality_report.overall_score:.2f}, "
                f"issues={quality_report.metrics.get('total_issues', 0)}, "
                f"regeneration_required={quality_report.requires_regeneration}"
            )

            # Log quality issues for monitoring
            if quality_report.issues:
                for issue in quality_report.issues:
                    if issue.severity == 'critical':
                        logger.error(f"Critical quality issue in {issue.location}: {issue.description}")
                    elif issue.severity == 'major':
                        logger.warning(f"Major quality issue in {issue.location}: {issue.description}")
                    else:
                        logger.info(f"Minor quality issue in {issue.location}: {issue.description}")

            # For now, we log the quality report but don't regenerate
            # In future iterations, could implement automatic regeneration for critical issues
            if quality_report.requires_regeneration:
                logger.warning(
                    "Newsletter quality below threshold but continuing with current content. "
                    "Consider implementing automatic regeneration for critical quality issues."
                )

        except Exception as e:
            logger.warning(f"Quality check failed, continuing with newsletter generation: {e}")

        # Calculate word count
        word_count = len(newsletter_content.split())

        # Save Markdown file
        output_file = self._save_newsletter(
            newsletter_content, newsletter_date, edition, output_dir
        )

        # ------------------------------------------------------------------
        # Backup (HTML プレビューは drafts には不要なので生成しない)
        # ------------------------------------------------------------------

        preview_file = None  # HTML ファイルを作成しない

        try:
            from src.utils.backup_manager import backup_file  # local import to avoid cycle
            backup_path = backup_file(output_file)
        except Exception as backup_err:  # pylint: disable=broad-except
            logger.warning(f"Backup failed: {str(backup_err)}")
            backup_path = None

        # 🔥 ULTRA THINK: Final failsafe削除 - 統合タイトル生成で処理済み
        # 重複による「🆙🆙」問題を根本解決
        update_count_check = 0
        for article in filtered_articles:
            if hasattr(article, 'is_update') and article.is_update:
                update_count_check += 1
                # 統合タイトル生成で🆙が正しく付与されているかチェックのみ
                japanese_title = getattr(article, 'japanese_title', None)
                has_emoji = japanese_title and '🆙' in japanese_title
                logger.debug(
                    "UPDATE article title check",
                    article_id=article.summarized_article.filtered_article.raw_article.id,
                    has_emoji=has_emoji,
                    japanese_title=japanese_title
                )

        logger.info(f"F-16 UPDATE article verification: {update_count_check} articles processed with integrated title generation")

        # Create newsletter output
        newsletter_output = NewsletterOutput(
            title=f"{newsletter_date.strftime('%Y年%m月%d日')} AI NEWS TLDR",
            date=newsletter_date,
            lead_text=lead_text,
            articles=filtered_articles,
            metadata={
                "edition": edition,
                "template": template_name,
                "output_file": str(output_file),
                "preview_file": str(preview_file),
                "backup_file": str(backup_path) if backup_path else None,
                "generation_method": "automated"
            },
            word_count=word_count,
            processing_summary=processing_summary or {}
        )

        if HAS_LOGGER:
            logger.info(
                "Newsletter generation completed",
                output_file=str(output_file),
                word_count=word_count,
                articles_included=len(filtered_articles)
            )
        else:
            logger.info(
                f"Newsletter generation completed: {output_file}, word_count={word_count}, articles_included={len(filtered_articles)}"
            )

        return newsletter_output

    async def _apply_context_analysis(self, articles: list[ProcessedArticle]) -> list[ProcessedArticle]:
        """
        [FIXED] Apply context analysis based on PRD F-16.
        Now respects workflow's existing context analysis instead of overriding it.
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

            # Ensure required imports are available
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            from src.utils.embedding_manager import EmbeddingManager
            from src.utils.supabase_client import get_recent_contextual_articles

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
                            import json
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
                        if similarity_score > 0.95: # Very high threshold - only near-identical content
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

                                # 🔥 ULTRA THINK: 🆙絵文字は統合タイトル生成で処理済み
                                # raw_titleへの追加は削除（重複防止）
                                logger.info(
                                    "Confirmed fallback UPDATE - emoji handled in integrated title generation",
                                    article_id=article.summarized_article.filtered_article.raw_article.id
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
            return articles # Return original articles on failure

    async def _confirm_update_with_llm(self, current_article: ProcessedArticle, past_article: dict) -> str:
        """
        Use LLM to confirm if the current article is an update to the past one.
        """
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

            if HAS_LLM_ROUTER and self.llm_router:
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

            return "UNRELATED" # Default to unrelated if LLM fails - be conservative

        except Exception as e:
            logger.warning(f"LLM update confirmation failed: {e}")
            return "UNRELATED"

    async def _generate_lead_text(
        self,
        articles: list[ProcessedArticle],
        edition: str
    ) -> dict[str, Any]:
        """Generate introduction text (title + paragraphs) based on actual article content.

        Returns
        -------
        dict
            {"title": str, "paragraphs": List[str]}
        """

        if not articles:
            return {
                "title": "本日のAI関連ニュース",
                "paragraphs": [
                    "本日は注目すべきAI関連ニュースがございませんでした。"
                ],
            }

        # Try LLM-driven lead text generation first (if available)
        if HAS_LLM_ROUTER and self.llm_router:
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

        # 具体的なタイトル生成（汎用表現を避ける）
        if themes:
            # 企業名・技術名を優先してより具体的なタイトルに
            specific_titles = self._generate_specific_theme_title(themes, articles)
            title = specific_titles or f"{themes[0]}による技術発表"
        else:
            # 最後の手段でも具体的な内容を含める
            title = self._generate_fallback_specific_title(articles)

        # 体言止めを保証（末尾が「。」「です」等なら削除）
        title = re.sub(r"[。.!?ですます]+$", "", title)

        return {
            "title": title,
            "paragraphs": paragraphs,
        }

    async def _generate_llm_lead_text(
        self,
        articles: list[ProcessedArticle],
        edition: str
    ) -> dict[str, Any]:
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
        article_summaries: list[dict],
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

    def _validate_lead_paragraph(self, paragraph: str) -> tuple[bool, str]:
        """リード文の文法検証"""

        if not paragraph or len(paragraph.strip()) < 10:
            return False, "段落が短すぎる"

        paragraph = paragraph.strip()

        # 不完全な文のパターン
        incomplete_patterns = [
            (r'^[^。！？]*[がはをにで]。', "助詞の後に句点"),
            (r'[A-Za-z\u30A0-\u30FF\u3040-\u309F\u4E00-\u9FAF]+が。', "主語の後すぐに句点"),
            (r'[はがをに]$', "助詞で終わる文"),
            (r'[がはをにで]。\s*[^。！？]*$', "文中に不完全な句点")
        ]

        for pattern, reason in incomplete_patterns:
            if re.search(pattern, paragraph):
                return False, f"不完全な文: {reason}"

        # 重複表現のチェック
        if re.search(r'(?:されています|しています).*?(?:と発表|と報告|と説明)', paragraph):
            return False, "重複表現（〜していますと発表）"

        # 文の長さチェック
        if len(paragraph) > 200:
            return False, "文が長すぎる（200文字超）"

        # 適切な語尾チェック
        proper_endings = ('です。', 'ます。', 'ました。', 'ています。', 'でした。', 'ません。')
        if not paragraph.endswith(proper_endings):
            return False, "適切な敬語で終わっていない"

        return True, "OK"

    async def _generate_llm_lead_text_with_retry(self, articles, edition, max_retries=3):
        """文法検証付きリード文生成"""

        for attempt in range(max_retries):
            try:
                result = await self._generate_llm_lead_text(articles, edition)

                if not result or 'lead_paragraphs' not in result:
                    logger.warning(f"Lead text generation attempt {attempt + 1}: No valid response")
                    continue

                # 各段落を検証
                valid_paragraphs = []
                for i, para in enumerate(result.get('lead_paragraphs', [])):
                    is_valid, reason = self._validate_lead_paragraph(para)
                    if is_valid:
                        valid_paragraphs.append(para)
                        logger.info(f"Lead paragraph {i+1} validated: {para[:50]}...")
                    else:
                        logger.warning(f"Invalid paragraph {i+1}: {reason} - {para[:50]}...")

                # 最低2つの有効な段落が必要
                if len(valid_paragraphs) >= 2:
                    # 3つに満たない場合は、最後の段落を複製・修正
                    while len(valid_paragraphs) < 3:
                        if valid_paragraphs:
                            # 最後の段落をベースに展望文を作成
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

        # 全て失敗した場合は安全なフォールバック
        logger.warning("All lead text generation attempts failed, using fallback")
        return self._generate_safe_fallback_lead_text(articles)

    def _generate_safe_fallback_lead_text(self, articles):
        """安全なフォールバック：シンプルで確実なリード文"""

        # 記事数をカウント
        article_count = len(articles) if articles else 0

        # 主要企業を抽出
        companies = set()
        for article in articles[:5]:
            if hasattr(article, 'summarized_article') and article.summarized_article:
                title = article.summarized_article.filtered_article.raw_article.title
                # 企業名を簡単に抽出
                for company in ['OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'Apple']:
                    if company in title:
                        companies.add(company)

        main_companies = list(companies)[:2]
        companies_str = "、".join(main_companies) if main_companies else "主要AI企業"

        # 確実に文法的に正しい文を生成
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

    def _parse_llm_lead_text_response(self, response: str) -> dict[str, Any]:
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
            para = re.sub(r'([^\s。！？])((?:また|さらに)|(?:一方|なお)|(?:ただし|しかし))', r'\1。\2', para)

        # 4. Remove incomplete sentence patterns
        para = re.sub(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)が。\s*', '', para)
        para = re.sub(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)は。\s*', '', para)

        # 5. Fix missing particles before nouns
        para = re.sub(r'([、。])([A-Z][a-z]+)((?:が|は|を|に|で|と))', r'\1\2\3', para)
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

    def _truncate_paragraphs_to_limit(self, paragraphs: list[str], char_limit: int) -> list[str]:
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
                        # Use proper sentence boundary detection
                        truncated_para = truncate_at_sentence_boundary(paragraph, max_length=remaining_chars)
                        if truncated_para and len(truncated_para) > 20:
                            truncated.append(truncated_para)
                        break
                    except:
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

    def _generate_basic_markdown(self, context: dict[str, Any]) -> str:
        """Generate basic markdown newsletter without Jinja2 template."""

        date = context.get("date", datetime.now())
        lead_text = context.get("lead_text", {})
        articles = context.get("articles", [])

        lines = [
            f"# {date.strftime('%Y年%m月%d日')} AI NEWS TLDR",
            "",
        ]

        # Add lead text
        if lead_text and "title" in lead_text:
            lines.extend([
                f"### {lead_text['title']}",
                "",
            ])

            paragraphs = lead_text.get("paragraphs", [])
            for paragraph in paragraphs:
                lines.extend([paragraph, ""])

            # Removed: "それでは各トピックの詳細を見ていきましょう。"
        else:
            lines.extend([
                "### 本日のAI関連ニュース",
                "",
                "本日は注目すべきAI関連ニュースがございませんでした。",
                "",
            ])

        # Add table of contents
        lines.extend(["### 目次", ""])

        visible_articles = [a for a in articles if getattr(a, 'japanese_title', None)]

        for i, article in enumerate(visible_articles, 1):
            title = article.japanese_title[:45] if len(article.japanese_title) > 45 else article.japanese_title
            update_indicator = " 🆙" if getattr(article, 'is_update', False) else ""
            lines.append(f"{i}. {title}{update_indicator}")
            lines.append("")  # Add blank line after each TOC entry

        lines.extend(["", "---", ""])

        # Add articles
        for article in visible_articles:
            title = article.japanese_title
            update_indicator = " 🆙" if getattr(article, 'is_update', False) else ""
            lines.extend([f"### {title}{update_indicator}", ""])

            # Add summary points
            if (article.summarized_article and
                article.summarized_article.summary and
                article.summarized_article.summary.summary_points):

                for point in article.summarized_article.summary.summary_points:
                    lines.append(f"- {point}")
                lines.append("")

            # 引用ブロック
            if hasattr(article, 'citations') and article.citations:
                for citation in article.citations:
                    if isinstance(citation, Citation):
                        lines.extend([self._citation_to_markdown(citation), ""])
                    else:
                        # 旧仕様 (str) にも対応
                        lines.extend([str(citation), ""])

        return "\n".join(lines)

    def _citation_to_markdown(self, citation: 'Citation') -> str:
        """Convert Citation object to Markdown format."""
        if hasattr(citation, 'japanese_summary') and citation.japanese_summary:
            return f"> **{citation.source_name}** ({citation.url}): {citation.japanese_summary}"
        else:
            return f"> **{citation.source_name}** ({citation.url}): {citation.title}"

    def _generate_html_preview(
        self,
        content: str,
        articles: list[ProcessedArticle]
    ) -> str:
        """Generate HTML preview for newsletter content."""
        # This method should be implemented to generate HTML preview
        # For example, you can use a library like BeautifulSoup to parse the Markdown
        # and convert it to HTML for preview purposes.
        pass

    def _extract_article_highlights(self, articles: list[ProcessedArticle]) -> list[str]:
        """Extract PRD-quality highlights from articles for compelling lead text generation."""

        highlights = []

        # Prioritize articles by impact and specificity
        prioritized_articles = self._prioritize_articles_for_highlights(articles)

        for article in prioritized_articles[:3]:  # Top 3 most impactful articles
            try:
                if (article.summarized_article and
                    article.summarized_article.summary and
                    article.summarized_article.summary.summary_points):

                    summary_points = article.summarized_article.summary.summary_points
                    title = article.summarized_article.filtered_article.raw_article.title
                    japanese_title = article.japanese_title or "AI技術新展開"

                    # Create sophisticated highlight with multiple details
                    highlight = self._create_sophisticated_highlight(
                        summary_points, title, japanese_title, getattr(article, 'is_update', False)
                    )

                    if highlight and len(highlight) > 50:  # Ensure substantial content
                        highlights.append(highlight)

                        # Add complementary context for major announcements
                        context = self._extract_contextual_impact(summary_points, title)
                        if context and len(highlights) < 3:
                            highlights.append(context)

            except Exception as e:
                logger.warning(f"Failed to extract highlight from article: {e}")
                continue

        # If we still need more highlights, create thematic summaries
        if len(highlights) < 2:
            thematic_highlights = self._create_thematic_highlights(articles)
            highlights.extend(thematic_highlights[:3-len(highlights)])

        return highlights[:3]  # Maximum 3 highlights for clean lead text

    def _prioritize_articles_for_highlights(self, articles: list[ProcessedArticle]) -> list[ProcessedArticle]:
        """Prioritize articles based on impact indicators for highlight generation."""

        def calculate_impact_score(article: ProcessedArticle) -> float:
            score = 0.0

            try:
                if not (article.summarized_article and article.summarized_article.summary):
                    return 0.0

                summary_points = article.summarized_article.summary.summary_points
                title = article.summarized_article.filtered_article.raw_article.title
                combined_text = title + " " + " ".join(summary_points)

                # Major companies/products boost score
                major_entities = [
                    'OpenAI', 'Google', 'Meta', 'Microsoft', 'Apple', 'Amazon', 'NVIDIA',
                    'Anthropic', 'DeepMind', 'GPT', 'Claude', 'Gemini', 'ChatGPT'
                ]
                for entity in major_entities:
                    if entity in combined_text:
                        score += 2.0

                # Impact indicators
                impact_terms = [
                    '発表', 'リリース', '開始', '公開', '導入', '実装', '改善', '向上',
                    '強化', '拡大', '展開', '活用', '応用', '突破', 'breakthrough'
                ]
                for term in impact_terms:
                    if term in combined_text:
                        score += 1.0

                # Numerical data increases credibility
                if re.search(r'\d+%|\d+倍|\d+[年月日]|\$\d+|¥\d+', combined_text):
                    score += 1.5

                # Update articles get slight priority
                if getattr(article, 'is_update', False):
                    score += 0.5

                # Confidence score from LLM
                if article.summarized_article.summary.confidence_score:
                    score += article.summarized_article.summary.confidence_score

            except Exception:
                return 0.0

            return score

        return sorted(articles, key=calculate_impact_score, reverse=True)

    def _create_sophisticated_highlight(
        self,
        summary_points: list[str],
        title: str,
        japanese_title: str,
        is_update: bool
    ) -> str:
        """Create a sophisticated, PRD-quality highlight sentence."""

        if not summary_points:
            return ""

        first_point = summary_points[0]

        # Extract key entities and actions with advanced patterns
        companies = self._extract_companies(first_point, title)
        products = self._extract_products(first_point, title)
        actions = self._extract_key_actions(first_point)
        metrics = self._extract_metrics(first_point)

        # Build sophisticated highlight
        highlight_parts = []

        # Company/product identification
        if companies or products:
            entity = companies[0] if companies else products[0]
            if is_update:
                highlight_parts.append(f"{entity}が新たに")
            else:
                highlight_parts.append(f"{entity}が")

        # Core action with context (remove company name if already added)
        if actions:
            action = actions[0]

            # Remove company name from action if we already added it
            if companies:
                company = companies[0]
                # Remove company name and particles from the action
                action = re.sub(rf'{re.escape(company)}(?:(?:が|は)|の)?', '', action).strip()

            if metrics:
                metric = metrics[0]
                highlight_parts.append(f"{action}、{metric}の")
            else:
                highlight_parts.append(action)

        # Additional context from second summary point
        if len(summary_points) > 1:
            second_point = summary_points[1]
            context = self._extract_business_context(second_point)
            if context:
                highlight_parts.append(f"。{context}")

        if highlight_parts:
            base_highlight = "".join(highlight_parts)
            # Ensure proper sentence ending
            if not base_highlight.endswith(('。', '。')):
                base_highlight += "と発表しました。"
            return base_highlight

        # Fallback to enhanced first point
        return first_point if len(first_point) > 30 else ""

    def _extract_companies(self, text: str, title: str) -> list[str]:
        """Extract company names with expanded recognition."""
        companies = []
        combined_text = text + " " + title

        company_patterns = [
            r'(OpenAI|ChatGPT|GPT-\d+)',
            r'(Google|Alphabet|DeepMind|Gemini)',
            r'(Meta|Facebook|Instagram)',
            r'(Microsoft|Azure|Copilot)',
            r'(Apple|iPhone|iPad|macOS)',
            r'(Amazon|AWS|Alexa)',
            r'(NVIDIA|Tesla|SpaceX)',
            r'(Anthropic|Claude)',
            r'(IBM|Watson)',
            r'(Samsung|LG|Sony)'
        ]

        for pattern in company_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            companies.extend(matches)

        return list(dict.fromkeys(companies))  # Remove duplicates while preserving order

    def _extract_products(self, text: str, title: str) -> list[str]:
        """Extract product/technology names."""
        products = []
        combined_text = text + " " + title

        product_patterns = [
            r'(GPT-\d+(?:\.\d+)?|ChatGPT|GPT)',
            r'(Claude(?:-\d+)?)',
            r'(Gemini(?:\s+\d+\.\d+)?)',
            r'(LLaMA|Llama)',
            r'(DALL-(?:E|DALL)·E)',
            r'((?:Midjourney|Stable) Diffusion)',
            r'(TensorFlow|PyTorch)',
            r'(Transformer|BERT|T5)'
        ]

        for pattern in product_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            products.extend(matches)

        return list(dict.fromkeys(products))

    def _extract_key_actions(self, text: str) -> list[str]:
        """Extract key business actions."""
        actions = []

        action_patterns = [
            # Extract action part after company name, avoiding full sentence capture
            r'(?:が|は)([^。]*?(?:発表|リリース|公開|開始|導入|実装|展開|提供))',
            r'(?:が|は)([^。]*?(?:向上|改善|強化|拡大|増大|倍増))',
            r'(?:が|は)([^。]*?(?:値下げ|価格).*?(?:削減|コスト).*?削減)',
            r'(?:が|は)([^。]*?(?:新機能|新サービス|新製品|新技術))',
            # Fallback: extract just the action verb and immediate context
            r'((?:\d+[%倍億ドル]*.*?)?(?:発表|リリース|公開|開始|導入))',
            r'((?:\d+[%倍]*.*?)?(?:向上|改善|強化))'
        ]

        for pattern in action_patterns:
            matches = re.findall(pattern, text)
            if matches:
                actions.extend([match.strip() for match in matches if len(match.strip()) > 10])

        return actions[:3]  # Top 3 most relevant actions

    def _extract_metrics(self, text: str) -> list[str]:
        """Extract quantitative metrics."""
        metrics = []

        metric_patterns = [
            r'(\d+%(?:.*?(?:向上|改善|削減|増加|減少))?)',
            r'(\d+倍(?:.*?(?:向上|改善|増加))?)',
            r'(\$\d+(?:\.\d+)?(?:[MKB]illion)?)',
            r'(v?\d+\.\d+)',
            r'(\d+(?:GB|TB|PB))',
        ]

        for pattern in metric_patterns:
            matches = re.findall(pattern, text)
            metrics.extend(matches)

        return metrics

    def _extract_business_context(self, text: str) -> str:
        """Extract business/impact context."""
        context_patterns = [
            r'([^。]*(?:企業|ビジネス|業界|市場|競争)[^。]*)',
            r'([^。]*(?:活用|応用|導入|実用)[^。]*)',
            r'([^。]*(?:開発者|ユーザー|顧客)[^。]*)',
            r'([^。]*(?:影響|効果|成果|結果)[^。]*)'
        ]

        for pattern in context_patterns:
            match = re.search(pattern, text)
            if match:
                context = match.group(1).strip()
                if len(context) > 15 and len(context) < 100:
                    return context

        return ""

    def _extract_contextual_impact(self, summary_points: list[str], title: str) -> str:
        """Create contextual impact statement for complementary information."""

        if len(summary_points) < 2:
            return ""

        # Look for complementary information in subsequent points
        for point in summary_points[1:]:
            if any(keyword in point for keyword in [
                '一方', 'また', 'さらに', '加えて', '同時に', '並行して'
            ]):
                # Extract the contrasting or additional information
                context_match = re.search(r'([^。]*(?:発表|開始|導入|実装)[^。]*)', point)
                if context_match and len(context_match.group(1)) > 20:
                    return f"一方、{context_match.group(1).strip()}。"

        return ""

    def _create_thematic_highlights(self, articles: list[ProcessedArticle]) -> list[str]:
        """Create thematic highlights when individual article highlights are insufficient."""

        highlights = []

        # Analyze themes across articles
        all_text = []
        for article in articles:
            if (article.summarized_article and
                article.summarized_article.summary and
                article.summarized_article.summary.summary_points):
                all_text.extend(article.summarized_article.summary.summary_points)

        combined_text = " ".join(all_text)

        # Technology themes
        if any(term in combined_text for term in ['LLM', 'GPT', '言語モデル', 'AI']):
            highlights.append("大規模言語モデル（LLM）分野では複数の重要な技術進展が報告され、実用化に向けた動きが加速しています。")

        # Business application themes
        if any(term in combined_text for term in ['企業', 'ビジネス', '導入', '活用']):
            highlights.append("企業におけるAI活用が本格化し、具体的な業務改善や新サービス創出の事例が相次いで発表されています。")

        # Research and development themes
        if any(term in combined_text for term in ['研究', '開発', '技術', '性能']):
            highlights.append("AI研究分野では性能向上と実用性を両立させる技術開発が進み、産業界への影響が期待されています。")

        return highlights

    def _extract_key_themes(self, articles: list[ProcessedArticle]) -> list[str]:
        """Extract key themes from articles."""

        # Common AI themes and their keywords
        theme_keywords = {
            "OpenAI・GPT関連": ["openai", "gpt", "chatgpt"],
            "Google・Gemini関連": ["google", "gemini", "bard"],
            "Anthropic・Claude関連": ["anthropic", "claude"],
            "企業・ビジネス": ["企業", "ビジネス", "投資", "資金調達", "startup"],
            "研究・技術": ["研究", "論文", "技術", "開発", "breakthrough"],
            "規制・政策": ["規制", "政策", "法律", "政府", "policy"],
            "量子コンピュータ": ["量子", "quantum"],
            "ロボティクス": ["ロボット", "robot", "自動化"],
            "画像生成": ["画像生成", "stable diffusion", "midjourney", "dall-e"]
        }

        # Count theme occurrences
        theme_counts = {}

        for article in articles:
            title = article.summarized_article.filtered_article.raw_article.title.lower()
            content = ' '.join(article.summarized_article.summary.summary_points).lower()
            text = f"{title} {content}"

            for theme, keywords in theme_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        theme_counts[theme] = theme_counts.get(theme, 0) + 1
                        break  # Count theme only once per article

        # Return top themes
        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
        return [theme for theme, count in sorted_themes[:3] if count > 0]

    def _generate_specific_theme_title(self, themes: list[str], articles: list[ProcessedArticle]) -> Union[str, None]:
        """具体的なテーマタイトルを生成（汎用表現を回避）"""
        try:
            # 記事から具体的な企業名・技術名を抽出
            companies = []
            technologies = []

            for article in articles[:3]:  # 上位3記事から抽出
                raw_article = article.summarized_article.filtered_article.raw_article
                text = f"{raw_article.title} {raw_article.content or ''}"

                # 企業名抽出
                company_patterns = [
                    'OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'Apple',
                    'Amazon', 'Tesla', 'NVIDIA', 'DeepMind', 'LinkedIn', 'GitHub'
                ]

                for company in company_patterns:
                    if company.lower() in text.lower() and company not in companies:
                        companies.append(company)

                # 技術・製品名抽出
                tech_patterns = [
                    'ChatGPT', 'GPT-4', 'Gemini', 'Claude', 'Llama', 'Copilot',
                    'API', 'CLI', 'LLM', 'Agent', 'RAG', 'Transformer'
                ]

                for tech in tech_patterns:
                    if tech.lower() in text.lower() and tech not in technologies:
                        technologies.append(tech)

            # 具体的なタイトルパターンを生成
            if companies and technologies:
                return f"{companies[0]}・{technologies[0]}を中心とした技術進展"
            elif len(companies) >= 2:
                return f"{companies[0]}・{companies[1]}による重要発表"
            elif companies:
                return f"{companies[0]}の技術革新と業界動向"
            elif technologies:
                return f"{technologies[0]}技術の進歩と活用展開"
            else:
                return None

        except Exception as e:
            logger.warning(f"Specific theme title generation failed: {e}")
            return None

    def _generate_fallback_specific_title(self, articles: list[ProcessedArticle]) -> str:
        """フォールバック用の具体的タイトル（汎用表現を避ける）"""
        try:
            if articles:
                # 最初の記事のタイトルから要素を抽出
                first_article = articles[0]
                raw_title = first_article.summarized_article.filtered_article.raw_article.title

                # タイトルから具体的要素を抽出
                if any(company in raw_title for company in ['OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic']):
                    return "大手AI企業による技術発表・戦略転換"
                elif any(tech in raw_title for tech in ['ChatGPT', 'GPT', 'Gemini', 'Claude', 'LLM']):
                    return "主要AIモデルの機能強化・新展開"
                elif any(keyword in raw_title for keyword in ['研究', 'Research', '論文']):
                    return "AI研究の最新成果・技術ブレイクスルー"
                elif any(keyword in raw_title for keyword in ['投資', '資金', 'funding']):
                    return "AI業界の投資動向・企業動向"
                else:
                    # 最後の手段：記事数を活用
                    return f"注目AI企業{len(articles)}社の重要発表"
            else:
                return "AI技術の重要な進展"

        except Exception as e:
            logger.warning(f"Fallback specific title generation failed: {e}")
            return "AI技術の重要な進展"

    def _save_newsletter(
        self,
        content: str,
        date: datetime,
        edition: str,
        output_dir: str
    ) -> Path:
        """Save newsletter content to file."""

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename – include HHMM to avoid overwrite and aid manual comparison
        # "2025-06-22_0135_daily_newsletter.md" のような形式になる
        date_str = date.strftime("%Y-%m-%d_%H%M")
        filename = f"{date_str}_{edition}_newsletter.md"

        output_file = output_path / filename

        # Write content
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            if HAS_LOGGER:
                logger.info("Newsletter saved", file=str(output_file))
            else:
                logger.info(f"Newsletter saved: {output_file}")

        except Exception as e:
            if HAS_LOGGER:
                logger.error(
                    "Failed to save newsletter",
                    file=str(output_file),
                    error=str(e)
                )
            else:
                logger.error(f"Failed to save newsletter: file={output_file}, error={str(e)}")
            raise

        return output_file

    def _regex_replace_filter(self, text: str, pattern: str, replacement: str) -> str:
        """Jinja2 filter for regex replacement."""
        return re.sub(pattern, replacement, text)

    def _slugify_filter(self, text: str) -> str:
        """Jinja2 filter to create URL-friendly slugs."""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.lower()
        text = re.sub(r'[^\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', '-', text)
        text = text.strip('-')
        if len(text) > 50:
            text = text[:50].rstrip('-')
        return text

    def _generate_lead_title_from_articles(self, articles: list[ProcessedArticle], edition: str) -> str:
        """Generate a lead title based on the articles and edition."""

        if not articles:
            return "企業・ビジネスとAI技術の最新動向"

        # Extract key companies and technologies
        companies = set()
        technologies = set()

        for article in articles[:5]:  # Use top 5 articles
            try:
                title = article.summarized_article.filtered_article.raw_article.title

                # Extract companies
                for company in ['OpenAI', 'Google', 'Meta', 'Microsoft', 'Anthropic', 'Apple', 'Amazon', 'LinkedIn']:
                    if company in title:
                        companies.add(company)

                # Extract technologies
                for tech in ['ChatGPT', 'GPT-4', 'Gemini', 'Claude', 'AI', 'LLM', 'エージェント', 'API']:
                    if tech in title:
                        technologies.add(tech)

            except Exception as e:
                logger.debug(f"Error extracting title info: {e}")
                continue

        # Generate title based on content
        companies_list = list(companies)[:2]
        technologies_list = list(technologies)[:2]

        if companies_list and technologies_list:
            companies_str = "・".join(companies_list)
            tech_str = "・".join(technologies_list)
            return f"{companies_str}による{tech_str}の最新動向"
        elif companies_list:
            companies_str = "・".join(companies_list)
            return f"{companies_str}のAI技術開発動向"
        elif technologies_list:
            tech_str = "・".join(technologies_list)
            return f"{tech_str}の企業活用と技術進展"
        else:
            # Default based on edition
            if edition == "daily":
                return "企業・ビジネスとAI技術の最新動向"
            else:
                return f"AI分野の{edition}レポート"

    def _short_title_filter(self, text: str, max_chars: int = 70) -> str:
        """Jinja2 filter to shorten title text."""
        return self._intelligent_truncate(text, max_chars)

    def _toc_format_filter(self, text: str) -> str:
        """Jinja2 filter for formatting table of contents entries with improved Japanese truncation."""

        if not text:
            return text

        # Clean hash marks that might leak into title (Fix for PRD F-5)
        text = re.sub(r'^#+\s*', '', text.strip())
        
        # CRITICAL FIX: Apply text processing fixes before truncation
        text = fix_inappropriate_period_insertions(text)
        text = fix_particle_duplication(text)

        # For TOC, we want to show meaningful content but avoid extremely long entries
        max_toc_length = 90  # Increased from 80 to reduce aggressive truncation

        # If text is already short enough, return as is
        if len(text) <= max_toc_length:
            return text

        # Special handling for titles with quoted content like 「Deep Research」
        # Try to include the quoted part if possible
        quote_pattern = r'「([^」]+)」'
        quote_match = re.search(quote_pattern, text)

        if quote_match:
            quote_start = quote_match.start()
            quote_end = quote_match.end()

            # If the quote appears early enough, try to include it
            if quote_end <= max_toc_length + 15:  # Allow more overflow for quotes
                # Find a good cut point after the quote
                cut_text = text[:quote_end]

                # Look for natural break points after the quote
                remaining = text[quote_end:]
                for break_char in ['を', 'が', 'に', 'で', 'と', 'から', 'まで', 'より']:
                    break_pos = remaining.find(break_char)
                    if break_pos != -1 and break_pos < 15:
                        cut_text = text[:quote_end + break_pos + 1]
                        if len(cut_text) <= max_toc_length + 10:
                            return cut_text.rstrip()
                        break

                # If we can fit the quote, use it
                if len(cut_text) <= max_toc_length + 15:
                    return cut_text.rstrip()

        # Use the improved sentence completion function for better truncation
        result = ensure_sentence_completeness(text, max_toc_length)
        
        # Clean up any trailing particles that make it incomplete
        if result.endswith(('は', 'が', 'を', 'に', 'へ', 'と', 'から', 'まで', 'より')):
            result = result[:-1].rstrip()

        # Only add ellipsis if we actually truncated and don't already have proper ending
        if len(result) < len(text) and not result.endswith(('。', '！', '？', '…')):
            result += '…'

        return result

    async def _process_titles_in_batches(self, articles: list[ProcessedArticle]) -> None:
        """
        Process titles in batches for improved performance (Phase 3.2c optimization).
        
        This method processes article titles using batch LLM processing to significantly
        reduce API call overhead and improve overall performance.
        
        Args:
            articles: List of ProcessedArticle objects to generate titles for
        """
        if not articles:
            return
            
        logger.info(f"Starting batch title processing for {len(articles)} articles")
        
        # Check if batch processing is enabled
        if not self.settings.processing.enable_llm_batch_processing or not self.llm_router:
            logger.info("Batch title processing disabled, using individual processing")
            await self._process_titles_individually(articles)
            return
        
        try:
            # Generate titles using batch processing
            batch_titles = await self.llm_router.generate_titles_batch(
                articles=articles,
                batch_size=self.settings.processing.llm_batch_size,
                max_concurrent_batches=self.settings.processing.max_concurrent_llm_batches
            )
            
            # Assign titles to articles with fallback handling
            successful_titles = 0
            for i, (article, title) in enumerate(zip(articles, batch_titles)):
                if title:
                    # Apply normalization to batch-generated titles
                    article.japanese_title = self._normalize_and_clean_title(title)
                    successful_titles += 1
                else:
                    # Fallback to individual processing for failed titles
                    try:
                        is_update = getattr(article, '_temp_is_update', False)
                        article.japanese_title = await self._generate_article_title_integrated(
                            article, is_update=is_update
                        )
                        if article.japanese_title:
                            article.japanese_title = self._normalize_and_clean_title(article.japanese_title)
                            successful_titles += 1
                    except Exception as e:
                        logger.error(f"Individual title fallback failed for article {i}: {e}")
                        # Ultimate fallback to raw title
                        article.japanese_title = self._generate_fallback_title(article)
                        successful_titles += 1
                
                # Clean up temporary attribute
                if hasattr(article, '_temp_is_update'):
                    delattr(article, '_temp_is_update')
            
            success_rate = (successful_titles / len(articles)) * 100
            logger.info(
                f"Batch title processing completed: {successful_titles}/{len(articles)} titles generated "
                f"({success_rate:.1f}% success rate)"
            )
            
        except Exception as e:
            logger.error(f"Batch title processing failed, falling back to individual processing: {e}")
            await self._process_titles_individually(articles)

    async def _process_titles_individually(self, articles: list[ProcessedArticle]) -> None:
        """
        Fallback method to process titles individually when batch processing fails.
        
        Args:
            articles: List of ProcessedArticle objects to generate titles for
        """
        logger.info(f"Processing {len(articles)} titles individually")
        
        successful_titles = 0
        for i, article in enumerate(articles):
            try:
                is_update = getattr(article, '_temp_is_update', False)
                article.japanese_title = await self._generate_article_title_integrated(
                    article, is_update=is_update
                )
                if article.japanese_title:
                    article.japanese_title = self._normalize_and_clean_title(article.japanese_title)
                    successful_titles += 1
                else:
                    # Ultimate fallback
                    article.japanese_title = self._generate_fallback_title(article)
                    successful_titles += 1
                    
            except Exception as e:
                logger.error(f"Individual title processing failed for article {i}: {e}")
                # Ultimate fallback to raw title
                article.japanese_title = self._generate_fallback_title(article)
                successful_titles += 1
            finally:
                # Clean up temporary attribute
                if hasattr(article, '_temp_is_update'):
                    delattr(article, '_temp_is_update')
        
        success_rate = (successful_titles / len(articles)) * 100
        logger.info(
            f"Individual title processing completed: {successful_titles}/{len(articles)} titles generated "
            f"({success_rate:.1f}% success rate)"
        )

    def _generate_fallback_title(self, article: ProcessedArticle) -> str:
        """
        Generate a fallback title when all other methods fail.
        
        Args:
            article: ProcessedArticle object
            
        Returns:
            A fallback title string
        """
        try:
            raw_title = article.summarized_article.filtered_article.raw_article.title
            is_update = getattr(article, '_temp_is_update', False)
            
            if is_update:
                # Remove redundant 【続報】 and add 🆙 if needed
                clean_title = re.sub(r'【?続報】?[:：]?\s*', '', raw_title)
                return f"🆙 {clean_title}" if '🆙' not in clean_title else clean_title
            else:
                return raw_title
                
        except Exception as e:
            logger.error(f"Fallback title generation failed: {e}")
            return "AI技術ニュース"  # Ultimate fallback

    def _normalize_and_clean_title(self, title: str) -> str:
        """
        Normalize and clean a generated title.
        
        Args:
            title: Raw title to normalize
            
        Returns:
            Cleaned and normalized title
        """
        if not title:
            return title
            
        # Clean any remaining hash marks (safety measure for double hash issue)
        title = re.sub(r'^[#\s]*["\'「]|["\'」]+$', '', title).strip()
        title = re.sub(r'^#+\s*', '', title)
        
        # Apply terminology normalization
        title = self._normalize_terminology(title)
        
        return title

    async def _generate_article_title_integrated(
        self,
        article: ProcessedArticle,
        is_update: bool = False
    ) -> str:
        """
        🔥 ULTRA THINK: 統合タイトル生成で【続報】+🆙重複を根本解決

        Args:
            article: Processed article
            is_update: Whether this is an update article (determines emoji usage)

        Returns:
            Generated Japanese title with proper update handling
        """
        # First try LLM-based generation if available
        if HAS_LLM_ROUTER and self.llm_router:
            try:
                # LLM generates a base summary sentence
                base_summary = await self.llm_router.generate_japanese_title(article)

                if base_summary:
                    logger.debug(f"LLM generated base summary for title: {base_summary}")
                    # Apply integrated formatting with update context
                    return self._format_headline_integrated(base_summary, is_update)
            except Exception as e:
                logger.warning(f"LLM title generation failed, falling back: {e}")

        # Fallback to using the first summary point with integrated logic
        return self._generate_integrated_fallback_title(article, is_update)

    def _validate_title_quality(self, title: str) -> dict[str, Any]:
        """
        Validate title quality and detect common issues.

        Args:
            title: Generated title to validate

        Returns:
            Dictionary with validation results and suggested improvements
        """
        import re

        issues = []
        suggestions = []
        score = 100  # Start with perfect score

        # Check 1: Duplicate word patterns
        duplicate_patterns = [
            (r'(\w+)\s+\1\b', '同じ単語が連続しています'),
            (r'((?:LLM|AI)|GPT)の技術.*?\1', 'LLM/AI用語の重複があります'),
            (r'(\w+)技術\s*\1', '技術用語の重複があります')
        ]

        for pattern, message in duplicate_patterns:
            if re.search(pattern, title):
                issues.append(f'重複パターン: {message}')
                suggestions.append('重複した単語を除去してください')
                score -= 30

        # Check 2: Generic/vague titles
        generic_patterns = [
            r'^LLM（大規模言語モデル）$',
            r'^技術進展$',
            r'^AI技術$',
            r'^新技術$'
        ]

        for pattern in generic_patterns:
            if re.search(pattern, title):
                issues.append('汎用的すぎるタイトルです')
                suggestions.append('より具体的な情報を含めてください')
                score -= 40
                break

        # Check 3: Incomplete titles (cut off)
        if title.endswith('...'):
            issues.append('タイトルが中途半端で切れています')
            suggestions.append('適切な長さで完結させてください')
            score -= 25

        # Check 4: Missing key information
        if len(title) < 15:
            issues.append('タイトルが短すぎます')
            suggestions.append('より詳細な情報を追加してください')
            score -= 15

        # Check 5: Too many emoji
        emoji_count = len(re.findall(r'[�-􏰀-�☀-⟿]', title))
        if emoji_count > 2:
            issues.append('絵文字が多すぎます')
            suggestions.append('絵文字は1-2個までに抑えてください')
            score -= 10

        # Calculate final quality level
        if score >= 90:
            quality = 'excellent'
        elif score >= 70:
            quality = 'good'
        elif score >= 50:
            quality = 'fair'
        else:
            quality = 'poor'

        return {
            'score': max(0, score),
            'quality': quality,
            'issues': issues,
            'suggestions': suggestions,
            'is_acceptable': score >= 60
        }

    def _improve_title_based_on_validation(self, title: str, validation_result: dict[str, Any]) -> str:
        """
        Attempt to automatically improve title based on validation results.

        Args:
            title: Original title
            validation_result: Results from _validate_title_quality

        Returns:
            Improved title
        """
        import re

        improved_title = title

        # Fix duplicate patterns
        improved_title = re.sub(r'(\w+)\s+\1\b', r'\1', improved_title)
        improved_title = re.sub(r'((?:LLM|AI)|GPT)(の技術).*?\1', r'\1\2', improved_title)
        improved_title = re.sub(r'(\w+)技術\s*\1', r'\1技術', improved_title)

        # Remove trailing ellipsis and try to complete
        if improved_title.endswith('...'):
            improved_title = improved_title[:-3].strip()
            if not improved_title.endswith(('。', 'です', 'ます', 'た')):
                improved_title += 'を発表'

        # Clean up spacing
        improved_title = re.sub(r'\s+', ' ', improved_title.strip())

        return improved_title

    async def _generate_article_title(self, article: ProcessedArticle) -> str:
        """
        DEPRECATED: Use _generate_article_title_integrated instead.
        Kept for compatibility with existing code.
        """
        logger.warning("Using deprecated _generate_article_title. Use _generate_article_title_integrated instead.")
        return await self._generate_article_title_integrated(article, is_update=False)

    def _format_headline_integrated(self, summary_sentence: str, is_update: bool) -> str:
        """🔥 ULTRA THINK: 統合ヘッドライン生成で【続報】+🆙重複を完全防止"""

        # 🔥 ULTRA THINK: 【続報】テキスト完全除去強化
        summary_sentence = re.sub(r'【?続報】?[:：]?\s*', '', summary_sentence)
        summary_sentence = re.sub(r'^続報[:：]\s*', '', summary_sentence)
        summary_sentence = re.sub(r'続報\s*[：:]\s*', '', summary_sentence)  # 中間位置の続報も除去
        summary_sentence = re.sub(r'\s*続報$', '', summary_sentence)  # 末尾の続報も除去

        # STEP 2: Extract key entity for specificity
        entity_match = re.search(r'「([^」]+)」|\b([A-Z][a-zA-Z0-9]+)\b', summary_sentence)
        entity = ""
        if entity_match:
            entity = entity_match.group(1) or entity_match.group(2)

        # STEP 3: Truncate for proper length
        truncated_summary = ensure_sentence_completeness(summary_sentence, self.settings.processing.title_short_length)

        # STEP 4: Build base title
        if entity and entity not in truncated_summary:
            base_title = f"{entity}、{truncated_summary}"
        else:
            base_title = truncated_summary

        # STEP 5: Add UPDATE emoji ONLY if is_update=True (unified processing)
        if is_update:
            # Ensure no duplicate emoji
            if '🆙' not in base_title:
                final_title = f"{base_title}🆙"
                logger.debug(f"Added UPDATE emoji: {base_title} → {final_title}")
                return final_title
            else:
                logger.debug(f"UPDATE emoji already present: {base_title}")
                return base_title
        else:
            return base_title

    def _format_headline_from_summary(self, summary_sentence: str) -> str:
        """DEPRECATED: Use _format_headline_integrated instead."""
        logger.warning("Using deprecated _format_headline_from_summary. Use _format_headline_integrated instead.")
        return self._format_headline_integrated(summary_sentence, is_update=False)

    def _generate_integrated_fallback_title(self, article: ProcessedArticle, is_update: bool) -> str:
        """🔥 ULTRA THINK: 統合フォールバックタイトル生成"""
        try:
            summary_points = article.summarized_article.summary.summary_points
            if summary_points and summary_points[0]:
                # Use the first bullet point with integrated processing
                first_point = summary_points[0]

                # 🔥 ULTRA THINK: 【続報】テキスト完全除去強化（フォールバック）
                first_point = re.sub(r'【?続報】?[:：]?\s*', '', first_point)
                first_point = re.sub(r'^続報[:：]\s*', '', first_point)
                first_point = re.sub(r'続報\s*[：:]\s*', '', first_point)  # 中間位置
                first_point = re.sub(r'\s*続報$', '', first_point)  # 末尾
                first_point = re.sub(r'続報.*?、', '', first_point)  # 続報...、パターン

                # Extract key entities and actions - 拡張版
                company_match = re.search(
                    r'(OpenAI|Google|Meta|Microsoft|Anthropic|Apple|Amazon|NVIDIA|DeepMind|Agentica|Together AI|Hugging Face|TechCrunch|VentureBeat|WIRED|IEEE|NextWord|SemiAnalysis|'
                    r'[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*?)(?:社|が|は|の|、)',
                    first_point
                )
                company = company_match.group(1) if company_match else None

                # 数値・成果の抽出強化
                numbers_match = re.search(r'(\d+(?:\.\d+)?[%万億円ドル倍件名]|Pass@1\s+\d+\.\d+%|(?:SOTA|年間)\d+万ドル)', first_point)
                numbers = numbers_match.group(1) if numbers_match else None

                # Pattern matching for key actions/technologies - 拡張版
                action_patterns = [
                    (r'(DeepSWE-(?:Preview|コーディングエージェント))', 'AI開発ツール'),
                    (r'(強化学習|RL|GRPO\+\+|rLLM)', '機械学習技術'),
                    (r'(Pass@1\s+\d+\.\d+%|SOTA|ベンチマーク)', '性能指標'),
                    (r'(SWE-(?:Bench|Qwen3)-32B)', 'AI基盤'),
                    (r'(年間\d+(?:万ドル|収益)|売上|投資)', '事業展開'),
                    (r'(コンサルティング|サービス拡大)', 'ビジネス'),
                    (r'(\d+名?の?(?:AI)?研究者)', '研究者'),
                    (r'(トップ.*?研究者)', '人材'),
                    (r'(新機能|新サービス|新技術)', 'リリース'),
                    (r'(発表|公開|開始|導入|獲得|雇用)', None),
                    (r'(ChatGPT|Claude|Gemini|GPT-\d+)', 'AI'),
                    (r'(Deep (?:Research|RAG)|LLM)', '技術'),
                ]

                key_action = None
                action_type = None
                for pattern, type_hint in action_patterns:
                    match = re.search(pattern, first_point)
                    if match:
                        key_action = match.group(1)
                        action_type = type_hint
                        break

                # Build base title - 改良版
                if company and key_action and numbers:
                    # 最高品質: 企業名 + アクション + 数値
                    base_title = f"{company}、{key_action}で{numbers}達成"
                elif company and key_action:
                    # 高品質: 企業名 + アクション
                    if '研究者' in key_action:
                        base_title = f"{company}が{key_action}を獲得"
                    elif action_type == 'AI開発ツール':
                        base_title = f"{company}の{key_action}が新記録達成"
                    elif action_type == '事業展開':
                        base_title = f"{company}が{key_action}を本格展開"
                    elif action_type:
                        base_title = f"{company}の{action_type}で{key_action}を実現"
                    else:
                        base_title = f"{company}が{key_action}を発表"
                elif company and numbers:
                    # 中品質: 企業名 + 数値
                    base_title = f"{company}、{numbers}の成果を達成"
                elif company:
                    # 基本品質: 企業名のみ
                    if 'AI' in first_point or 'LLM' in first_point:
                        base_title = f"{company}がAI技術で新展開"
                    elif '研究' in first_point:
                        base_title = f"{company}が研究開発分野で新戦略"
                    else:
                        base_title = f"{company}による技術革新発表"
                else:
                    # フォールバック: 要約から智的に抽出
                    # コンテキストエンジニアリング関連の処理
                    if 'コンテキストエンジニアリング' in first_point:
                        base_title = "プロンプト技術がコンテキストエンジニアリングに進化、LLM精度最大化"
                    elif 'プロンプトエンジニアリング' in first_point:
                        base_title = "プロンプトエンジニアリング手法の新展開"
                    elif 'AgenticaとTogether AI' in first_point:
                        base_title = "AgenticaとTogether AI、DeepSWE-Previewでコーディング新記録"
                    elif 'DeepSWE' in first_point or 'Pass@1' in first_point:
                        base_title = "AI開発エージェント、コーディングベンチマークで新記録達成"
                    elif '強化学習' in first_point and 'コーディング' in first_point:
                        base_title = "強化学習AI、プログラミング自動化で画期的進展"
                    else:
                        # 最後の手段
                        base_title = ensure_sentence_completeness(first_point, 45)
                        # 重複除去を最後に適用
                        base_title = self._clean_llm_generated_title(base_title)

                        # Title quality validation
                        if self._is_highly_generic_title(base_title):
                            # Generate a more specific title based on content
                            base_title = self._generate_specific_title_from_content(article)

                # Apply integrated update processing
                if is_update:
                    if '🆙' not in base_title:
                        return f"{base_title}🆙"
                    else:
                        return base_title
                else:
                    return base_title

        except Exception as e:
            logger.warning(f"Integrated fallback title generation failed: {e}")

        # Final fallback with update handling
        fallback = "AI技術の最新動向"
        if is_update:
            return f"{fallback}🆙"
        else:
            return fallback

    def _generate_improved_fallback_title(self, article: ProcessedArticle) -> str:
        """DEPRECATED: Use _generate_integrated_fallback_title instead."""
        logger.warning("Using deprecated _generate_improved_fallback_title. Use _generate_integrated_fallback_title instead.")
        return self._generate_integrated_fallback_title(article, is_update=False)

    def _clean_llm_generated_title(self, title: str) -> str:
        """Clean up common LLM title generation artifacts."""
        if not title or not isinstance(title, str):
            return ""

        # First apply the centralized duplicate pattern removal
        try:
            title = remove_duplicate_patterns(title)
        except Exception as e:
            logger.debug(f"Centralized duplicate removal failed: {e}")

        # Remove duplicate phrases and concatenation errors first
        title = re.sub(r'(.+?)((?:と発表|と報告|と述べ|と語っ|と表明))(.*?)\2', r'\1\2\3', title)
        # Fix duplicate company/product names (e.g., "Claude CodeAI Claude" -> "Claude Code") - more conservative
        title = re.sub(r'\b(\w+)\s+((?:AI|Code|Pro|Plus))\s+\1\b', r'\1 \2', title)
        title = re.sub(r'\b(\w+)((?:AI|Code|Pro|Plus))\1\b', r'\1\2', title)
        # Fix duplicate adjacent words
        title = re.sub(r'(\b\w+)\s+\1\b', r'\1', title)

        # Legacy patterns - kept for additional coverage beyond centralized patterns
        # Pattern 9: Specific numeric/text duplicates like "年間1000万ドルで年間1000万ドル"
        title = re.sub(r'(年間\d+[万億千]?[ドル円])((?:で|を|が|は))\1', r'\1', title)
        title = re.sub(r'(\d+[万億千]?[ドル円])((?:で|を|が|は))\1', r'\1', title)
        # Pattern 10: More specific duplicates with currencies and numbers
        title = re.sub(r'(\d+万ドル)((?:で|を|が|は))(\d+万ドル)', r'\1', title)
        title = re.sub(r'(年間\d+万ドル)((?:で|を|が|は))(年間\d+万ドル)', r'\1', title)

        # Debug logging for title cleaning (can be removed in production)
        if '年間' in title and '万ドル' in title:
            print(f"DEBUG: Currency title after cleaning: '{title}'")

        # Remove verb endings like "〜と報じられました" or "〜と発表しました"
        # to ensure the title is a proper headline (体言止め).
        verb_endings_pattern = r"(?:(?:と報じられました|と発表しました)|(?:と述べました|と語りました)|(?:と表明しました|と明らかにしました)|(?:氏は、|氏は，)|(?:を発表|を報告))$"
        cleaned_title = re.sub(verb_endings_pattern, '', title).strip()

        # Remove incomplete sentence patterns
        incomplete_patterns = r"(?:(?:について|に関して)|(?:において|に対して)|をめぐって)$"
        cleaned_title = re.sub(incomplete_patterns, '', cleaned_title).strip()

        # Additional cleanup for cases where a comma is left at the end
        if cleaned_title.endswith(('、', ',', '。', '：', ':')):
            cleaned_title = cleaned_title[:-1].strip()

        # Remove trailing particles that make titles incomplete and fix them properly
        if cleaned_title.endswith(('が', 'を', 'に', 'は', 'で', 'と', 'での', 'のため', 'により', 'によって', 'として')):
            # 適切な結びでタイトルを完成させる
            if cleaned_title.endswith('が'):
                cleaned_title = cleaned_title[:-1] + 'を発表'
            elif cleaned_title.endswith('を'):
                cleaned_title = cleaned_title[:-1] + 'が進展'
            elif cleaned_title.endswith(('に', 'で')):
                cleaned_title = cleaned_title[:-1] + 'が加速'
            else:
                cleaned_title = cleaned_title.rstrip('はとでのためによりによってとして').strip()

        return cleaned_title

    def _is_highly_generic_title(self, title: str) -> bool:
        """Check if the title is too generic or low-quality."""
        # Reject generic titles and incomplete patterns
        highly_generic_patterns = [
            r'^AI関連ニュース$',
            r'^最新AI動向$',
            r'^技術ニュース$',
            r'^業界動向$',
            r'^最新情報$',
            r'^.*について$',
            r'^.*に関して$',
            r'^.*を発表🆙$',  # Broken titles ending with emoji
            r'^.*の$',  # Titles ending with incomplete possessive
            r'.*を発表しながら',  # Incomplete "while announcing" patterns
        ]

        return any(re.search(pattern, title, re.IGNORECASE) for pattern in highly_generic_patterns)

    def _generate_specific_title_from_content(self, article: ProcessedArticle) -> str:
        """Generate a more specific title when the original is too generic."""
        try:
            # Extract key information from the article
            raw_article = article.summarized_article.filtered_article.raw_article
            summary_points = article.summarized_article.summary.summary_points

            # Try to extract company names from summary
            major_companies = ['OpenAI', 'Google', 'Microsoft', 'Apple', 'Meta', 'Amazon', 'Anthropic',
                              'DeepMind', 'Hugging Face', 'NVIDIA', 'Intel', 'AMD', 'Tesla', 'Uber']

            companies = []
            for point in summary_points:
                for company in major_companies:
                    if company in point:
                        companies.append(company)

            # Remove duplicates while preserving order
            unique_companies = list(dict.fromkeys(companies))

            # Extract key action verbs
            actions = []
            for point in summary_points:
                for action in ['発表', '発売', '公開', 'リリース', '開始', '提供', '導入', '開発', '改良', '向上']:
                    if action in point:
                        actions.append(action)
                        break

            # Build title
            title_parts = []

            # Add company name if found
            if unique_companies:
                title_parts.append(unique_companies[0])
                if len(unique_companies) > 1:
                    title_parts.append(f"と{unique_companies[1]}")

            # Add action if found
            if actions:
                title_parts.append(f"、{actions[0]}")

            # Add subject matter
            first_point = summary_points[0] if summary_points else ""
            if 'AI' in first_point:
                title_parts.append("AI技術")
            elif 'LLM' in first_point:
                title_parts.append("LLM")
            elif 'GPT' in first_point:
                title_parts.append("GPT")
            elif 'API' in first_point:
                title_parts.append("API")

            # Construct final title
            if title_parts:
                generated_title = "".join(title_parts)
                # Ensure it's not too long
                if len(generated_title) > 50:
                    generated_title = generated_title[:47] + "..."
                return generated_title
            else:
                # Ultimate fallback
                return "AI関連技術の最新動向"

        except Exception as e:
            logger.warning(f"Failed to generate specific title: {e}")
            return "AI関連技術の最新動向"

    def _generate_specific_lead_paragraphs(self, articles: list[ProcessedArticle], edition: str) -> list[str]:
        """Generate specific lead paragraphs that reflect actual article content."""
        if not articles:
            return []

        try:
            # Extract specific information from top 3 articles
            specific_items = []
            companies_mentioned = set()
            key_developments = []

            for article in articles[:3]:
                try:
                    if (article.summarized_article and
                        article.summarized_article.summary and
                        article.summarized_article.summary.summary_points):

                        summary_points = article.summarized_article.summary.summary_points
                        title = article.summarized_article.filtered_article.raw_article.title

                        # Extract company names
                        for company in ['OpenAI', 'Google', 'Microsoft', 'Apple', 'Meta', 'Amazon', 'Anthropic',
                                       'DeepMind', 'Hugging Face', 'NVIDIA', 'Tesla', 'AgenticaAI', 'Together AI']:
                            if company in " ".join(summary_points) or company in title:
                                companies_mentioned.add(company)

                        # Extract key developments (first point simplified)
                        if summary_points:
                            first_point = summary_points[0]
                            # Simplify and extract key action
                            for action in ['発表', 'リリース', '開発', '達成', '実現', '提供', '公開', '開始']:
                                if action in first_point:
                                    # Extract the essence of the development
                                    if 'コーディング' in first_point and '記録' in first_point:
                                        key_developments.append('AIエージェントのコーディング性能向上')
                                    elif 'billion' in first_point or '億' in first_point or 'revenue' in first_point:
                                        key_developments.append('AI企業の収益拡大')
                                    elif 'Context Engineering' in first_point or 'プロンプト' in first_point:
                                        key_developments.append('プロンプト技術の進化')
                                    elif 'LLM' in first_point and '学習' in first_point:
                                        key_developments.append('LLM開発手法の体系化')
                                    elif 'Code Hook' in first_point or 'ツール' in first_point:
                                        key_developments.append('開発ツールの機能強化')
                                    break
                except Exception:
                    continue

            # Build specific paragraphs
            paragraphs = []

            # First paragraph: Specific companies and developments
            if companies_mentioned and key_developments:
                companies_list = list(companies_mentioned)[:2]  # Max 2 companies
                company_str = "、".join(companies_list)
                development_str = key_developments[0] if key_developments else "新技術"

                if len(companies_list) == 1:
                    first_para = f"{company_str}が{development_str}を発表するなど、本日は具体的な技術進展が相次いで報告されました。"
                else:
                    first_para = f"{company_str}をはじめとする主要企業が{development_str}など重要な発表を行いました。"
                paragraphs.append(first_para)
            else:
                paragraphs.append("本日は注目すべきAI関連ニュースを厳選してお届けします。")

            # Second paragraph: Additional context
            if len(key_developments) > 1:
                second_dev = key_developments[1]
                second_para = f"また、{second_dev}に関する進展も見られ、AI技術の多面的な発展が続いています。"
                paragraphs.append(second_para)
            elif len(companies_mentioned) > 2:
                other_companies = list(companies_mentioned)[2:]
                if other_companies:
                    other_str = "、".join(other_companies[:2])
                    second_para = f"{other_str}からも重要な技術発表があり、業界全体での競争が激化しています。"
                    paragraphs.append(second_para)
                else:
                    paragraphs.append("これらの技術革新により、AI分野の競争がさらに活発化しています。")
            else:
                paragraphs.append("これらの技術革新により、AI分野の競争がさらに活発化しています。")

            # Third paragraph: Closing
            update_count = sum(1 for article in articles if getattr(article, 'is_update', False))
            if update_count > 0:
                third_para = f"今回は{update_count}件の続報も含め、急速に変化するAI業界の最新動向をお伝えします。"
            else:
                third_para = "それでは各トピックの詳細を見ていきましょう。"
            paragraphs.append(third_para)

            return paragraphs

        except Exception as e:
            logger.warning(f"Failed to generate specific lead paragraphs: {e}")
            return []

    def _shorten_summary_points(self, summary_points: list[str]) -> list[str]:
        """Shorten summary points to fit within character limits."""

        if not summary_points:
            return []

        cleaned_points = []

        for point in summary_points:
            if not isinstance(point, str):
                continue

            # Strip whitespace
            point = point.strip()

            # Skip empty or very short points
            if len(point) < 10:
                continue

            # Remove bullet point markers if present
            point = re.sub(r'^[\-\*\•・\u2022]\s*', '', point)

            # Remove redundant prefixes
            point = re.sub(r'^(また、|さらに、|なお、|一方、)', '', point)

            # Ensure point ends with proper punctuation
            if not point.endswith(('。', '！', '？')):
                point += '。'

            cleaned_points.append(point)

        return cleaned_points

    def _generate_japanese_title(self, article: ProcessedArticle) -> str:
        """
        Generate a Japanese title for an article using template-based rules.

        This is used as a fallback when LLM title generation fails.

        Args:
            article: ProcessedArticle containing the article data

        Returns:
            Generated Japanese title string
        """
        # Ensure regular expressions are available throughout this method
        import re

        try:
            raw_article = article.summarized_article.filtered_article.raw_article
            summary_points = article.summarized_article.summary.summary_points

            # First, try to extract from first summary point
            if summary_points and len(summary_points) > 0:
                first_point = summary_points[0]

                # Improved extraction with better logic
                # Extract company name from summary
                company_patterns = [
                    r'([A-Za-z][A-Za-z0-9]*(?:\\s+[A-Za-z][A-Za-z0-9]*)*?)(?:Union[社, が]|Union[は, の]).{0,20}?(Union[発表, 開始]|Union[提供, リリース]|公開)',
                    r'(OpenAI|Meta|Google|Microsoft|Anthropic|Apple|Amazon|Tesla|NVIDIA|AMD)(?:社|が|は|の)?',
                    r'([A-Za-z]+)(?:社|が|は|の).*?(AI|人工知能|機械学習|ディープラーニング)'
                ]

                company = None
                for pattern in company_patterns:
                    match = re.search(pattern, first_point)
                    if match:
                        company = match.group(1)
                        break

                # Extract key action/technology
                tech_action_patterns = [
                    r'(?:AGI|ChatGPT|Claude|Gemini|GPT-\\d+|Llama|LLaMA)(?:(?:の|を)|が)?(.{0,15}?)(?:発表|リリース|公開|開発)',
                    r'(?:AI|人工知能|機械学習)(?:(?:の|を)|が)?(.{0,15}?)(?:発表|開発|導入|活用)',
                    r'(?:量子|法的|医療|自動化)(?:(?:の|を)|が)?(.{0,10}?)(?:技術|システム|プラットフォーム|ソリューション)',
                    r'(?:著作権|訴訟|契約|投資|買収|提携)(?:(?:の|を)|が)?(.{0,10}?)(?:問題|合意|発表)'
                ]

                tech_action = None
                for pattern in tech_action_patterns:
                    match = re.search(pattern, first_point)
                    if match:
                        tech_action = match.group(1) + (match.group(2) if match.group(2) else "")
                        break

                # Build natural title
                if company and tech_action:
                    title_candidate = f"{company}の{tech_action}関連動向"
                elif company:
                    title_candidate = f"{company}の最新動向"
                elif tech_action:
                    title_candidate = f"{tech_action}関連ニュース"
                else:
                    # Extract first meaningful phrase (up to 20 chars)
                    clean_text = re.sub(r'^[。、]*', '', first_point)
                    sentences = re.split(r'[。、]', clean_text)
                    if sentences and len(sentences[0]) > 5:
                        first_sentence = sentences[0][:20]
                        title_candidate = first_sentence + ("..." if len(sentences[0]) > 20 else "")
                    else:
                        title_candidate = "AI関連ニュース"

                # Clean up redundant phrases
                title_candidate = re.sub(r'しましたを((?:発表|開始)|提供)', r'を\\1', title_candidate)
                title_candidate = re.sub(r'がしました', 'が', title_candidate)
                title_candidate = re.sub(r'\\s+', ' ', title_candidate).strip()

                # Ensure title doesn't end with incomplete sentences
                title_candidate = re.sub(r'[。、]$', '', title_candidate)
                if not re.search(r'[関ニ発表開始導入技術動向]', title_candidate):
                    title_candidate += "関連"

                return title_candidate

            # Extract from original title as last resort
            title = raw_article.title if raw_article.title else ""

            # Clean up English title and create Japanese equivalent
            if title:
                # Remove common prefixes and suffixes
                cleaned_title = re.sub(r'^[A-Za-z0-9\s\-\.]+:', '', title)  # Remove "Company:" prefixes
                cleaned_title = re.sub(r'https?://\S+', '', cleaned_title)  # Remove URLs
                cleaned_title = cleaned_title.strip()

                # Map common English terms to Japanese
                term_mappings = {
                    "announces": "が発表",
                    "releases": "がリリース",
                    "launches": "が開始",
                    "introduces": "が導入",
                    "AI": "AI",
                    "OpenAI": "OpenAI",
                    "Google": "Google",
                    "Meta": "Meta",
                    "Microsoft": "Microsoft"
                }

                # Simple mapping for common patterns
                for eng, _jp in term_mappings.items():
                    if eng.lower() in cleaned_title.lower():
                        # Extract company name before the action
                        words = cleaned_title.split()
                        if len(words) > 0:
                            company = words[0]
                            if company in ["OpenAI", "Google", "Meta", "Microsoft", "Apple", "Amazon", "Tesla", "IBM"]:
                                if "AI" in cleaned_title or "model" in cleaned_title.lower():
                                    return f"{company}の新AI技術発表"
                                else:
                                    return f"{company}の最新動向"

                # If no mapping found, use intelligent truncation
                if len(cleaned_title) > 25:
                    return self._intelligent_truncate(cleaned_title, max_chars=25) + "関連ニュース"
                else:
                    return cleaned_title + "関連ニュース"

            return "AI技術の最新発表"

        except Exception as e:
            logger.warning(f"Template title generation failed: {e}")
            return "AI技術の最新発表"

    def _extract_key_topic_from_summary(self, summary_point: str) -> Union[str, None]:
        """
        Extract key topic/action from a summary point for title generation.

        Args:
            summary_point: A single summary point text

        Returns:
            Key topic string or None if not found
        """

        if not summary_point or not isinstance(summary_point, str):
            return None

        # Pattern to extract key actions/topics from Japanese summary points
        action_patterns = [
            r'(.{5,20}?を発表)',  # "XXXを発表"
            r'(.{5,20}?をリリース)',  # "XXXをリリース"
            r'(.{5,20}?を開始)',  # "XXXを開始"
            r'(.{5,20}?を導入)',  # "XXXを導入"
            r'(.{5,20}?が向上)',  # "XXXが向上"
            r'(.{5,20}?を改善)',  # "XXXを改善"
            r'(.{5,20}?に成功)',  # "XXXに成功"
            r'(.{5,20}?を実現)',  # "XXXを実現"
            r'(.{5,20}?が可能)',  # "XXXが可能"
        ]

        for pattern in action_patterns:
            match = re.search(pattern, summary_point)
            if match:
                topic = match.group(1).strip()
                # Clean up common prefixes
                topic = re.sub(r'^((?:新しい|最新の)|次世代の)', '', topic)
                if len(topic) >= 5:  # Ensure meaningful length
                    return topic

        # Fallback to noun phrase extraction
        noun_patterns = [
            r'([A-Za-z0-9]{3,}[の]?(?:API|SDK|サービス|機能|技術|システム|プラットフォーム))',
            r'([ぁ-ん]{2,}[の]?(?:機能|技術|サービス|システム|性能|精度))',
        ]

        for pattern in noun_patterns:
            match = re.search(pattern, summary_point)
            if match:
                return match.group(1).strip()

        return None

    def _sanitize_heading(self, heading: str) -> str:
        """
        Sanitize heading text for use in table of contents and section headers.

        Args:
            heading: Raw heading text

        Returns:
            Sanitized heading text
        """

        if not heading:
            return ""

        # Remove any markdown syntax
        heading = re.sub(r'[#*_`\[\]]', '', heading)

        # Remove URLs
        heading = re.sub(r'https?://\S+', '', heading)

        # Clean up extra whitespace
        heading = ' '.join(heading.split())

        # Remove trailing punctuation
        heading = re.sub(r'[.,:;!?]+$', '', heading)

        return heading.strip()

    def _normalize_terminology(self, text: str) -> str:
        """
        Normalize AI/tech terminology for consistency.

        Args:
            text: Text to normalize

        Returns:
            Normalized text with consistent terminology
        """

        if not text:
            return ""

        # Common terminology normalizations
        normalizations = {
            # AI model names
            r'\bGPT[\s-]?4[\s-]?o[\s-]?mini\b': 'GPT-4o-mini',
            r'\bGPT[\s-]?4[\s-]?o\b': 'GPT-4o',
            r'\bGPT[\s-]?3\.5\b': 'GPT-3.5',
            r'\bClaude[\s-]?3\.5\b': 'Claude 3.5',
            r'\bGemini[\s-]?Pro\b': 'Gemini Pro',

            # Company names
            r'\bOpenAI\b': 'OpenAI',
            r'\bAnthropic\b': 'Anthropic',
            r'\bGoogle\b': 'Google',
            r'\bMicrosoft\b': 'Microsoft',
            r'\bMeta\b': 'Meta',

            # Technology terms
            r'\bAI\b': 'AI',
            r'\bML\b': 'ML',
            r'\bLLM\b': 'LLM',
            r'\bAPI\b': 'API',
        }

        for pattern, replacement in normalizations.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _cleanup_summary_points(self, summary_points: list[str]) -> list[str]:
        """
        Clean up summary points by removing unwanted content.

        Args:
            summary_points: List of summary points to clean

        Returns:
            Cleaned list of summary points
        """

        if not summary_points:
            return []

        cleaned_points = []

        for point in summary_points:
            if not isinstance(point, str):
                continue

            # Strip whitespace
            point = point.strip()

            # Skip empty or very short points
            if len(point) < 10:
                continue

            # Remove bullet point markers if present
            point = re.sub(r'^[\-\*\•・\u2022]\s*', '', point)

            # Remove redundant prefixes
            point = re.sub(r'^(また、|さらに、|なお、|一方、)', '', point)

            # Ensure point ends with proper punctuation
            if not point.endswith(('。', '！', '？')):
                point += '。'

            cleaned_points.append(point)

        return cleaned_points

    def _validate_and_fix_newsletter_content(
        self,
        content: str,
        articles: list[ProcessedArticle]
    ) -> str:
        """
        Validate and fix newsletter content for quality issues.

        Args:
            content: Generated newsletter content
            articles: Source articles for validation

        Returns:
            Fixed newsletter content
        """

        if not content:
            return ""

        # Fix common formatting issues
        content = re.sub(r'\n{3,}', '\n\n', content)  # Limit consecutive newlines
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)  # Remove trailing whitespace
        content = content.strip()

        # Ensure proper line endings
        if not content.endswith('\n'):
            content += '\n'

        # Validate that all articles are represented
        missing_articles = []
        for article in articles:
            if article.japanese_title:
                # Check if article title appears in content
                if article.japanese_title not in content:
                    missing_articles.append(article)

        if missing_articles:
            logger.warning(f"Found {len(missing_articles)} articles missing from newsletter content")

        return content

    async def _consolidate_multi_source_articles(self, articles: list[ProcessedArticle]) -> list[ProcessedArticle]:
        """Consolidate temporary multi/related article lists into proper citation data.

        The clustering stage may store helper lists (`_multi_articles_tmp`, `_related_articles_tmp`) on
        individual `ProcessedArticle` instances so that we can later attach richer citation
        information.  This helper walks through the provided articles, generates the corresponding
        `Citation` objects (using ``CitationGenerator`` when available), persists them to the
        article, and finally removes the temporary attributes to avoid unintended side-effects.

        Args:
            articles: List of `ProcessedArticle` objects coming from the workflow.

        Returns:
            The same list with citation information consolidated.
        """

        if not articles:
            return articles

        # If citation generator failed to initialise, just strip helper attributes and return.
        if not getattr(self, "citation_generator", None):
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
                if hasattr(article, "_multi_articles_tmp") and not article.is_multi_source_enhanced:
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
                    existing_citations = list(article.citations) if article.citations else []

                    additional_citations = await self.citation_generator.generate_citations(
                        article=article,
                        related_sources=[ra.summarized_article.filtered_article.raw_article for ra in related_articles],
                        max_citations=max(0, 3 - len(existing_citations)),
                    )

                    article.citations = _dedup_citations(existing_citations + additional_citations)

                    delattr(article, "_related_articles_tmp")

            except Exception as e:
                logger.warning(
                    "Failed consolidating multi-source citations",
                    error=str(e),
                )

        return articles

    async def _generate_multi_source_summary(
        self,
        representative_article: ProcessedArticle,
        cluster_articles: list[ProcessedArticle]
    ) -> list[str] | None:
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
                        "Generated multi-source summary",
                        representative_id=rep_raw.id,
                        sources_count=len(source_summaries),
                        points_generated=len(summary_points)
                    )
                    return summary_points[:4]  # Return max 4 points

            return None

        except Exception as e:
            logger.error(
                "Failed to generate multi-source summary",
                representative_id=representative_article.summarized_article.filtered_article.raw_article.id,
                error=str(e)
            )
            return None

    def _improve_japanese_quality(self, text: str) -> str:
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
            (r'(?:(?:記事|内容))によると[、]?', ''),
            (r'記事の著者は[、]?', ''),
            (r'記事の中で[、]?', ''),
            (r'について言及[しされ](?:て(?:い)?ます?)?[、。]?', 'を発表'),
            (r'について触れて(?:い)?ます?[、。]?', 'を説明'),
            (r'に(?:(?:ついて|関して))詳しく(?:(?:述べ|説明))[しされ](?:て(?:い)?ます?)?[、。]?', 'を詳述'),
            (r'(?:(?:上記|以下))の[、]?', ''),
            (r'提供された情報[によると]?[、]?', ''),
            (r'記事内容[はで][、]?', ''),
        ]

        for pattern, replacement in redundant_patterns:
            improved_text = re.sub(pattern, replacement, improved_text)

        # 2. Remove negative/uncertain expressions
        negative_patterns = [
            (r'(?:(?:記事内容|情報))は断片的で[、]?', ''),
            (r'具体的な(?:(?:説明|内容)|詳細)(?:は)?(?:(?:ありません|不明)|なし)[、。]?', ''),
            (r'詳細(?:は)?(?:(?:不明|明らかでない))[、。]?', ''),
            (r'情報が(?:(?:少ない|不足))[、。]?', ''),
            (r'不明確な[、]?', ''),
            (r'(?:(?:はっきりと|明確に))(?:は)?(?:述べられて)?いません[、。]?', ''),
        ]

        for pattern, replacement in negative_patterns:
            improved_text = re.sub(pattern, replacement, improved_text)

        # 3. Remove personal name references (but keep company/product names)
        personal_name_patterns = [
            (r'kzzzm氏?(?:(?:による|が)|(?:は|の))?[、]?', ''),
            (r'kzzzmさん(?:(?:による|が)|(?:は|の))?[、]?', ''),
            (r'(?:(?:著者|筆者)|執筆者)(?:の)?(?:kzzzm)?(?:(?:氏|さん))?(?:(?:による|が)|(?:は|の))?[、]?', ''),
            (r'ニック・ターリー氏(?:(?:による|が)|(?:は|の))?[、]?', 'OpenAI責任者'),
            (r'ターリー氏(?:(?:による|が)|(?:は|の))?[、]?', 'OpenAI幹部'),
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
            (r'記事(?:の|では?)[、]?', ''),
            (r'(?:このような|こうした)[、]?', ''),
            (r'同(?:記事|内容)[、]?', ''),

            # Improve conjunctions and reduce monotony
            (r'[、。]\s*また[、]?', '、'),
            (r'[、。]\s*さらに[、]?', '。一方、'),
            (r'[、。]\s*加えて[、]?', '。また、'),
            (r'[、。]\s*なお[、]?', '。'),

            # Add variety to sentence patterns to reduce stiffness
            (r'(\w+)は(\w+)を', r'\1が\2を'),  # Vary は/が usage
            (r'による(\w+)', r'での\1'),  # Vary による/での
            (r'において(\w+)', r'で\1'),  # Simplify において
            (r'に関する(\w+)', r'の\1'),  # Simplify に関する
            (r'についての(\w+)', r'の\1'),  # Simplify についての
        ]

        for pattern, replacement in flow_improvements:
            improved_text = re.sub(pattern, replacement, improved_text)

        # 5. Clean up spacing and punctuation
        improved_text = re.sub(r'\s+', ' ', improved_text)  # Multiple spaces to single
        improved_text = re.sub(r'[、。]{2,}', '。', improved_text)  # Multiple punct to single
        improved_text = re.sub(r'、\s*。', '。', improved_text)  # Comma before period

        # 6. Ensure proper sentence ending
        if improved_text and not improved_text.endswith(('。', '！', '？', '：', '）', '」', '』')):
            if improved_text.endswith('です') or improved_text.endswith('ます'):
                improved_text += '。'

        # 7. Validate minimum meaningful content
        if len(improved_text.strip()) < 10:
            logger.debug(f"Text too short after improvements: '{improved_text.strip()}'")
            return text  # Return original if too short

        logger.debug(f"Japanese quality improvement: '{text[:50]}...' -> '{improved_text[:50]}...'")
        return improved_text.strip()

    # ------------------------------------------------------------------
    # Quality filtering & deduplication helpers (re-added)
    # ------------------------------------------------------------------

    def _filter_articles_by_quality(
        self,
        articles: list[ProcessedArticle],
        quality_threshold: float = 0.35,
    ) -> list[ProcessedArticle]:
        """Filter articles whose AI 関連度 (relevance score) >= threshold.

        If an article is missing `ai_relevance_score`, it is kept to avoid
        accidental loss of content during early development phases.
        The resulting list is sorted by relevance score (desc).
        """

        if not articles:
            return []

        def _score(art: ProcessedArticle) -> float:
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

    def _deduplicate_articles(self, articles: list[ProcessedArticle]) -> list[ProcessedArticle]:
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
                if HAS_LOGGER:
                    try:
                        title = art.summarized_article.filtered_article.raw_article.title[:50]
                        logger.debug(f"Article flagged as duplicate: {title}...")
                    except:
                        logger.debug("Article flagged as duplicate (title unavailable)")
                continue

            if raw_id and raw_id in seen_ids:
                id_duplicates += 1
                if HAS_LOGGER:
                    logger.debug(f"Article with duplicate ID: {raw_id}")
                continue

            unique_articles.append(art)
            if raw_id:
                seen_ids.add(raw_id)

        if HAS_LOGGER:
            logger.info(
                "Deduplication summary",
                total_input=len(articles),
                unique_output=len(unique_articles),
                duplicate_flagged=duplicate_flagged,
                id_duplicates=id_duplicates
            )

        return unique_articles

    # ------------------------------------------------------------------
    # Text truncation helper
    # ------------------------------------------------------------------

    def _intelligent_truncate(self, text: str, max_chars: int = 70) -> str:
        """Smartly truncate *text* within *max_chars* keeping sentence integrity."""
        return ensure_sentence_completeness(text, max_chars)

    def save_to_file(self, content: str, output_dir: str = "drafts") -> str:
        """Save newsletter content to markdown file with organized directory structure."""

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

        # Create organized directory structure: drafts/YYYY/MM/
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")
        organized_dir = os.path.join(output_dir, year, month)

        # Ensure directory exists
        os.makedirs(organized_dir, exist_ok=True)

        filename = f"{timestamp}_daily_newsletter.md"
        filepath = os.path.join(organized_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"Newsletter saved to: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to save newsletter: {str(e)}")
            # Fallback to flat structure if organized save fails
            fallback_path = os.path.join(output_dir, filename)
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return fallback_path


async def generate_markdown_newsletter(
    articles: list[ProcessedArticle],
    edition: str = "daily",
    processing_summary: dict = None,
    output_dir: str = "drafts",
    templates_dir: str = "src/templates"
) -> NewsletterOutput:
    """
    Convenience function to generate newsletter.

    Args:
        articles: Processed articles
        edition: Newsletter edition
        processing_summary: Processing statistics
        output_dir: Output directory
        templates_dir: Templates directory

    Returns:
        NewsletterOutput
    """

    generator = NewsletterGenerator(templates_dir)
    return await generator.generate_newsletter(
        articles, edition, processing_summary, output_dir
    )

# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------

def ensure_sentence_completeness(text: str, max_chars: int = None) -> str:
    """
    日本語に最適化された文境界検出による自然な切断処理。
    目次の可読性を最大化するため、適切な切断点を優先度順に探索。
    """

    # Use TEXT_LIMITS default if max_chars not specified
    if max_chars is None:
        max_chars = TEXT_LIMITS.get('title_short', 120)

    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    snippet = text[:max_chars]

    # 優先度順の切断ポイント定義
    cut_strategies = [
        # 1. 完全な文境界（最優先）
        {
            'patterns': [r'[。！？]'],
            'include_match': True,
            'min_length_ratio': 0.3,
            'add_ellipsis': False,
            'description': '文末句読点'
        },

        # 2. 自然な休止点
        {
            'patterns': [r'[、，]'],
            'include_match': True,
            'min_length_ratio': 0.4,
            'add_ellipsis': False,
            'description': '読点'
        },

        # 3. 括弧の外側（情報の完結性を保持）
        {
            'patterns': [r'[）」』]'],
            'include_match': True,
            'min_length_ratio': 0.3,
            'add_ellipsis': False,
            'description': '括弧終了'
        },

        # 4. 接続詞の前（論理構造を保持）
        {
            'patterns': [r'(?=(?:また|さらに)|(?:一方|なお)|(?:ただし|しかし)|そして)'],
            'include_match': False,
            'min_length_ratio': 0.4,
            'add_ellipsis': True,
            'description': '接続詞前'
        },

        # 5. 助詞の後（最後の手段、但し不完全感を避ける）
        {
            'patterns': [r'(?<=[のでもや])(?!\s*[はがをに])'],  # 「は」「が」等の直前は避ける
            'include_match': False,
            'min_length_ratio': 0.5,
            'add_ellipsis': True,
            'description': '助詞後（安全な位置）'
        }
    ]

    min_acceptable_length = max(10, int(max_chars * 0.3))

    # 各戦略を試行
    for strategy in cut_strategies:
        for pattern in strategy['patterns']:
            matches = list(re.finditer(pattern, snippet))
            if matches:
                # 最後のマッチを使用
                last_match = matches[-1]
                cut_pos = last_match.end() if strategy['include_match'] else last_match.start()

                # 最小長要件チェック
                if cut_pos >= min_acceptable_length:
                    result = snippet[:cut_pos].rstrip()

                    # 不完全な助詞で終わる場合は修正
                    if result.endswith(('は', 'が', 'を', 'に', 'で', 'と', 'から')):
                        result = result[:-1].rstrip()

                    # 残りコンテンツの確認
                    remaining = text[cut_pos:].strip()
                    needs_ellipsis = (
                        strategy['add_ellipsis'] and
                        remaining and
                        len(remaining) > 8 and
                        not result.endswith(('。', '！', '？'))
                    )

                    final_result = result + ('…' if needs_ellipsis else '')

                    # デバッグログ（目次の品質確認用）
                    logger.debug(
                        f"TOC truncation: '{strategy['description']}' at {cut_pos}/{max_chars} chars"
                    )

                    return final_result

    # フォールバック：安全な位置での切断
    # 単語境界を探す（日本語では空白や句読点）
    safe_positions = []
    for i in range(len(snippet) - 1, min_acceptable_length, -1):
        char = snippet[i]
        if char in '　 、，。！？）」』':
            safe_positions.append(i + (1 if char in '、，。！？）」』' else 0))
        elif i > 0 and snippet[i-1] in 'のでもや' and char not in 'はがをに':
            safe_positions.append(i)

    if safe_positions:
        cut_pos = safe_positions[0]  # 最も後ろの安全な位置
        result = snippet[:cut_pos].rstrip()

        # 最終的な品質チェック
        if not result.endswith(('。', '！', '？', '、', '）', '」', '』')):
            remaining = text[cut_pos:].strip()
            if remaining and len(remaining) > 8:
                result += '…'

        return result

    # 最終フォールバック：単純切断
    fallback_pos = max_chars - 3
    while fallback_pos > min_acceptable_length and snippet[fallback_pos] in 'はがをに':
        fallback_pos -= 1

    return snippet[:fallback_pos].rstrip() + '…'

