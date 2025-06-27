"""
Newsletter generation utilities.

This module handles the generation of Markdown newsletters from processed articles.
"""

import os
import re
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import shutil
from urllib.parse import urlparse
from collections import defaultdict
import json

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
    from src.models.schemas import NewsletterOutput, ProcessedArticle, Citation
    HAS_SCHEMAS = True
except ImportError:
    HAS_SCHEMAS = False

try:
    from src.utils.logger import setup_logging
    logger = setup_logging()
    HAS_LOGGER = True
except ImportError:
    # Fallback logger
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    HAS_LOGGER = False

try:
    from src.llm.llm_router import LLMRouter
    from src.utils.citation_generator import CitationGenerator
    HAS_LLM_ROUTER = True
except ImportError:
    HAS_LLM_ROUTER = False
    LLMRouter = None

try:
    from numpy import ndarray
    from src.models.schemas import ProcessedArticle, NewsletterOutput
    from src.utils.logger import setup_logging
    from src.utils.supabase_client import SupabaseManager
    from src.utils.embedding_manager import EmbeddingManager
    from numpy.linalg import norm
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
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
        
        if HAS_LLM_ROUTER:
            self.llm_router = LLMRouter()
        else:
            self.llm_router = None
        
        # Initialize citation generator for later use
        try:
            from src.utils.citation_generator import CitationGenerator  # local import to avoid circular refs
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
        articles: List[ProcessedArticle],
        edition: str = "daily",
        processing_summary: Dict = None,
        output_dir: str = "drafts",
        quality_threshold: float = 0.35
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
        min_articles_target = 7  # Ensure最低7本の記事を確保する（Lawrence からの追加要望）
        max_articles_target = 10  # 上限を10本に拡大
        
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
        
        # Apply deduplication
        filtered_articles = self._deduplicate_articles(filtered_articles)
        
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
        lead_text = await self._generate_lead_text(filtered_articles, edition)
        
        # Generate Japanese titles for each article in parallel
        async def process_single_article(article):
            # First try LLM-based title generation, fallback to template-based
            article.japanese_title = await self._generate_article_title(article)

            # Fallback for failed title generation to prevent article loss
            if not article.japanese_title:
                raw_title = article.summarized_article.filtered_article.raw_article.title
                logger.warning(
                    "Japanese title generation failed, using original title as fallback",
                    article_id=article.summarized_article.filtered_article.raw_article.id
                )
                article.japanese_title = raw_title

            # PRD F-16準拠: UPDATE記事に🆙絵文字を追加
            if hasattr(article, 'is_update') and article.is_update:
                if not article.japanese_title.endswith('🆙'):
                    article.japanese_title = f"{article.japanese_title}🆙"
                    logger.info(
                        "Added UPDATE emoji to title",
                        article_id=article.summarized_article.filtered_article.raw_article.id,
                        title=article.japanese_title
                    )

            # Normalize terminology in Japanese title
            if article.japanese_title:
                article.japanese_title = self._normalize_terminology(article.japanese_title)
            if (article.summarized_article and 
                article.summarized_article.summary and 
                article.summarized_article.summary.summary_points):
                article.summarized_article.summary.summary_points = self._cleanup_summary_points(
                    article.summarized_article.summary.summary_points
                )
                # Apply terminology normalization to each summary point
                normalized_points = []
                for point in article.summarized_article.summary.summary_points:
                    normalized_points.append(self._normalize_terminology(point))
                article.summarized_article.summary.summary_points = normalized_points
                # Note: Removed _shorten_summary_points to preserve bullet content integrity per Lawrence's feedback
            return article
        
        # Process all articles in parallel for title generation and cleanup
        tasks = [process_single_article(article) for article in filtered_articles]
        filtered_articles = await asyncio.gather(*tasks)
        
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
    
    async def _apply_context_analysis(self, articles: List[ProcessedArticle]) -> List[ProcessedArticle]:
        """
        [NEW] Apply context analysis based on PRD F-16.
        Checks for sequels to past articles and applies metadata.
        """
        try:
            # Ensure required imports are available
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            from src.utils.supabase_client import get_recent_contextual_articles
            from src.utils.embedding_manager import EmbeddingManager

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

            # Process each current article
            updates_found = 0
            for article in articles:
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
                        if similarity_score > 0.80: # Lowered threshold for better sequel detection
                            past_article_id = past_article_ids[i]
                            past_article_data = past_article_map[past_article_id]
                            
                            logger.info(
                                f"Found potential sequel for '{article.summarized_article.filtered_article.raw_article.title[:50]}...' "
                                f"(score: {similarity_score:.2f}) with '{past_article_data['title'][:50]}...'"
                            )

                            # Use LLM to confirm if it's an update
                            decision = await self._confirm_update_with_llm(article, past_article_data)
                            
                            if decision == "UPDATE":
                                article.is_update = True
                                article.previous_article_url = past_article_data.get('source_url', '')
                                updates_found += 1
                                logger.info(f"Confirmed UPDATE for article {article.summarized_article.filtered_article.raw_article.id}")
                                # Once confirmed, no need to check other past articles
                                break
                except Exception as e:
                    logger.warning(f"Failed to analyze context for article: {e}")
                    continue
            
            if updates_found > 0:
                logger.info(f"Context analysis completed: found {updates_found} update articles")
            
            return articles

        except Exception as e:
            logger.error(f"Context analysis failed: {e}", exc_info=True)
            return articles # Return original articles on failure

    async def _confirm_update_with_llm(self, current_article: ProcessedArticle, past_article: Dict) -> str:
        """
        Use LLM to confirm if the current article is an update to the past one.
        """
        try:
            current_title = current_article.summarized_article.filtered_article.raw_article.title
            current_summary = " ".join(current_article.summarized_article.summary.summary_points)
            
            past_title = past_article.get('title', '')
            past_summary = past_article.get('content_summary', '')

            prompt = f"""
            You are an expert news analyst. Compare the "current news" with the "past news" and decide their relationship.

            # Current News
            Title: {current_title}
            Summary: {current_summary}

            # Past News
            Title: {past_title}
            Summary: {past_summary}

            # Decision
            Based on the content, is the "current news" a direct follow-up, update, or sequel to the "past news"?
            Respond with only one word: "UPDATE", "RELATED", or "UNRELATED".
            """

            if HAS_LLM_ROUTER and self.llm_router:
                response = await self.llm_router.generate_simple_text(
                    prompt=prompt,
                    max_tokens=5,
                    temperature=0.0
                )
                
                decision = response.strip().upper()
                if decision in ["UPDATE", "RELATED", "UNRELATED"]:
                    return decision
            
            return "RELATED" # Default to related if LLM fails

        except Exception as e:
            logger.warning(f"LLM update confirmation failed: {e}")
            return "RELATED"
    
    async def _generate_lead_text(
        self,
        articles: List[ProcessedArticle],
        edition: str
    ) -> Dict[str, Any]:
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
        
        # Extract key highlights from actual articles
        key_highlights = self._extract_article_highlights(articles)
        themes = self._extract_key_themes(articles)

        # --- paragraphs --------------------------------------------------
        paragraphs: List[str] = []
        
        if edition == "daily":
            # First paragraph: Main highlights with specific details
            if key_highlights:
                main_highlight = key_highlights[0]
                paragraphs.append(main_highlight)
            elif themes:
                joined = "、".join(themes)
                paragraphs.append(
                    f"本日は{joined}分野を中心とした重要なAI関連の動向が相次いで発表されました。"
                )
            else:
                paragraphs.append(
                    "本日は注目すべきAIニュースを厳選してお届けします。"
                )

            # Second paragraph: Additional context or updates
            if len(key_highlights) > 1:
                second_highlight = key_highlights[1]
                paragraphs.append(second_highlight)
            elif update_count > 0:
                paragraphs.append(
                    f"一方で、{update_count}件の続報も含め、急速に変化するAI業界の最新動向をお伝えします。"
                )
            elif len(articles) >= 5:
                paragraphs.append(
                    "企業の新技術発表から研究機関の成果まで、多方面にわたる重要な発表が続いています。"
                )
            else:
                paragraphs.append(
                    "技術革新とビジネス活用の両面で注目すべき動きが見られます。"
                )
            
            # Third paragraph: Additional details or context
            if len(key_highlights) > 2:
                third_highlight = key_highlights[2]
                paragraphs.append(third_highlight)
            elif themes and len(themes) > 1:
                additional_themes = themes[1:]
                joined_additional = "、".join(additional_themes)
                paragraphs.append(
                    f"また、{joined_additional}分野でも具体的な活用事例や技術進展が報告されています。"
                )
        else:
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
        articles: List[ProcessedArticle], 
        edition: str
    ) -> Dict[str, Any]:
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
        
        prompt = f"""あなたはプロのニュースライターです。以下のAIニュース要約を基に、ニュースレターの導入文を生成してください。

【本日の主要記事】
{context}

【導入文の要件】
- 3つの段落で構成
- 各段落は1文で、60-150文字
- 第1段落: 最も重要なニュースを具体的に紹介
- 第2段落: 他の重要な動向や関連する話題
- 第3段落: 全体的な業界への影響や今後の展望

【重要な注意事項】
- 各文は必ず「です」「ます」「ました」「ています」で終わること
- 「〜が。」のような不完全な文は作らない
- 具体的な企業名や技術名を含める

【回答形式】
以下の形式で3つの段落を生成してください：

段落1: [第1文をここに記載]
段落2: [第2文をここに記載]
段落3: [第3文をここに記載]

JSONではなく、上記の形式で日本語の文章を直接生成してください。"""
        
        return prompt
    
    def _validate_lead_paragraph(self, paragraph: str) -> Tuple[bool, str]:
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
        if re.search(r'(されています|しています).*?(と発表|と報告|と説明)', paragraph):
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
                                expansion = "今後もAI技術の進歩と企業活用が加速していくことが予想されます。"
                            else:
                                expansion = "この分野での更なる技術革新が期待されています。"
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
                                    "この分野での更なる技術革新が期待されています。"
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
        
        # Remove incomplete sentence patterns
        para = re.sub(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)が。\s*', '', para)
        para = re.sub(r'([A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)は。\s*', '', para)
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
    
    def _truncate_paragraphs_to_limit(self, paragraphs: List[str], char_limit: int) -> List[str]:
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
    
    def _generate_basic_markdown(self, context: Dict[str, Any]) -> str:
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
        articles: List[ProcessedArticle]
    ) -> str:
        """Generate HTML preview for newsletter content."""
        # This method should be implemented to generate HTML preview
        # For example, you can use a library like BeautifulSoup to parse the Markdown
        # and convert it to HTML for preview purposes.
        pass
    
    def _extract_article_highlights(self, articles: List[ProcessedArticle]) -> List[str]:
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
    
    def _prioritize_articles_for_highlights(self, articles: List[ProcessedArticle]) -> List[ProcessedArticle]:
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
        summary_points: List[str], 
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
                action = re.sub(rf'{re.escape(company)}(?:が|は|の)?', '', action).strip()
            
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
    
    def _extract_companies(self, text: str, title: str) -> List[str]:
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
    
    def _extract_products(self, text: str, title: str) -> List[str]:
        """Extract product/technology names."""
        products = []
        combined_text = text + " " + title
        
        product_patterns = [
            r'(GPT-\d+(?:\.\d+)?|ChatGPT|GPT)',
            r'(Claude(?:-\d+)?)',
            r'(Gemini(?:\s+\d+\.\d+)?)',
            r'(LLaMA|Llama)',
            r'(DALL-E|DALL·E)',
            r'(Midjourney|Stable Diffusion)',
            r'(TensorFlow|PyTorch)',
            r'(Transformer|BERT|T5)'
        ]
        
        for pattern in product_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            products.extend(matches)
            
        return list(dict.fromkeys(products))
    
    def _extract_key_actions(self, text: str) -> List[str]:
        """Extract key business actions."""
        actions = []
        
        action_patterns = [
            # Extract action part after company name, avoiding full sentence capture
            r'(?:が|は)([^。]*?(?:発表|リリース|公開|開始|導入|実装|展開|提供))',
            r'(?:が|は)([^。]*?(?:向上|改善|強化|拡大|増大|倍増))',
            r'(?:が|は)([^。]*?(?:値下げ|価格.*?削減|コスト.*?削減))',
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
    
    def _extract_metrics(self, text: str) -> List[str]:
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
    
    def _extract_contextual_impact(self, summary_points: List[str], title: str) -> str:
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
    
    def _create_thematic_highlights(self, articles: List[ProcessedArticle]) -> List[str]:
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
    
    def _extract_key_themes(self, articles: List[ProcessedArticle]) -> List[str]:
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
    
    def _generate_specific_theme_title(self, themes: List[str], articles: List[ProcessedArticle]) -> Optional[str]:
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
    
    def _generate_fallback_specific_title(self, articles: List[ProcessedArticle]) -> str:
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

    def _generate_lead_title_from_articles(self, articles: List[ProcessedArticle], edition: str) -> str:
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
        
        # For TOC, we want to show meaningful content but avoid extremely long entries
        max_toc_length = 80  # Optimal length for TOC entries
        
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
            if quote_end <= max_toc_length + 10:  # Allow slight overflow for quotes
                # Find a good cut point after the quote
                cut_text = text[:quote_end]
                
                # Look for natural break points after the quote
                remaining = text[quote_end:]
                for break_char in ['を', 'が', 'に', 'で', 'と']:
                    break_pos = remaining.find(break_char)
                    if break_pos != -1 and break_pos < 10:
                        cut_text = text[:quote_end + break_pos + 1]
                        if len(cut_text) <= max_toc_length + 5:
                            return cut_text.rstrip() + '…'
                        break
                
                # If we can fit the quote, use it
                if len(cut_text) <= max_toc_length + 10:
                    return cut_text.rstrip() + '…'
        
        # For very long text, try to find natural breaking points
        if len(text) > 120:
            # Look for early natural breaks
            early_break_patterns = [
                (r'において', '、'),
                (r'について', '、'), 
                (r'に関して', '、'),
                (r'による', ''),
                (r'のための', ''),
                (r'を通じて', ''),
                (r'における', ''),
            ]
            
            for keyword, suffix in early_break_patterns:
                pattern = keyword + suffix
                match_pos = text.find(pattern)
                if match_pos != -1 and 20 <= match_pos <= 60:
                    # Cut after the pattern
                    cut_pos = match_pos + len(pattern)
                    return text[:cut_pos].rstrip() + '…'
        
        # Look for good breaking points within the limit
        snippet = text[:max_toc_length]
        
        # Priority: complete phrases or natural boundaries
        # 1. Try to break at punctuation
        for punct in ['、', '。', '・']:
            last_punct = snippet.rfind(punct)
            if last_punct > max_toc_length * 0.6:  # At least 60% of target length
                return snippet[:last_punct + 1].rstrip()
        
        # 2. Try to break after particles (but not certain ones that need completion)
        safe_particles = ['で', 'から', 'まで', 'より', 'にて']
        for particle in safe_particles:
            last_pos = snippet.rfind(particle)
            if last_pos > max_toc_length * 0.6:
                return snippet[:last_pos + len(particle)].rstrip() + '…'
        
        # 3. Avoid breaking in the middle of important terms
        # Find the last "safe" position (not in the middle of a word/term)
        safe_pos = max_toc_length
        while safe_pos > max_toc_length * 0.7:
            char = text[safe_pos - 1] if safe_pos > 0 else ''
            next_char = text[safe_pos] if safe_pos < len(text) else ''
            
            # Don't break in the middle of:
            # - ASCII words
            # - Katakana words  
            # - Numbers
            if (char.isascii() and char.isalnum() and next_char.isascii() and next_char.isalnum()) or \
               (ord('ァ') <= ord(char) <= ord('ヶ') and ord('ァ') <= ord(next_char) <= ord('ヶ')) or \
               (char.isdigit() and next_char.isdigit()):
                safe_pos -= 1
                continue
            else:
                break
        
        # Use the safe position
        result = text[:safe_pos].rstrip()
        
        # Clean up any trailing particles that make it incomplete
        if result.endswith(('は', 'が', 'を', 'に', 'へ', 'と')):
            result = result[:-1].rstrip()
        
        # Add ellipsis if we actually truncated
        if len(result) < len(text):
            result += '…'
        
        return result
    
    async def _generate_article_title(self, article: ProcessedArticle) -> str:
        """
        Generate Japanese title using LLM first, fallback to template-based generation.
        
        Args:
            article: Processed article
            
        Returns:
            Generated Japanese title
        """
        # First try LLM-based generation if available
        if HAS_LLM_ROUTER and self.llm_router:
            try:
                # LLM generates a base summary sentence
                base_summary = await self.llm_router.generate_japanese_title(article)
                
                if base_summary:
                    logger.debug(f"LLM generated base summary for title: {base_summary}")
                    # Programmatically format the headline
                    return self._format_headline_from_summary(base_summary)
            except Exception as e:
                logger.warning(f"LLM title generation failed, falling back: {e}")
        
        # Fallback to using the first summary point
        return self._generate_improved_fallback_title(article)
    
    def _format_headline_from_summary(self, summary_sentence: str) -> str:
        """Formats a summary sentence into a structured headline."""
        
        # Extract a key entity to make the title more specific
        entity_match = re.search(r'「([^」]+)」|\b([A-Z][a-zA-Z0-9]+)\b', summary_sentence)
        entity = ""
        if entity_match:
            entity = entity_match.group(1) or entity_match.group(2)
        
        # Truncate the summary sentence to keep it concise
        truncated_summary = ensure_sentence_completeness(summary_sentence, 60)
        
        if entity and entity not in truncated_summary:
             return f"{entity}、{truncated_summary}"
        else:
            return truncated_summary

    def _generate_improved_fallback_title(self, article: ProcessedArticle) -> str:
        """
        Generate a fallback title by creating a concise summary from the first summary point.
        This provides a safe and informative fallback.
        """
        try:
            summary_points = article.summarized_article.summary.summary_points
            if summary_points and summary_points[0]:
                # Use the first bullet point to create a concise title
                first_point = summary_points[0]
                
                # Extract key entities and actions
                # Pattern 1: Extract company/organization names
                company_match = re.search(
                    r'(OpenAI|Google|Meta|Microsoft|Anthropic|Apple|Amazon|NVIDIA|DeepMind|'
                    r'[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*?)(?:社|が|は|の|、)',
                    first_point
                )
                company = company_match.group(1) if company_match else None
                
                # Pattern 2: Extract key actions/technologies
                action_patterns = [
                    (r'(\d+名?の?(?:AI)?研究者)', '研究者'),
                    (r'(トップ.*?研究者)', '人材'),
                    (r'(新機能|新サービス|新技術)', 'リリース'),
                    (r'(発表|公開|開始|導入|獲得|雇用)', None),
                    (r'(ChatGPT|Claude|Gemini|GPT-\d+)', 'AI'),
                    (r'(Deep Research|RAG|LLM)', '技術'),
                ]
                
                key_action = None
                action_type = None
                for pattern, type_hint in action_patterns:
                    match = re.search(pattern, first_point)
                    if match:
                        key_action = match.group(1)
                        action_type = type_hint
                        break
                
                # Build concise title
                if company and key_action:
                    if '研究者' in key_action:
                        # Special handling for researcher hiring
                        return f"{company}が{key_action}を獲得"
                    elif action_type:
                        return f"{company}の{action_type}{key_action}"
                    else:
                        return f"{company}が{key_action}"
                elif company:
                    return f"{company}がAI技術を強化"
                elif key_action:
                    # PRD準拠: 完全な文章でタイトル生成
                    if '発表' in key_action:
                        return f"AI業界で新技術発表、{key_action}に注目"
                    elif '導入' in key_action:
                        return f"AI業界で新システム導入、{key_action}が進行"
                    else:
                        return f"AI業界で{key_action}の動きが活発化"
                else:
                    # PRD準拠: 不完全タイトル禁止、要約ポイントから完全な文章生成
                    clean_point = re.sub(r'^(また、|さらに、|一方、)', '', first_point)
                    
                    # 主語と述語を抽出して完全な文章に
                    subject_match = re.search(r'([^、。]{1,15})(が|は|の)', clean_point)
                    verb_match = re.search(r'(発表|開始|導入|強化|獲得|実現|提供|開発)', clean_point)
                    
                    if subject_match and verb_match:
                        subject = subject_match.group(1)
                        verb = verb_match.group(1)
                        # 助詞の重複を避けて自然な文章に
                        if subject.endswith('が'):
                            subject = subject[:-1]
                        elif subject.endswith('は'):
                            subject = subject[:-1]
                        return f"{subject}、新技術を{verb}でAI業界が進展"
                    else:
                        # 最終フォールバック：要約ポイントの最初の文を使用
                        first_sentence = re.split(r'[。、]', clean_point)[0]
                        if len(first_sentence) > 10 and len(first_sentence) < 50:
                            return first_sentence + "を発表"
                        else:
                            return "AI技術の重要な進展が報告"

            # If no summary points, create a title from the content
            content_summary = article.summarized_article.filtered_article.raw_article.content
            if content_summary and len(content_summary) > 20:
                # Sanitize content to avoid template injection
                sanitized_content = content_summary.replace("{", "").replace("}", "")
                return f"【AI関連】{sanitized_content[:30]}..."
            
            # If content is also unavailable, use the original title but shortened
            original_title = article.summarized_article.filtered_article.raw_article.title
            if original_title:
                return self._intelligent_truncate(original_title, max_chars=50)
            
            return "AI技術の最新動向"
            
        except Exception as e:
            logger.warning(f"Fallback title generation failed: {e}")
            # Ultimate fallback for unexpected errors
            return "AI関連ニュース"

    def _clean_llm_generated_title(self, title: str) -> str:
        """Clean up common LLM title generation artifacts."""
        if not title or not isinstance(title, str):
            return ""
        
        # Remove duplicate phrases first
        title = re.sub(r'(.+?)(と発表|と報告|と述べ|と語っ|と表明)(.*?)\2', r'\1\2\3', title)
        
        # Remove verb endings like "〜と報じられました" or "〜と発表しました"
        # to ensure the title is a proper headline (体言止め).
        verb_endings_pattern = r"(?:と報じられました|と発表しました|と述べました|と語りました|と表明しました|と明らかにしました|氏は|氏は、|を発表|を報告)$"
        cleaned_title = re.sub(verb_endings_pattern, '', title).strip()
        
        # Remove incomplete sentence patterns
        incomplete_patterns = r"(?:について|に関して|において|に対して|をめぐって)$"
        cleaned_title = re.sub(incomplete_patterns, '', cleaned_title).strip()
        
        # Additional cleanup for cases where a comma is left at the end
        if cleaned_title.endswith(('、', ',', '。', '：', ':')):
            cleaned_title = cleaned_title[:-1].strip()
        
        # Remove trailing particles that make titles incomplete
        if cleaned_title.endswith(('が', 'を', 'に', 'は', 'で', 'と')):
            cleaned_title = cleaned_title[:-1].strip()
            
        return cleaned_title

    def _is_highly_generic_title(self, title: str) -> bool:
        """Check if the title is too generic or low-quality."""
        # Only reject extremely generic titles
        highly_generic_patterns = [
            r'^AI関連ニュース$',
            r'^最新AI動向$',
            r'^技術ニュース$',
            r'^業界動向$',
            r'^最新情報$',
            r'^.*について$',
            r'^.*に関して$'
        ]
         
        return any(re.search(pattern, title, re.IGNORECASE) for pattern in highly_generic_patterns)

    def _shorten_summary_points(self, summary_points: List[str]) -> List[str]:
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
                    r'([A-Za-z][A-Za-z0-9]*(?:\\s+[A-Za-z][A-Za-z0-9]*)*?)(?:社|が|は|の).{0,20}?(発表|開始|提供|リリース|公開)',
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
                    r'(AGI|ChatGPT|Claude|Gemini|GPT-\\d+|Llama|LLaMA)(?:の|を|が)?(.{0,15}?)(?:発表|リリース|公開|開発)',
                    r'(?:AI|人工知能|機械学習)(?:の|を|が)?(.{0,15}?)(?:発表|開発|導入|活用)',
                    r'(量子|法的|医療|自動化)(?:の|を|が)?(.{0,10}?)(?:技術|システム|プラットフォーム|ソリューション)',
                    r'(著作権|訴訟|契約|投資|買収|提携)(?:の|を|が)?(.{0,10}?)(?:問題|合意|発表)'
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
                title_candidate = re.sub(r'しましたを(発表|開始|提供)', r'を\\1', title_candidate)
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
                for eng, jp in term_mappings.items():
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
    
    def _extract_key_topic_from_summary(self, summary_point: str) -> Optional[str]:
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
                topic = re.sub(r'^(新しい|最新の|次世代の)', '', topic)
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

    def _cleanup_summary_points(self, summary_points: List[str]) -> List[str]:
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
        articles: List[ProcessedArticle]
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

    async def _consolidate_multi_source_articles(self, articles: List[ProcessedArticle]) -> List[ProcessedArticle]:
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

    # ------------------------------------------------------------------
    # Quality filtering & deduplication helpers (re-added)
    # ------------------------------------------------------------------

    def _filter_articles_by_quality(
        self,
        articles: List[ProcessedArticle],
        quality_threshold: float = 0.35,
    ) -> List[ProcessedArticle]:
        """Filter articles whose AI 関連度 (relevance score) >= threshold.

        If an article is missing `ai_relevance_score`, it is kept to avoid
        accidental loss of content during early development phases.
        The resulting list is sorted by relevance score (desc).
        """

        if not articles:
            return []

        def _score(art: ProcessedArticle) -> float:
            try:
                return art.summarized_article.filtered_article.ai_relevance_score
            except Exception:
                return 0.5  # neutral default

        filtered = [a for a in articles if _score(a) >= quality_threshold]

        # Always ensure at least one article remains to avoid empty newsletter
        if not filtered:
            filtered = articles[:]

        return sorted(filtered, key=_score, reverse=True)

    def _deduplicate_articles(self, articles: List[ProcessedArticle]) -> List[ProcessedArticle]:
        """Remove articles flagged as duplicates or with identical raw IDs."""

        unique_articles = []
        seen_ids = set()

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
                continue

            if raw_id and raw_id in seen_ids:
                continue

            unique_articles.append(art)
            if raw_id:
                seen_ids.add(raw_id)

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
    articles: List[ProcessedArticle],
    edition: str = "daily",
    processing_summary: Dict = None,
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

def ensure_sentence_completeness(text: str, max_chars: int = 60) -> str:
    """
    日本語に最適化された文境界検出による自然な切断処理。
    目次の可読性を最大化するため、適切な切断点を優先度順に探索。
    """

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
            'patterns': [r'(?=また|さらに|一方|なお|ただし|しかし|そして)'],
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