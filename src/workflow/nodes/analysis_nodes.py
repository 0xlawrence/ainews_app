"""
Analysis workflow nodes for duplicate checking, clustering, and context analysis.

This module contains the analysis phase nodes of the newsletter workflow:
- Duplicate detection and consolidation
- Topic clustering with multi-source priority
- Context analysis for UPDATE/KEEP decisions
- Article relationship tracking
"""

import asyncio
import time
from typing import Optional, Tuple, List, Union

from src.config.settings import get_settings
from src.deduplication.duplicate_checker import BasicDuplicateChecker, consolidate_similar_articles
from src.models.schemas import (
    ProcessedArticle,
    ProcessingLog,
    SummarizedArticle,
    Citation,
    SummaryOutput
)
from src.utils.context_analyzer import ContextAnalyzer
from src.utils.embedding_manager import EmbeddingManager
from src.utils.logger import setup_logging
from src.utils.topic_clustering import cluster_articles_with_multi_source_priority
from src.utils.citation_generator import CitationGenerator

logger = setup_logging()


class AnalysisNodes:
    """Analysis workflow nodes for duplicate checking and clustering."""
    
    def __init__(self, llm_router):
        """Initialize analysis nodes with dependencies."""
        from src.config.settings import get_settings
        self.settings = get_settings()
        self.llm_router = llm_router
        self.duplicate_checker = BasicDuplicateChecker()
        self.embedding_manager = None  # Initialized lazily
        self.context_analyzer = None   # Initialized lazily
    
    async def check_duplicates_node(self, state: dict) -> dict:
        """Intelligent duplicate consolidation and context analysis (Enhanced Phase 2)."""
        
        logger.info("Starting intelligent duplicate consolidation and context analysis")
        start_time = time.time()
        
        try:
            config = state["config"]
            summarized_articles = state["summarized_articles"]
            
            if not summarized_articles:
                logger.warning("No summarized articles to consolidate")
                return {
                    **state,
                    "deduplicated_articles": [],
                    "status": "no_articles_to_consolidate"
                }
            
            # Phase 1: Intelligent duplicate consolidation
            consolidated_articles = await self._consolidate_duplicates(summarized_articles)
            
            # Phase 2: Context analysis and article processing
            deduplicated_articles, duplicate_count, update_count = await self._process_articles_with_context(
                consolidated_articles
            )
            
            # Phase 2.5: Bulk save all articles to database (Phase 3.2d optimization)
            await self._bulk_save_articles_to_database(deduplicated_articles)
            
            # Phase 3: Log results
            processing_time = time.time() - start_time
            log_entry = self._log_duplicate_processing_results(
                config, summarized_articles, deduplicated_articles,
                duplicate_count, update_count, processing_time
            )
            
            return {
                **state,
                "deduplicated_articles": deduplicated_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "duplicates_and_context_checked"
            }
            
        except Exception as e:
            logger.error("Check duplicates and context node failed", error=str(e))
            
            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="check_duplicates_context",
                event_type="error",
                message=f"Failed to check duplicates and context: {str(e)}",
                duration_seconds=time.time() - start_time
            )
            
            return {
                **state,
                "deduplicated_articles": [],
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "deduplication_context_failed"
            }
    
    async def cluster_topics_node(self, state: dict) -> dict:
        """Cluster articles by topic with Phase 3 advanced clustering."""
        
        logger.info("Starting advanced topic clustering node")
        start_time = time.time()
        
        try:
            config = state["config"]
            deduplicated_articles = state["deduplicated_articles"]
            
            if not deduplicated_articles:
                logger.warning("No deduplicated articles to cluster")
                return {
                    **state,
                    "clustered_articles": [],
                    "status": "no_articles_to_cluster"
                }
            
            # Phase 3: Multi-source topic prioritization with clustering
            clustered_articles = await cluster_articles_with_multi_source_priority(
                articles=deduplicated_articles,
                max_articles_target=self.settings.workflow.max_newsletter_articles,
            )
            
            # Generate proper citations for all clustered articles
            logger.info("Generating citations for clustered articles")
            citation_start_time = time.time()
            
            # Reset URL tracking for newsletter-wide citation deduplication
            citation_deduplicator = CitationGenerator()
            citation_deduplicator.reset_url_tracking()
            logger.info("Citation URL tracking reset for new newsletter generation")
            
            # Generate citations for each article using cluster information
            citation_generator = CitationGenerator()
            
            for i, article in enumerate(clustered_articles):
                try:
                    # Use other articles in cluster as citation sources
                    cluster_articles = [other for j, other in enumerate(clustered_articles) if i != j]
                    
                    citations = await citation_generator.generate_citations(
                        article=article,
                        cluster_articles=cluster_articles[:self.settings.workflow.max_cluster_sources],
                        max_citations=self.settings.workflow.max_citations_per_article
                    )
                    
                    article.citations = citations
                    
                    logger.info(
                        f"Generated {len(citations)} cluster-based citations for article",
                        article_id=article.summarized_article.filtered_article.raw_article.id,
                        cluster_size=len(cluster_articles)
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Failed to generate cluster citations for article {i}: {e}",
                        article_id=getattr(article.summarized_article.filtered_article.raw_article, 'id', 'unknown')
                    )
                    article.citations = []
            
            citation_time = time.time() - citation_start_time
            logger.info(f"Citation generation completed in {citation_time:.2f}s")
            
            # Validate article count and apply PRD compliance if needed
            max_newsletter_articles = min(config.max_items, self.settings.workflow.max_newsletter_articles)
            
            if len(clustered_articles) > max_newsletter_articles:
                clustered_articles = self._trim_articles_by_relevance(clustered_articles, max_newsletter_articles)
            
            # PRD F-5: Ensure minimum articles
            if len(clustered_articles) < self.settings.workflow.min_newsletter_articles and len(deduplicated_articles) > len(clustered_articles):
                clustered_articles = await self._ensure_minimum_articles(
                    clustered_articles, deduplicated_articles, target_count=self.settings.workflow.min_newsletter_articles
                )
            
            # Validate PRD compliance
            compliance_result = self._validate_prd_compliance(clustered_articles)
            
            # Save cluster relationships to database
            await self._save_cluster_relationships(clustered_articles)
            
            processing_time = time.time() - start_time
            
            # Log processing
            log_entry = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="cluster_topics_advanced",
                event_type="info",
                message=f"Advanced clustering completed with {len(clustered_articles)} articles",
                data={
                    "input_articles": len(deduplicated_articles),
                    "output_articles": len(clustered_articles),
                    "max_newsletter_articles": max_newsletter_articles,
                    "citations_generated": sum(len(a.citations) for a in clustered_articles),
                    "validation_enabled": True
                },
                duration_seconds=processing_time
            )
            
            return {
                **state,
                "clustered_articles": clustered_articles,
                "processing_logs": state["processing_logs"] + [log_entry],
                "status": "topics_clustered_advanced"
            }
            
        except Exception as e:
            logger.error("Advanced topic clustering failed", error=str(e))
            
            # Fallback to simple clustering
            return await self._fallback_simple_clustering(state, deduplicated_articles, start_time, str(e))
    
    # Private helper methods
    
    async def _consolidate_duplicates(self, summarized_articles: List[SummarizedArticle]) -> List[SummarizedArticle]:
        """Phase 1: Intelligent duplicate consolidation."""
        logger.info("Phase 1: Intelligent duplicate consolidation")
        
        settings = get_settings()
        consolidation_threshold = settings.embedding.duplicate_similarity_threshold
        adjusted_threshold = max(
            settings.embedding.minimum_consolidation_threshold,
            consolidation_threshold - settings.embedding.consolidation_threshold_adjustment
        )
        
        consolidated_articles = consolidate_similar_articles(
            articles=summarized_articles,
            jaccard_threshold=adjusted_threshold,
            sequence_threshold=adjusted_threshold,
            consolidation_mode=True
        )
        
        consolidation_stats = {
            "input_articles": len(summarized_articles),
            "output_articles": len(consolidated_articles),
            "articles_consolidated": len(summarized_articles) - len(consolidated_articles)
        }
        
        logger.info("Duplicate consolidation completed", **consolidation_stats)
        return consolidated_articles
    
    async def _process_articles_with_context(self, consolidated_articles: List[SummarizedArticle]) -> Tuple[List[ProcessedArticle], int, int]:
        """Phase 2: Context analysis and article processing."""
        logger.info("Phase 2: Context analysis and article processing")
        
        # Initialize context analyzer if needed
        if self.context_analyzer is None:
            if self.embedding_manager is None:
                self.embedding_manager = EmbeddingManager()
            
            self.context_analyzer = ContextAnalyzer(
                embedding_manager=self.embedding_manager,
                llm_router=self.llm_router
            )
        
        deduplicated_articles = []
        duplicate_count = 0
        update_count = 0
        
        for article in consolidated_articles:
            try:
                processed_article, is_duplicate, is_update = await self._process_single_article_for_duplicates(
                    article, deduplicated_articles
                )
                
                if processed_article:
                    deduplicated_articles.append(processed_article)
                    if is_update:
                        update_count += 1
                elif is_duplicate:
                    duplicate_count += 1
                    
            except Exception as e:
                logger.error(
                    "Error processing article for duplicates/context",
                    article_id=article.filtered_article.raw_article.id,
                    error=str(e)
                )
                continue
        
        return deduplicated_articles, duplicate_count, update_count
    
    async def _process_single_article_for_duplicates(self, article: SummarizedArticle, existing_articles: List[ProcessedArticle]) -> Tuple[Optional[ProcessedArticle], bool, bool]:
        """Process a single article for duplicates and context analysis."""
        # Check for duplicates using BasicDuplicateChecker
        duplicate_result = self.duplicate_checker.check_duplicate(
            current_article=article,
            past_articles=[p.summarized_article for p in existing_articles]
        )
        
        if duplicate_result.is_duplicate:
            logger.info(
                "Duplicate article filtered out by basic checker",
                article_id=article.filtered_article.raw_article.id,
                similarity_score=duplicate_result.similarity_score
            )
            return None, True, False
        
        # Context analysis for UPDATE detection
        context_analysis = await self._analyze_context_for_article(article)
        is_update = False
        
        if context_analysis and context_analysis.decision == "UPDATE" and context_analysis.references:
            is_update = await self._apply_context_analysis_to_article(article, context_analysis)
            logger.info(
                "Article marked as UPDATE by context analysis",
                article_id=article.filtered_article.raw_article.id,
                references_count=len(context_analysis.references)
            )
        
        # Create processed article
        processed_article = ProcessedArticle(
            summarized_article=article,
            duplicate_check=duplicate_result,
            context_analysis=context_analysis,
            final_summary=' '.join(article.summary.summary_points),
            japanese_title=None,  # Generated later
            citations=[],  # Generated later
            is_update=is_update
        )
        
        # Individual storage moved to bulk processing - store context for bulk save
        processed_article._bulk_context_analysis = context_analysis
        processed_article._bulk_is_update = is_update
        
        return processed_article, False, is_update
    
    async def _analyze_context_for_article(self, article: SummarizedArticle):
        """Analyze context for a single article."""
        if not self.context_analyzer:
            return None
        
        try:
            settings = get_settings()
            
            context_analysis = await self.context_analyzer.analyze_context(
                current_article=article,
                max_similar_articles=5,
                similarity_threshold=settings.embedding.context_similarity_threshold
            )
            
            if context_analysis:
                logger.info(
                    f"Context analysis completed for article {article.filtered_article.raw_article.id}: "
                    f"decision={context_analysis.decision}, "
                    f"references={len(context_analysis.references) if context_analysis.references else 0}"
                )
            
            return context_analysis
        except Exception as e:
            logger.warning(
                "Context analysis failed, proceeding with standard processing",
                article_id=article.filtered_article.raw_article.id,
                error=str(e)
            )
            return None
    
    async def _apply_context_analysis_to_article(self, article: SummarizedArticle, context_analysis) -> bool:
        """Apply context analysis results to an article."""
        is_update = False
        
        if context_analysis.decision == "UPDATE":
            is_update = True
            
            logger.info(
                "Marked article as UPDATE in workflow - emoji handling delegated to title generation",
                article_id=article.filtered_article.raw_article.id
            )
            
            # Generate context-aware summary if available
            if context_analysis.contextual_summary:
                enhanced_summary_points = await self._generate_contextual_update_summary(
                    article, context_analysis
                )
                
                if enhanced_summary_points:
                    original_summary = article.summary
                    
                    enhanced_summary = SummaryOutput(
                        summary_points=enhanced_summary_points,
                        confidence_score=min(original_summary.confidence_score + 0.15, 1.0),
                        source_reliability=original_summary.source_reliability,
                        model_used=original_summary.model_used + "_contextual",
                        fallback_used=original_summary.fallback_used,
                        total_tokens=original_summary.total_tokens,
                        processing_time_seconds=original_summary.processing_time_seconds
                    )
                    
                    article.summary = enhanced_summary
                    
                    logger.info(
                        "Enhanced UPDATE article with past context",
                        article_id=article.filtered_article.raw_article.id,
                        context_refs=len(context_analysis.references)
                    )
        
        elif context_analysis.decision == "KEEP" and context_analysis.references:
            # Add context metadata
            if not hasattr(article, 'context_metadata'):
                article.context_metadata = {}
            
            article.context_metadata.update({
                'related_articles': context_analysis.references[:3],
                'context_reasoning': context_analysis.reasoning,
                'similarity_score': context_analysis.similarity_score
            })
            
            logger.info(
                "Added context metadata to KEEP article",
                article_id=article.filtered_article.raw_article.id,
                related_count=len(context_analysis.references)
            )
        
        return is_update
    
    async def _generate_contextual_update_summary(self, article: SummarizedArticle, context_analysis) -> Optional[List[str]]:
        """Generate enhanced summary for UPDATE articles incorporating past context."""
        try:
            current_title = article.filtered_article.raw_article.title
            current_points = article.summary.summary_points
            
            # Format references
            references_text = ""
            past_links_text = ""
            if context_analysis.references:
                references_text = "\n".join([
                    f"- {ref}" for ref in context_analysis.references[:3]
                ])
                
                past_links_text = "\n\n**関連する過去記事:**\n"
                for i, ref in enumerate(context_analysis.references[:2], 1):
                    ref_title = ref.split(' - ')[0] if ' - ' in ref else ref[:50]
                    past_links_text += f"- [{ref_title}](#past-article-{i})\n"
            
            # Create context-aware prompt
            prompt = f"""以下の続報記事について、過去の関連記事の文脈を踏まえた包括的な日本語要約を生成してください。

【今回の記事】
タイトル: {current_title}
要点: {' / '.join(current_points)}

【過去の関連記事】
{references_text}

【文脈分析】
{context_analysis.reasoning}

【要件】
- 必ず4項目の箇条書きで作成
- 各項目150-200文字程度
- 過去の経緯を自然に織り込む
- 今回の新しい展開を明確に示す
- 「続報」「UPDATE」等の文言は使わない
- 具体的な変化や進展を強調

【出力形式】
- 過去の経緯を踏まえた現在の状況
- 今回発表された新しい要素や変化
- これまでとの比較や違い
- 今後への影響や展望{past_links_text}"""
            
            # Generate enhanced summary using LLM
            response = await self.llm_router.generate_simple_text(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            if not response:
                return None
            
            # Parse response into bullet points
            lines = response.strip().split('\n')
            summary_points = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('- ') or line.startswith('• '):
                    point = line[2:].strip()
                    if 100 <= len(point) <= 250:
                        summary_points.append(point)
            
            # Validate output
            if len(summary_points) >= 3:
                final_points = summary_points[:4]
                if past_links_text and final_points:
                    final_points[-1] += past_links_text.replace('\n\n', ' ')
                
                logger.info(
                    "Generated contextual update summary with past links",
                    article_id=article.filtered_article.raw_article.id,
                    enhanced_points=len(final_points),
                    references_used=len(context_analysis.references),
                    past_links_added=bool(past_links_text)
                )
                return final_points
            
            return None
            
        except Exception as e:
            logger.warning(
                "Failed to generate contextual update summary",
                article_id=article.filtered_article.raw_article.id,
                error=str(e)
            )
            return None
    
    async def _save_article_data_to_storage(self, article: SummarizedArticle, processed_article: ProcessedArticle, is_update: bool, context_analysis):
        """Save article data to embedding index and Supabase."""
        # Add to embedding index for future context analysis
        try:
            if self.embedding_manager:
                await self.embedding_manager.add_article(article, save_immediately=False)
        except Exception as embedding_error:
            logger.warning(
                "Failed to add article to embedding index",
                article_id=article.filtered_article.raw_article.id,
                error=str(embedding_error)
            )
        
        # Save to Supabase contextual_articles
        await self._save_article_to_supabase(article, processed_article, is_update, context_analysis)
    
    async def _save_article_to_supabase(self, article: SummarizedArticle, processed_article: ProcessedArticle, is_update: bool, context_analysis):
        """Save article and relationships to Supabase."""
        try:
            from src.utils.supabase_client import save_contextual_article
            
            if not self.embedding_manager:
                return
            
            # Generate embedding for Supabase
            embedding_text = f"{article.filtered_article.raw_article.title}\n{article.filtered_article.raw_article.content}\n" + "\n".join(article.summary.summary_points)
            embedding_vector = await self.embedding_manager.generate_embedding(embedding_text)
            
            # Save contextual article
            article_uuid = await save_contextual_article(
                article=processed_article,
                embedding=embedding_vector.tolist() if embedding_vector is not None else None,
                topic_cluster=None  # Will be set in clustering phase
            )
            
            # Save relationships if this is an update
            if is_update and context_analysis and context_analysis.references and article_uuid:
                await self._save_supabase_relationships(article_uuid, context_analysis)
            
            logger.info(
                "Saved article to Supabase",
                article_id=article.filtered_article.raw_article.id,
                article_uuid=article_uuid,
                is_update=is_update
            )
            
        except Exception as supabase_error:
            logger.warning(
                "Failed to save article to Supabase",
                article_id=article.filtered_article.raw_article.id,
                error=str(supabase_error)
            )
    
    async def _save_supabase_relationships(self, article_uuid: str, context_analysis):
        """Save article relationships to Supabase (F-17 implementation)."""
        for ref_article_id in context_analysis.references[:3]:
            try:
                from src.utils.supabase_client import get_supabase_client, save_article_relationship
                client = await get_supabase_client()
                if client.is_available():
                    ref_result = client.client.table("contextual_articles").select("id").eq(
                        "article_id", ref_article_id
                    ).execute()
                    
                    if ref_result.data:
                        ref_uuid = ref_result.data[0]["id"]
                        
                        # Determine relationship type
                        relationship_type = "related"
                        if context_analysis.decision == "UPDATE":
                            relationship_type = "update"
                        elif context_analysis.similarity_score > 0.8:
                            relationship_type = "sequel"
                        
                        await save_article_relationship(
                            parent_article_uuid=ref_uuid,
                            child_article_uuid=article_uuid,
                            relationship_type=relationship_type,
                            similarity_score=context_analysis.similarity_score,
                            reasoning=f"Context analysis: {context_analysis.reasoning}"
                        )
                        
                        logger.info(
                            "F-17: Saved article relationship",
                            parent_article_id=ref_article_id,
                            child_article_uuid=article_uuid,
                            relationship_type=relationship_type,
                            similarity_score=context_analysis.similarity_score
                        )
            except Exception as e:
                logger.warning(f"Failed to save relationship for {ref_article_id}: {e}")
    
    async def _save_cluster_relationships(self, clustered_articles: List[ProcessedArticle]):
        """Save topic cluster relationships to Supabase using bulk operations (Phase 3.2d optimization)."""
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            
            if not settings.processing.enable_db_bulk_operations:
                logger.info("Database bulk operations disabled for cluster relationships, using individual processing")
                await self._save_cluster_relationships_individually(clustered_articles)
                return
            
            from src.utils.supabase_client import get_supabase_client, save_article_relationships_bulk
            client = await get_supabase_client()
            
            if not client.is_available():
                return
            
            # Group articles by cluster_id
            clusters = {}
            for article in clustered_articles:
                cluster_id = getattr(article, 'cluster_id', None)
                if cluster_id is not None:
                    if cluster_id not in clusters:
                        clusters[cluster_id] = []
                    clusters[cluster_id].append(article)
            
            # Prepare all cluster relationships for bulk insertion
            all_relationships_data = []
            
            # For each cluster with multiple articles, prepare relationship data
            for cluster_id, articles in clusters.items():
                if len(articles) < 2:
                    continue
                
                # Get article UUIDs from Supabase (batch query for efficiency)
                article_ids = [a.summarized_article.filtered_article.raw_article.id for a in articles]
                
                try:
                    # Single query to get all UUIDs for this cluster
                    result = client.client.table("contextual_articles").select("id, article_id").in_(
                        "article_id", article_ids
                    ).execute()
                    
                    # Create mapping from article_id to UUID
                    article_uuids = {}
                    if result.data:
                        for record in result.data:
                            article_uuids[record["article_id"]] = record["id"]
                    
                    # Generate all pairwise relationships for this cluster
                    article_list = list(article_uuids.items())
                    for i, (article_id_1, uuid_1) in enumerate(article_list):
                        for j, (article_id_2, uuid_2) in enumerate(article_list[i+1:], i+1):
                            relationship_data = {
                                "parent_article_id": uuid_1,
                                "child_article_id": uuid_2,
                                "relationship_type": "related",
                                "similarity_score": 0.75,  # Default cluster similarity
                                "reasoning": f"Topic cluster {cluster_id}: Articles grouped together by semantic similarity"
                            }
                            all_relationships_data.append(relationship_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to prepare cluster {cluster_id} relationships: {e}")
                    continue
            
            # Bulk save all cluster relationships
            if all_relationships_data:
                results = await save_article_relationships_bulk(all_relationships_data)
                successful_relationships = sum(results)
                
                logger.info(
                    "F-17: Bulk saved topic cluster relationships",
                    clusters_processed=len(clusters),
                    relationships_created=successful_relationships,
                    total_attempted=len(all_relationships_data)
                )
            else:
                logger.info("No cluster relationships to save")
                
        except Exception as e:
            logger.warning(f"Failed to bulk save cluster relationships: {e}")
            # Fallback to individual processing
            await self._save_cluster_relationships_individually(clustered_articles)
    
    async def _save_cluster_relationships_individually(self, clustered_articles: List[ProcessedArticle]):
        """Fallback method to save cluster relationships individually."""
        try:
            from src.utils.supabase_client import get_supabase_client, save_article_relationship
            client = await get_supabase_client()
            
            if not client.is_available():
                return
            
            # Group articles by cluster_id
            clusters = {}
            for article in clustered_articles:
                cluster_id = getattr(article, 'cluster_id', None)
                if cluster_id is not None:
                    if cluster_id not in clusters:
                        clusters[cluster_id] = []
                    clusters[cluster_id].append(article)
            
            relationship_count = 0
            
            # For each cluster with multiple articles, record relationships
            for cluster_id, articles in clusters.items():
                if len(articles) < 2:
                    continue
                
                # Get article UUIDs from Supabase
                article_uuids = {}
                for article in articles:
                    article_id = article.summarized_article.filtered_article.raw_article.id
                    try:
                        result = client.client.table("contextual_articles").select("id").eq(
                            "article_id", article_id
                        ).execute()
                        
                        if result.data:
                            article_uuids[article_id] = result.data[0]["id"]
                    except Exception as e:
                        logger.warning(f"Failed to get UUID for article {article_id}: {e}")
                
                # Record relationships between articles in the same cluster
                article_list = list(article_uuids.items())
                for i, (_article_id_1, uuid_1) in enumerate(article_list):
                    for _j, (_article_id_2, uuid_2) in enumerate(article_list[i+1:], i+1):
                        try:
                            similarity_score = 0.75  # Default cluster similarity
                            
                            await save_article_relationship(
                                parent_article_uuid=uuid_1,
                                child_article_uuid=uuid_2,
                                relationship_type="related",
                                similarity_score=similarity_score,
                                reasoning=f"Topic cluster {cluster_id}: Articles grouped together by semantic similarity"
                            )
                            relationship_count += 1
                            
                        except Exception as e:
                            logger.warning(f"Failed to save cluster relationship: {e}")
            
            if relationship_count > 0:
                logger.info(
                    "F-17: Saved topic cluster relationships (individual)",
                    clusters_processed=len(clusters),
                    relationships_created=relationship_count
                )
                
        except Exception as e:
            logger.warning(f"Failed to save cluster relationships individually: {e}")
    
    def _trim_articles_by_relevance(self, articles: List[ProcessedArticle], max_count: int) -> List[ProcessedArticle]:
        """Trim articles to maximum count by relevance score."""
        def sort_key(article):
            relevance = article.summarized_article.filtered_article.ai_relevance_score
            confidence = article.summarized_article.summary.confidence_score
            citation_count = len(getattr(article, 'citations', []))
            return (relevance * 0.4 + confidence * 0.4 + citation_count * 0.1, -len(article.summarized_article.summary.summary_points))
        
        articles.sort(key=sort_key, reverse=True)
        trimmed_articles = articles[:max_count]
        
        logger.info(
            "Trimmed articles to meet PRD limit",
            final_count=len(trimmed_articles),
            max_allowed=max_count
        )
        
        return trimmed_articles
    
    async def _ensure_minimum_articles(self, clustered_articles: List[ProcessedArticle], deduplicated_articles: List[ProcessedArticle], target_count: int) -> List[ProcessedArticle]:
        """Ensure minimum article count by adding additional articles."""
        logger.warning("Article count below PRD minimum (7), adding additional articles")
        
        # Get articles not in clustered_articles
        clustered_ids = {a.summarized_article.filtered_article.raw_article.id for a in clustered_articles}
        remaining_articles = [
            a for a in deduplicated_articles
            if a.summarized_article.filtered_article.raw_article.id not in clustered_ids
        ]
        
        if remaining_articles:
            additional_needed = min(target_count - len(clustered_articles), len(remaining_articles))
            logger.info(
                f"Adding {additional_needed} articles to meet PRD requirement",
                current_count=len(clustered_articles),
                target_count=target_count
            )
            
            additional_articles = remaining_articles[:additional_needed]
            clustered_articles.extend(additional_articles)
            
            logger.info(
                f"Added {len(additional_articles)} articles to meet PRD requirement",
                final_count=len(clustered_articles),
                prd_compliance=len(clustered_articles) >= target_count
            )
        
        return clustered_articles
    
    def _validate_prd_compliance(self, articles: List[ProcessedArticle]) -> dict:
        """Validate PRD compliance across multiple requirements."""
        compliance_result = {
            "total_articles": len(articles),
            "prd_compliant": True,
            "violations": [],
            "warnings": []
        }
        
        # F-5: 7-8 articles requirement
        if len(articles) < 7:
            compliance_result["prd_compliant"] = False
            compliance_result["violations"].append({
                "requirement": "F-5",
                "description": "記事数が最低要件を下回る",
                "expected": "7-8記事",
                "actual": f"{len(articles)}記事"
            })
        elif len(articles) > 8:
            compliance_result["warnings"].append({
                "requirement": "F-5",
                "description": "記事数が推奨上限を超過",
                "expected": "7-8記事",
                "actual": f"{len(articles)}記事"
            })
        
        # F-3: 3-4 bullet point summaries
        for i, article in enumerate(articles):
            summary_points = article.summarized_article.summary.summary_points
            if len(summary_points) < 3:
                compliance_result["warnings"].append({
                    "requirement": "F-3",
                    "description": f"記事{i+1}の箇条書きが不足",
                    "expected": "3-4個",
                    "actual": f"{len(summary_points)}個"
                })
            elif len(summary_points) > 4:
                compliance_result["warnings"].append({
                    "requirement": "F-3",
                    "description": f"記事{i+1}の箇条書きが過多",
                    "expected": "3-4個",
                    "actual": f"{len(summary_points)}個"
                })
        
        # Citations requirement
        for i, article in enumerate(articles):
            citation_count = len(article.citations) if article.citations else 0
            if citation_count < 1:
                compliance_result["violations"].append({
                    "requirement": "Citations",
                    "description": f"記事{i+1}に引用が不足",
                    "expected": "最低1個",
                    "actual": f"{citation_count}個"
                })
            elif citation_count < 3:
                compliance_result["warnings"].append({
                    "requirement": "Citations",
                    "description": f"記事{i+1}の引用が推奨数を下回る",
                    "expected": "3個推奨",
                    "actual": f"{citation_count}個"
                })
        
        # F-16: Update articles with 🆙 emoji
        update_articles = [a for a in articles if a.is_update]
        update_with_emoji = [a for a in update_articles
                           if a.japanese_title and a.japanese_title.startswith('🆙')]
        
        if update_articles and len(update_with_emoji) < len(update_articles):
            missing_emoji = len(update_articles) - len(update_with_emoji)
            compliance_result["warnings"].append({
                "requirement": "F-16",
                "description": f"{missing_emoji}件の続報記事に🆙絵文字が不足",
                "expected": "全続報記事に🆙",
                "actual": f"{len(update_with_emoji)}/{len(update_articles)}記事"
            })
        
        # Log compliance results
        if compliance_result["prd_compliant"]:
            logger.info(
                "PRD compliance validation PASSED",
                article_count=len(articles),
                violations=len(compliance_result["violations"]),
                warnings=len(compliance_result["warnings"])
            )
        else:
            logger.error(
                "PRD compliance validation FAILED",
                article_count=len(articles),
                violations=len(compliance_result["violations"]),
                warnings=len(compliance_result["warnings"]),
                violation_details=compliance_result["violations"]
            )
        
        return compliance_result
    
    async def _fallback_simple_clustering(self, state: dict, deduplicated_articles: List[ProcessedArticle], start_time: float, error_reason: str) -> dict:
        """Fallback to simple clustering when advanced clustering fails."""
        try:
            logger.info("Falling back to simple clustering")
            config = state["config"]
            
            def sort_key(article):
                relevance = article.summarized_article.filtered_article.ai_relevance_score
                confidence = article.summarized_article.summary.confidence_score
                return (relevance * 0.6 + confidence * 0.4)
            
            sorted_articles = sorted(deduplicated_articles, key=sort_key, reverse=True)
            max_articles = min(len(sorted_articles), config.max_items, 8)
            fallback_articles = sorted_articles[:max_articles]
            
            # Add empty citations for fallback
            for article in fallback_articles:
                if not hasattr(article, 'citations') or not article.citations:
                    raw_article = article.summarized_article.filtered_article.raw_article
                    basic_citation = Citation(
                        source_name=raw_article.source_id.title(),
                        url=str(raw_article.url),
                        title=raw_article.title,
                        japanese_summary=f"{raw_article.title[:80]}に関する記事"
                    )
                    article.citations = [basic_citation]
            
            logger.info(f"Fallback clustering produced {len(fallback_articles)} articles")
            
            fallback_log = ProcessingLog(
                processing_id=config.processing_id,
                timestamp=time.time(),
                stage="cluster_topics_fallback",
                event_type="warning",
                message=f"Fallback clustering completed with {len(fallback_articles)} articles",
                data={
                    "input_articles": len(deduplicated_articles),
                    "output_articles": len(fallback_articles),
                    "fallback_reason": error_reason
                },
                duration_seconds=time.time() - start_time
            )
            
            return {
                **state,
                "clustered_articles": fallback_articles,
                "processing_logs": state["processing_logs"] + [fallback_log],
                "status": "topics_clustered_fallback"
            }
            
        except Exception as fallback_error:
            logger.error("Fallback clustering also failed", error=str(fallback_error))
            
            error_log = ProcessingLog(
                processing_id=state["config"].processing_id,
                timestamp=time.time(),
                stage="cluster_topics",
                event_type="error",
                message=f"Both advanced and fallback clustering failed: {str(fallback_error)}",
                duration_seconds=time.time() - start_time
            )
            
            return {
                **state,
                "clustered_articles": [],
                "processing_logs": state["processing_logs"] + [error_log],
                "status": "cluster_topics_failed"
            }
    
    def _log_duplicate_processing_results(self, config, input_articles: List[SummarizedArticle], output_articles: List[ProcessedArticle],
                             duplicate_count: int, update_count: int, processing_time: float) -> ProcessingLog:
        """Create processing log for duplicate checking results."""
        return ProcessingLog(
            processing_id=config.processing_id,
            timestamp=time.time(),
            stage="check_duplicates_context",
            event_type="info",
            message=f"Processed {len(output_articles)} articles, removed {duplicate_count} duplicates, found {update_count} updates",
            data={
                "input_articles": len(input_articles),
                "output_articles": len(output_articles),
                "duplicates_removed": duplicate_count,
                "updates_found": update_count,
                "duplicate_rate": duplicate_count / len(input_articles) if input_articles else 0
            },
            duration_seconds=processing_time
        )
    
    # Phase 3.2d: Bulk Database Operations
    
    async def _bulk_save_articles_to_database(self, articles: List[ProcessedArticle]) -> None:
        """
        Save all articles to database using bulk operations (Phase 3.2d optimization).
        
        This method significantly reduces database connection overhead by:
        - Batching contextual articles into bulk inserts
        - Batching article relationships into bulk inserts  
        - Reducing individual DB calls from N to 1-2 bulk operations
        
        Args:
            articles: List of ProcessedArticle objects to save
        """
        if not articles:
            return
            
        logger.info(f"Starting bulk database save for {len(articles)} articles")
        
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            
            if not settings.processing.enable_db_bulk_operations:
                logger.info("Database bulk operations disabled, using individual processing")
                await self._save_articles_individually(articles)
                return
            
            # Step 1: Prepare embeddings for all articles
            embeddings = await self._generate_embeddings_for_articles(articles)
            
            # Step 2: Prepare bulk data for contextual articles
            from src.utils.supabase_client import prepare_contextual_articles_bulk_data, save_contextual_articles_bulk
            bulk_articles_data = prepare_contextual_articles_bulk_data(
                articles=articles,
                embeddings=embeddings,
                topic_clusters=[None] * len(articles)  # Will be set in clustering phase
            )
            
            # Step 3: Bulk save contextual articles
            article_uuids = await save_contextual_articles_bulk(bulk_articles_data)
            
            # Step 4: Prepare and save relationships in bulk
            relationships_data = self._prepare_relationships_bulk_data(articles, article_uuids)
            
            if relationships_data:
                from src.utils.supabase_client import save_article_relationships_bulk
                await save_article_relationships_bulk(relationships_data)
                logger.info(f"Bulk saved {len(relationships_data)} article relationships")
            
            successful_articles = sum(1 for uuid in article_uuids if uuid is not None)
            success_rate = (successful_articles / len(articles)) * 100
            
            logger.info(
                f"Bulk database save completed: {successful_articles}/{len(articles)} articles saved "
                f"({success_rate:.1f}% success rate)"
            )
            
        except Exception as e:
            logger.error(f"Bulk database save failed: {e}")
            # Fall back to individual processing
            await self._save_articles_individually(articles)
    
    async def _generate_embeddings_for_articles(self, articles: List[ProcessedArticle]) -> List[Union[list[float], None]]:
        """
        Generate embeddings for all articles efficiently.
        
        Args:
            articles: List of ProcessedArticle objects
            
        Returns:
            List of embedding vectors (same order as articles, None for failed items)
        """
        if not self.embedding_manager:
            return [None] * len(articles)
        
        try:
            # Prepare embedding texts
            embedding_texts = []
            for article in articles:
                raw_article = article.summarized_article.filtered_article.raw_article
                embedding_text = f"{raw_article.title}\n{raw_article.content}\n" + "\n".join(
                    article.summarized_article.summary.summary_points
                )
                embedding_texts.append(embedding_text)
            
            # Use batch embedding generation from Phase 3.2b
            embeddings = await self.embedding_manager.generate_embeddings_batch(
                texts=embedding_texts,
                batch_size=self.settings.processing.embedding_batch_size,
                max_concurrent_batches=self.settings.processing.max_concurrent_embedding_batches
            )
            
            # Convert numpy arrays to lists for JSON serialization
            result_embeddings = []
            for embedding in embeddings:
                if embedding is not None:
                    result_embeddings.append(embedding.tolist())
                else:
                    result_embeddings.append(None)
            
            return result_embeddings
            
        except Exception as e:
            logger.error(f"Bulk embedding generation failed: {e}")
            return [None] * len(articles)
    
    def _prepare_relationships_bulk_data(
        self, 
        articles: List[ProcessedArticle], 
        article_uuids: List[Union[str, None]]
    ) -> List[dict]:
        """
        Prepare relationship data for bulk insertion.
        
        Args:
            articles: List of ProcessedArticle objects
            article_uuids: List of article UUIDs from database
            
        Returns:
            List of relationship data dictionaries
        """
        relationships_data = []
        
        for i, (article, article_uuid) in enumerate(zip(articles, article_uuids)):
            if not article_uuid:
                continue  # Skip articles that failed to save
            
            # Get context analysis from temporary storage
            context_analysis = getattr(article, '_bulk_context_analysis', None)
            is_update = getattr(article, '_bulk_is_update', False)
            
            if not context_analysis or not context_analysis.references:
                continue
            
            # Process relationships for this article
            for ref_article_id in context_analysis.references[:3]:
                try:
                    # Find the reference article UUID
                    ref_uuid = None
                    for j, (ref_article, ref_uuid_candidate) in enumerate(zip(articles, article_uuids)):
                        if (ref_uuid_candidate and 
                            ref_article.summarized_article.filtered_article.raw_article.id == ref_article_id):
                            ref_uuid = ref_uuid_candidate
                            break
                    
                    if not ref_uuid:
                        continue  # Reference article not found in current batch
                    
                    # Determine relationship type
                    relationship_type = "related"
                    if context_analysis.decision == "UPDATE":
                        relationship_type = "update"
                    elif context_analysis.similarity_score > 0.8:
                        relationship_type = "sequel"
                    
                    # Add relationship data
                    relationship_data = {
                        "parent_article_id": ref_uuid,
                        "child_article_id": article_uuid,
                        "relationship_type": relationship_type,
                        "similarity_score": context_analysis.similarity_score,
                        "reasoning": f"Context analysis: {context_analysis.reasoning}"
                    }
                    
                    relationships_data.append(relationship_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to prepare relationship for {ref_article_id}: {e}")
                    continue
        
        return relationships_data
    
    async def _save_articles_individually(self, articles: List[ProcessedArticle]) -> None:
        """
        Fallback method to save articles individually when bulk operations fail.
        
        Args:
            articles: List of ProcessedArticle objects to save
        """
        logger.info(f"Saving {len(articles)} articles individually (fallback)")
        
        successful_saves = 0
        
        for article in articles:
            try:
                # Get context data from temporary storage
                context_analysis = getattr(article, '_bulk_context_analysis', None)
                is_update = getattr(article, '_bulk_is_update', False)
                
                # Use original individual save method
                await self._save_article_data_to_storage(article, article, is_update, context_analysis)
                successful_saves += 1
                
            except Exception as e:
                logger.error(f"Individual article save failed: {e}")
                continue
            finally:
                # Clean up temporary attributes
                if hasattr(article, '_bulk_context_analysis'):
                    delattr(article, '_bulk_context_analysis')
                if hasattr(article, '_bulk_is_update'):
                    delattr(article, '_bulk_is_update')
        
        success_rate = (successful_saves / len(articles)) * 100
        logger.info(
            f"Individual article save completed: {successful_saves}/{len(articles)} saved "
            f"({success_rate:.1f}% success rate)"
        )