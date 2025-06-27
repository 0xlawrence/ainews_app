"""
Duplicate detection using Jaccard similarity and SequenceMatcher.

This module implements a basic duplicate detection system for Phase 1,
using text similarity algorithms without embeddings.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

from src.models.schemas import DuplicateCheckResult, SummarizedArticle
from src.utils.logger import setup_logging
from src.constants.settings import SIMILARITY_THRESHOLDS, SIMILARITY_WEIGHTS, CONTENT_PROCESSING
from src.constants.mappings import REPUTABLE_DOMAINS
from src.utils.text_processing import normalize_title_for_comparison

logger = setup_logging()


class BasicDuplicateChecker:
    """Enhanced duplicate checker with intelligent consolidation."""
    
    def __init__(
        self,
        jaccard_threshold: float = SIMILARITY_THRESHOLDS['duplicate_jaccard'],
        sequence_threshold: float = SIMILARITY_THRESHOLDS['duplicate_sequence'], 
        consolidation_mode: bool = True    # Enable intelligent consolidation
    ):
        """
        Initialize duplicate checker.
        
        Args:
            jaccard_threshold: Minimum Jaccard similarity for duplicates
            sequence_threshold: Minimum sequence ratio for duplicates  
            consolidation_mode: Enable intelligent consolidation instead of simple removal
        """
        self.jaccard_threshold = jaccard_threshold
        self.sequence_threshold = sequence_threshold
        self.consolidation_mode = consolidation_mode
        
        # Cache for processed articles (in-memory for Phase 1)
        self.processed_articles: List[SummarizedArticle] = []
        
        # Duplicate groups for consolidation
        self.duplicate_groups: List[List[SummarizedArticle]] = []
    
    def check_duplicate(
        self,
        current_article: SummarizedArticle,
        past_articles: Optional[List[SummarizedArticle]] = None
    ) -> DuplicateCheckResult:
        """
        Check if current article is a duplicate of past articles.
        
        Args:
            current_article: Article to check for duplicates
            past_articles: Optional list of past articles (uses cache if None)
        
        Returns:
            DuplicateCheckResult with duplicate detection results
        """
        
        import time
        start_time = time.time()
        
        if past_articles is None:
            past_articles = self.processed_articles
        
        logger.debug(
            "Starting duplicate check",
            article_id=current_article.filtered_article.raw_article.id,
            past_articles_count=len(past_articles)
        )
        
        if not past_articles:
            # No past articles to compare against
            result = DuplicateCheckResult(
                is_duplicate=False,
                method="fast_screening",
                processing_time_seconds=time.time() - start_time
            )
            self._add_to_cache(current_article)
            return result
        
        # Extract text for comparison
        current_text = self._extract_comparison_text(current_article)
        
        best_match = None
        best_score = 0.0
        # Allowed values per DuplicateCheckResult schema
        best_method: str = "fast_screening"
        
        for past_article in past_articles:
            try:
                # Use enhanced similarity for better accuracy
                enhanced_score = self._calculate_enhanced_similarity(current_article, past_article)
                
                # Also calculate basic scores for comparison/fallback
                past_text = self._extract_comparison_text(past_article)
                jaccard_score = self._calculate_jaccard_similarity(current_text, past_text)
                sequence_score = self._calculate_sequence_similarity(current_text, past_text)
                basic_max_score = max(jaccard_score, sequence_score)
                
                # Use enhanced score if significantly different, otherwise use basic
                if abs(enhanced_score - basic_max_score) > SIMILARITY_THRESHOLDS['enhanced_diff_threshold']:
                    # Significant difference - use enhanced score
                    max_score = enhanced_score
                    method_internal = "enhanced"
                else:
                    # Similar results - use basic score for consistency
                    max_score = basic_max_score
                    method_internal = "jaccard" if jaccard_score > sequence_score else "sequence"
                
                # Schema only permits "fast_screening" or "embedding_similarity"
                method = "fast_screening"
                
                if max_score > best_score:
                    best_score = max_score
                    best_match = past_article
                    best_method = method
                
                logger.debug(
                    "Similarity comparison",
                    current_id=current_article.filtered_article.raw_article.id,
                    past_id=past_article.filtered_article.raw_article.id,
                    jaccard_score=jaccard_score,
                    sequence_score=sequence_score,
                    max_score=max_score
                )
            
            except Exception as e:
                logger.warning(
                    "Error comparing articles",
                    current_id=current_article.filtered_article.raw_article.id,
                    past_id=past_article.filtered_article.raw_article.id,
                    error=str(e)
                )
                continue
        
        # Determine if duplicate
        is_duplicate = False
        if best_score >= max(self.jaccard_threshold, self.sequence_threshold):
            is_duplicate = True
        
        # Ensure the method conforms to the schema literal set
        result = DuplicateCheckResult(
            is_duplicate=is_duplicate,
            method=best_method,
            similarity_score=best_score,
            duplicate_article_id=(
                best_match.filtered_article.raw_article.id if best_match else None
            ),
            processing_time_seconds=time.time() - start_time
        )
        
        if is_duplicate:
            logger.info(
                "Duplicate detected",
                current_id=current_article.filtered_article.raw_article.id,
                duplicate_id=result.duplicate_article_id,
                similarity_score=best_score,
                method=best_method
            )
        else:
            # Add to cache if not duplicate
            self._add_to_cache(current_article)
        
        return result
    
    def _extract_comparison_text(self, article: SummarizedArticle) -> str:
        """Extract text for comparison from article."""
        
        raw_article = article.filtered_article.raw_article
        
        # Combine title and content
        title = raw_article.title.strip()
        content = raw_article.content.strip()
        
        # Normalize text
        text = f"{title} {content}"
        text = self._normalize_text(text)
        
        return text
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove common stop words that don't affect meaning
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        words = text.split()
        filtered_words = [word for word in words if word not in stop_words]
        
        return ' '.join(filtered_words)
    
    def _calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        
        # Convert to word sets
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard coefficient
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        jaccard_score = len(intersection) / len(union)
        
        return jaccard_score
    
    def _calculate_sequence_similarity(self, text1: str, text2: str) -> float:
        """Calculate sequence similarity using SequenceMatcher."""
        
        matcher = SequenceMatcher(None, text1, text2)
        ratio = matcher.ratio()
        
        return ratio
    
    def _calculate_enhanced_similarity(self, article1: SummarizedArticle, article2: SummarizedArticle) -> float:
        """
        Calculate enhanced similarity combining multiple methods for better accuracy.
        
        Args:
            article1: First article to compare
            article2: Second article to compare
            
        Returns:
            Combined similarity score (0.0 to 1.0)
        """
        try:
            # Extract comparison texts
            text1 = self._extract_comparison_text(article1)
            text2 = self._extract_comparison_text(article2)
            
            # 1. Title similarity (weighted heavily)
            title1 = normalize_title_for_comparison(article1.filtered_article.raw_article.title)
            title2 = normalize_title_for_comparison(article2.filtered_article.raw_article.title)
            title_jaccard = self._calculate_jaccard_similarity(title1, title2)
            title_sequence = self._calculate_sequence_similarity(title1, title2)
            title_similarity = max(title_jaccard, title_sequence)
            
            # 2. Content similarity (summary points)
            content_jaccard = self._calculate_jaccard_similarity(text1, text2)
            content_sequence = self._calculate_sequence_similarity(text1, text2)
            content_similarity = max(content_jaccard, content_sequence)
            
            # 3. Content excerpt similarity (for detailed content comparison)
            excerpt_length = CONTENT_PROCESSING['excerpt_length']
            content1_excerpt = article1.filtered_article.raw_article.content[:excerpt_length]
            content2_excerpt = article2.filtered_article.raw_article.content[:excerpt_length]
            excerpt_sequence = self._calculate_sequence_similarity(content1_excerpt, content2_excerpt)
            
            # 4. Source domain similarity bonus
            source_bonus = 0.0
            url1 = str(article1.filtered_article.raw_article.url)
            url2 = str(article2.filtered_article.raw_article.url)
            
            # Extract domains for comparison
            import re
            domain1 = re.search(r'://([^/]+)', url1)
            domain2 = re.search(r'://([^/]+)', url2)
            
            if domain1 and domain2:
                d1 = domain1.group(1).lower()
                d2 = domain2.group(1).lower()
                
                # Different reputable sources covering same story gets bonus
                if d1 != d2:
                    d1_reputable = any(domain in d1 for domain in REPUTABLE_DOMAINS)
                    d2_reputable = any(domain in d2 for domain in REPUTABLE_DOMAINS)
                    if d1_reputable and d2_reputable:
                        source_bonus = SIMILARITY_WEIGHTS['source_bonus'] * 2  # Double bonus for cross-source coverage
            
            # 5. Weighted combination using configuration
            final_similarity = (
                title_similarity * SIMILARITY_WEIGHTS['title'] +
                content_similarity * SIMILARITY_WEIGHTS['content'] +  
                excerpt_sequence * SIMILARITY_WEIGHTS['excerpt'] +
                source_bonus
            )
            
            logger.debug(
                "Enhanced similarity breakdown",
                article1_id=article1.filtered_article.raw_article.id,
                article2_id=article2.filtered_article.raw_article.id,
                title_similarity=title_similarity,
                content_similarity=content_similarity,
                excerpt_similarity=excerpt_sequence,
                source_bonus=source_bonus,
                final_similarity=final_similarity
            )
            
            return min(final_similarity, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.warning(f"Enhanced similarity calculation failed: {e}")
            # Fallback to basic content similarity
            text1 = self._extract_comparison_text(article1)
            text2 = self._extract_comparison_text(article2)
            return max(
                self._calculate_jaccard_similarity(text1, text2),
                self._calculate_sequence_similarity(text1, text2)
            )
    
    
    def _add_to_cache(self, article: SummarizedArticle) -> None:
        """Add article to processed articles cache."""
        
        self.processed_articles.append(article)
        
        # Limit cache size to prevent memory issues
        max_cache_size = 1000
        if len(self.processed_articles) > max_cache_size:
            # Remove oldest articles
            self.processed_articles = self.processed_articles[-max_cache_size:]
            
            logger.debug(
                "Trimmed duplicate checker cache",
                new_size=len(self.processed_articles)
            )
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        
        return {
            "cached_articles": len(self.processed_articles),
            "memory_usage_mb": len(str(self.processed_articles)) / (1024 * 1024)
        }
    
    def clear_cache(self) -> None:
        """Clear the articles cache."""
        
        cache_size = len(self.processed_articles)
        self.processed_articles = []
        
        logger.info("Cleared duplicate checker cache", cleared_articles=cache_size)
    
    def consolidate_duplicates(self, articles: List[SummarizedArticle]) -> List[SummarizedArticle]:
        """
        Intelligent consolidation of duplicate articles.
        
        Instead of removing duplicates, this method:
        1. Groups similar articles together
        2. Selects the best representative from each group
        3. Enhances the representative with information from duplicates
        
        Args:
            articles: List of articles to process
            
        Returns:
            List of consolidated articles
        """
        if not self.consolidation_mode:
            # Fall back to simple duplicate removal
            return self._simple_duplicate_removal(articles)
        
        logger.info("Starting intelligent duplicate consolidation", total_articles=len(articles))
        
        # Build similarity groups
        groups = []
        ungrouped_articles = articles.copy()
        
        while ungrouped_articles:
            # Start new group with first ungrouped article
            current_article = ungrouped_articles.pop(0)
            current_group = [current_article]
            
            # Find similar articles to add to this group
            remaining_articles = []
            for candidate in ungrouped_articles:
                similarity_score = self._calculate_max_similarity(current_article, candidate)
                
                if similarity_score >= max(self.jaccard_threshold, self.sequence_threshold):
                    current_group.append(candidate)
                    logger.debug(
                        "Added article to duplicate group",
                        main_article=current_article.filtered_article.raw_article.id,
                        similar_article=candidate.filtered_article.raw_article.id,
                        similarity=similarity_score
                    )
                else:
                    remaining_articles.append(candidate)
            
            groups.append(current_group)
            ungrouped_articles = remaining_articles
        
        # Select best representative from each group
        consolidated_articles = []
        
        for group in groups:
            if len(group) == 1:
                # Single article, no consolidation needed
                consolidated_articles.append(group[0])
            else:
                # Multiple similar articles, consolidate
                representative = self._select_best_representative(group)
                enhanced_representative = self._enhance_with_duplicate_info(representative, group)
                consolidated_articles.append(enhanced_representative)
                
                logger.info(
                    "Consolidated duplicate group",
                    group_size=len(group),
                    representative_id=representative.filtered_article.raw_article.id,
                    duplicate_sources=[a.filtered_article.raw_article.source_id for a in group]
                )
        
        logger.info(
            "Duplicate consolidation completed",
            input_articles=len(articles),
            output_articles=len(consolidated_articles),
            groups_created=len(groups),
            duplicates_consolidated=len(articles) - len(consolidated_articles)
        )
        
        return consolidated_articles
    
    def _calculate_max_similarity(self, article1: SummarizedArticle, article2: SummarizedArticle) -> float:
        """Calculate maximum similarity between two articles."""
        text1 = self._extract_comparison_text(article1)
        text2 = self._extract_comparison_text(article2)
        
        jaccard_score = self._calculate_jaccard_similarity(text1, text2)
        sequence_score = self._calculate_sequence_similarity(text1, text2)
        
        return max(jaccard_score, sequence_score)
    
    def _simple_duplicate_removal(self, articles: List[SummarizedArticle]) -> List[SummarizedArticle]:
        """Simple duplicate removal (fallback method)."""
        unique_articles = []
        
        for article in articles:
            is_duplicate = False
            for existing in unique_articles:
                similarity = self._calculate_max_similarity(article, existing)
                if similarity >= max(self.jaccard_threshold, self.sequence_threshold):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_articles.append(article)
        
        return unique_articles
    
    def _select_best_representative(self, group: List[SummarizedArticle]) -> SummarizedArticle:
        """Select the best representative article from a duplicate group."""
        
        def score_article(article: SummarizedArticle) -> float:
            """Score article for representativeness."""
            # AI relevance score
            relevance = article.filtered_article.ai_relevance_score
            
            # Summary confidence score
            confidence = article.summary.confidence_score or 0.0
            
            # Source priority boost
            source_id = article.filtered_article.raw_article.source_id
            priority_sources = {
                'openai_news': 0.3,
                'anthropic_news': 0.3,
                'google_research_blog': 0.25,
                'the_decoder': 0.2,
                'semianalysis': 0.2,
                'stratechery': 0.2
            }
            source_boost = priority_sources.get(source_id, 0.0)
            
            # Content length bonus (more comprehensive articles)
            content_length = len(article.filtered_article.raw_article.content)
            length_bonus = min(content_length / 5000.0, 0.1)  # Max 0.1 bonus
            
            # Recency bonus (newer articles preferred)
            import time
            from datetime import datetime
            pub_date = article.filtered_article.raw_article.published_date
            age_hours = (datetime.now() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
            recency_bonus = max(0, 0.1 - (age_hours / 240))  # Decay over 10 days
            
            total_score = relevance + confidence + source_boost + length_bonus + recency_bonus
            
            logger.debug(
                "Article representativeness score",
                article_id=article.filtered_article.raw_article.id,
                relevance=relevance,
                confidence=confidence,
                source_boost=source_boost,
                length_bonus=length_bonus,
                recency_bonus=recency_bonus,
                total=total_score
            )
            
            return total_score
        
        # Select article with highest score
        best_article = max(group, key=score_article)
        
        logger.debug(
            "Selected best representative",
            representative_id=best_article.filtered_article.raw_article.id,
            group_size=len(group),
            representative_score=score_article(best_article)
        )
        
        return best_article
    
    def _enhance_with_duplicate_info(
        self, 
        representative: SummarizedArticle, 
        group: List[SummarizedArticle]
    ) -> SummarizedArticle:
        """Enhance representative article with information from duplicates."""
        
        if len(group) <= 1:
            return representative
        
        # Get other sources covering the same story
        other_sources = []
        for article in group:
            if article != representative:
                source_id = article.filtered_article.raw_article.source_id
                source_name = source_id.replace('_', ' ').title()
                other_sources.append(source_name)
        
        if other_sources:
            # Add source information to the summary
            source_info = f"[関連報道: {', '.join(other_sources)}]"
            
            # Modify the last summary point to include source information
            summary_points = representative.summary.summary_points.copy()
            if summary_points:
                summary_points[-1] = f"{summary_points[-1]} {source_info}"
                
                # Create updated summary
                from copy import deepcopy
                enhanced_representative = deepcopy(representative)
                enhanced_representative.summary.summary_points = summary_points
                
                # Add 🆙 emoji for multi-source stories
                title = enhanced_representative.filtered_article.raw_article.title
                if not title.startswith('🆙'):
                    enhanced_representative.filtered_article.raw_article.title = f"🆙 {title}"
                
                logger.debug(
                    "Enhanced representative with duplicate info",
                    representative_id=representative.filtered_article.raw_article.id,
                    other_sources=other_sources,
                    enhanced_title=enhanced_representative.filtered_article.raw_article.title
                )
                
                return enhanced_representative
        
        return representative
    
    def load_past_articles_from_window(
        self,
        articles: List[SummarizedArticle],
        days_lookback: int = 7
    ) -> None:
        """
        Load articles from a time window into cache.
        
        Args:
            articles: List of past articles
            days_lookback: Number of days to look back
        """
        
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_lookback)
        
        # Filter articles by date
        recent_articles = []
        for article in articles:
            pub_date = article.filtered_article.raw_article.published_date
            if pub_date.replace(tzinfo=None) >= cutoff_date:
                recent_articles.append(article)
        
        self.processed_articles = recent_articles
        
        logger.info(
            "Loaded past articles for duplicate checking",
            total_articles=len(articles),
            recent_articles=len(recent_articles),
            days_lookback=days_lookback
        )


def check_article_duplicates(
    current_article: SummarizedArticle,
    past_articles: List[SummarizedArticle],
    jaccard_threshold: float = 0.6,    # Lowered threshold
    sequence_threshold: float = 0.65   # Lowered threshold
) -> DuplicateCheckResult:
    """
    Convenience function to check for duplicates.
    
    Args:
        current_article: Article to check
        past_articles: Past articles to compare against
        jaccard_threshold: Jaccard similarity threshold
        sequence_threshold: Sequence similarity threshold
    
    Returns:
        DuplicateCheckResult
    """
    
    checker = BasicDuplicateChecker(jaccard_threshold, sequence_threshold)
    return checker.check_duplicate(current_article, past_articles)


def consolidate_similar_articles(
    articles: List[SummarizedArticle],
    jaccard_threshold: float = 0.55,  # Default fallback値
    sequence_threshold: float = 0.60,  # Default fallback値
    consolidation_mode: bool = True,
    *,
    similarity_threshold: float | None = None  # 新規オプション (both metricsに適用)
) -> List[SummarizedArticle]:
    """
    Convenience function for intelligent duplicate consolidation.
    
    Args:
        articles: Articles to consolidate
        jaccard_threshold: Jaccard similarity threshold
        sequence_threshold: Sequence similarity threshold
        consolidation_mode: Enable intelligent consolidation
        similarity_threshold: Optional unified similarity threshold for both metrics
    
    Returns:
        List of consolidated articles
    """
    
    # If a unified similarity_threshold が渡された場合は、両方のメトリクスに適用
    if similarity_threshold is not None:
        jaccard_threshold = similarity_threshold
        sequence_threshold = similarity_threshold

    checker = BasicDuplicateChecker(
        jaccard_threshold=jaccard_threshold,
        sequence_threshold=sequence_threshold,
        consolidation_mode=consolidation_mode,
    )
    return checker.consolidate_duplicates(articles)