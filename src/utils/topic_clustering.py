"""
Topic clustering for newsletter articles.

This module implements advanced topic clustering using embeddings
and clustering algorithms to group related articles and select
representative articles with citations.
"""

import asyncio
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

from src.models.schemas import ProcessedArticle, SummarizedArticle
from src.utils.embedding_manager import EmbeddingManager
from src.utils.logger import setup_logging
from src.config.settings import get_settings

try:
    from src.llm.llm_router import LLMRouter
    HAS_LLM_ROUTER = True
except ImportError:
    HAS_LLM_ROUTER = False
    LLMRouter = None

logger = setup_logging()


@dataclass
class TopicCluster:
    """Represents a topic cluster with articles and metadata."""
    cluster_id: int
    topic_name: str
    representative_article: ProcessedArticle
    related_articles: List[ProcessedArticle]
    confidence_score: float
    article_count: int
    
    def get_citations(self, max_citations: int = 3) -> List[str]:
        """Get citation strings for related articles with F-15 duplicate prevention."""
        citations = []
        used_urls = set()  # Track URLs to prevent duplicates
        used_sources = set()  # Track source IDs to ensure diversity per F-15
        
        # Add representative article citation
        rep_article = self.representative_article.summarized_article
        rep_raw = rep_article.filtered_article.raw_article
        
        # Normalize URL for duplicate checking
        from src.utils.citation_generator import CitationGenerator
        temp_generator = CitationGenerator()
        rep_url_normalized = temp_generator._normalize_url(rep_raw.url)
        
        citations.append(
            f"**{rep_raw.source_id.title()}** ({str(rep_raw.url)}): {rep_raw.title}"
        )
        used_urls.add(rep_url_normalized)
        used_sources.add(rep_raw.source_id)
        
        # Add related article citations (ensuring different sources per F-15)
        for article in self.related_articles:
            if len(citations) >= max_citations:
                break
                
            raw_article = article.summarized_article.filtered_article.raw_article
            url_str = str(raw_article.url)
            
            # Skip dummy placeholders
            if "video_example" in url_str:
                continue
            
            # F-15 compliance: Ensure different sources per article
            article_url_normalized = temp_generator._normalize_url(raw_article.url)
            if (article_url_normalized not in used_urls and 
                raw_article.source_id not in used_sources):
                
                citations.append(
                    f"**{raw_article.source_id.title()}** ({url_str}): {raw_article.title}"
                )
                used_urls.add(article_url_normalized)
                used_sources.add(raw_article.source_id)
        
        logger.info(
            f"Generated {len(citations)} citations for cluster {self.cluster_id}",
            sources_used=list(used_sources),
            duplicates_prevented=len([a for a in self.related_articles if 
                temp_generator._normalize_url(a.summarized_article.filtered_article.raw_article.url) in used_urls or
                a.summarized_article.filtered_article.raw_article.source_id in used_sources]) - len(citations) + 1
        )
        
        return citations


class TopicClusterer:
    """Advanced topic clustering for newsletter articles."""
    
    def __init__(self, embedding_manager: Optional[EmbeddingManager] = None):
        """Initialize topic clusterer."""
        self.settings = get_settings()
        self.embedding_manager = embedding_manager or EmbeddingManager()
        
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available - using simple clustering fallback")
            self.use_advanced_clustering = False
        else:
            self.use_advanced_clustering = True
        self.multi_source_threshold = 2.0  # 複数ソース判定の最小数（2記事以上）
        
        # Initialize LLM router for intelligent topic naming
        if HAS_LLM_ROUTER:
            self.llm_router = LLMRouter()
        else:
            self.llm_router = None
    
    async def cluster_articles(
        self, 
        articles: List[ProcessedArticle],
        max_clusters: int = 7,
        min_cluster_size: int = 2,
        similarity_threshold: float = 0.9  # Increased from 0.8 to 0.9 for tighter clustering
    ) -> List[TopicCluster]:
        """
        Cluster articles by topic and generate representative clusters.
        
        Args:
            articles: List of processed articles
            max_clusters: Maximum number of clusters to create
            min_cluster_size: Minimum articles per cluster
            similarity_threshold: Similarity threshold for clustering
            
        Returns:
            List of topic clusters with representative articles
        """
        
        if not articles:
            logger.info("No articles to cluster")
            return []
        
        # Filter articles for AI relevance before clustering
        filtered_articles = self._filter_ai_relevant_articles(articles)
        
        if not filtered_articles:
            logger.warning("No articles passed AI relevance filter")
            return []
        
        if len(filtered_articles) < len(articles):
            logger.info(
                f"Filtered {len(articles) - len(filtered_articles)} articles for low AI relevance"
            )
        
        # Generate embeddings for filtered articles
        embeddings = await self._generate_article_embeddings(filtered_articles)
        
        if not embeddings:
            logger.warning("No embeddings generated, using simple clustering")
            return await self._simple_clustering(filtered_articles, max_clusters)
        
        # Perform clustering
        if self.use_advanced_clustering and len(filtered_articles) >= min_cluster_size:
            clusters = await self._advanced_clustering(
                filtered_articles, embeddings, max_clusters, min_cluster_size, similarity_threshold
            )
        else:
            clusters = await self._simple_clustering(filtered_articles, max_clusters)
        
        logger.info(
            "Topic clustering completed",
            total_articles=len(articles),
            clusters_created=len(clusters),
            avg_cluster_size=np.mean([c.article_count for c in clusters]) if clusters else 0
        )
        
        return clusters
    
    async def _generate_article_embeddings(
        self, 
        articles: List[ProcessedArticle]
    ) -> List[Optional[np.ndarray]]:
        """Generate embeddings for articles."""
        
        embeddings = []
        
        for article in articles:
            try:
                # Create text for embedding (title + summary)
                raw_article = article.summarized_article.filtered_article.raw_article
                summary_points = article.summarized_article.summary.summary_points
                
                embedding_text = f"{raw_article.title} {' '.join(summary_points)}"
                
                # Get embedding
                embedding = await self.embedding_manager.get_embedding(embedding_text)
                embeddings.append(embedding)
                
            except Exception as e:
                logger.warning(
                    "Failed to generate embedding for article",
                    article_id=article.summarized_article.filtered_article.raw_article.id,
                    error=str(e)
                )
                embeddings.append(None)
        
        return embeddings
    
    async def _advanced_clustering(
        self,
        articles: List[ProcessedArticle],
        embeddings: List[Optional[np.ndarray]],
        max_clusters: int,
        min_cluster_size: int,
        similarity_threshold: float
    ) -> List[TopicCluster]:
        """Perform advanced clustering using machine learning."""
        
        # Filter out None embeddings
        valid_embeddings = []
        valid_articles = []
        
        for article, embedding in zip(articles, embeddings):
            if embedding is not None:
                valid_embeddings.append(embedding)
                valid_articles.append(article)
        
        if len(valid_embeddings) < min_cluster_size:
            logger.info("Not enough valid embeddings for advanced clustering")
            return await self._simple_clustering(articles, max_clusters)
        
        # Convert to numpy array
        embedding_matrix = np.array(valid_embeddings)
        
        # Determine optimal number of clusters
        n_articles = len(valid_articles)
        optimal_clusters = min(max_clusters, max(2, n_articles // min_cluster_size))
        
        try:
            # Use HDBSCAN for more robust, variable-density clustering
            if not HDBSCAN_AVAILABLE:
                raise ImportError("hdbscan library not found")

            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=1,  # Allow single-linkage clusters
                metric='euclidean', # Embeddings are normalized, so euclidean is equivalent to cosine
                cluster_selection_epsilon=1 - similarity_threshold, # Convert similarity to distance
                prediction_data=True
            )
            cluster_labels = clusterer.fit_predict(embedding_matrix)

            # Check if HDBSCAN found good clusters
            unique_labels = set(cluster_labels)
            n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
            
            if n_clusters == 0:
                # Fall back to KMeans if HDBSCAN finds no clusters
                logger.info("HDBSCAN found no clusters, using KMeans as fallback")
                kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(embedding_matrix)
            
        except Exception as e:
            logger.warning("Advanced clustering failed, using simple clustering", error=str(e))
            return await self._simple_clustering(articles, max_clusters)
        
        # Build clusters
        clusters = await self._build_clusters_from_labels(
            valid_articles, embedding_matrix, cluster_labels
        )
        
        return clusters
    
    async def _build_clusters_from_labels(
        self,
        articles: List[ProcessedArticle],
        embeddings: np.ndarray,
        cluster_labels: np.ndarray
    ) -> List[TopicCluster]:
        """Build TopicCluster objects from clustering results."""
        
        clusters = []
        cluster_groups = defaultdict(list)
        
        # Group articles by cluster label
        for article, embedding, label in zip(articles, embeddings, cluster_labels):
            if label != -1:  # Ignore noise points from DBSCAN
                cluster_groups[label].append((article, embedding))
        
        # Create TopicCluster objects
        for cluster_id, article_embedding_pairs in cluster_groups.items():
            # 各記事にクラスタ ID を付与（ProcessedArticle に動的フィールドとして保持）
            for art, _ in article_embedding_pairs:
                try:
                    # Convert numpy.int32 to Python int to avoid serialization errors
                    art.cluster_id = int(cluster_id)
                except Exception:
                    # ProcessedArticle は extra='allow' なので通常は問題ないが念のため
                    pass
            articles_in_cluster = [pair[0] for pair in article_embedding_pairs]
            embeddings_in_cluster = np.array([pair[1] for pair in article_embedding_pairs])
            
            if len(articles_in_cluster) < 1:
                continue
            
            # Find representative article (highest relevance + confidence)
            representative_article = self._select_representative_article(articles_in_cluster)
            
            # Generate topic name
            topic_name = await self._generate_topic_name(articles_in_cluster)
            
            # Calculate cluster confidence
            confidence_score = self._calculate_cluster_confidence(embeddings_in_cluster)
            
            # Create cluster
            cluster = TopicCluster(
                cluster_id=int(cluster_id),  # Convert numpy.int32 to Python int
                topic_name=topic_name,
                representative_article=representative_article,
                related_articles=[a for a in articles_in_cluster if a != representative_article],
                confidence_score=confidence_score,
                article_count=len(articles_in_cluster)
            )
            
            clusters.append(cluster)
        
        # Sort clusters by confidence and article count
        clusters.sort(key=lambda c: (c.confidence_score, c.article_count), reverse=True)
        
        return clusters
    
    async def _simple_clustering(
        self, 
        articles: List[ProcessedArticle], 
        max_clusters: int
    ) -> List[TopicCluster]:
        """Simple clustering fallback based on source and relevance."""
        
        # Group by source type
        source_groups = defaultdict(list)
        
        for article in articles:
            source_id = article.summarized_article.filtered_article.raw_article.source_id
            source_groups[source_id].append(article)
        
        clusters = []
        cluster_id = 0
        
        for source_id, source_articles in source_groups.items():
            if len(source_articles) == 0:
                continue
            
            # このソースグループに一意のクラスタ ID を割り当て
            for art in source_articles:
                try:
                    # Ensure cluster_id is Python int, not numpy type
                    art.cluster_id = int(cluster_id)
                except Exception:
                    pass
            
            # Sort by relevance and confidence
            sorted_articles = sorted(
                source_articles,
                key=lambda a: (
                    a.summarized_article.filtered_article.ai_relevance_score +
                    (a.summarized_article.summary.confidence_score or 0.0)
                ),
                reverse=True
            )
            
            # Create cluster
            representative_article = sorted_articles[0]
            related_articles = sorted_articles[1:]
            
            cluster = TopicCluster(
                cluster_id=int(cluster_id),  # Ensure Python int, not numpy type
                topic_name=f"{source_id.title()} News",
                representative_article=representative_article,
                related_articles=related_articles,
                confidence_score=representative_article.summarized_article.summary.confidence_score or 0.0,
                article_count=len(sorted_articles)
            )
            
            clusters.append(cluster)
            cluster_id += 1
            
            if len(clusters) >= max_clusters:
                break
        
        return clusters
    
    def _select_representative_article(
        self, 
        articles: List[ProcessedArticle]
    ) -> ProcessedArticle:
        """Select the most representative article from a cluster."""
        
        def score_article(article: ProcessedArticle) -> float:
            """Score article for representativeness."""
            relevance = article.summarized_article.filtered_article.ai_relevance_score
            confidence = article.summarized_article.summary.confidence_score or 0.0
            
            # Boost for high-priority sources
            source_id = article.summarized_article.filtered_article.raw_article.source_id
            priority_boost = 0.2 if source_id in { # Increased boost
                "openai_news", "anthropic_news", "google_research_blog", "deepmind_blog"
            } else 0.0
            
            # Penalty for broad news sources with potentially low AI relevance
            broad_news_penalty = 0.0
            if source_id in {"bay_area_times", "techcrunch", "wired", "venturebeat", "ieee_spectrum_ai"}:
                # Extra verification for AI relevance
                title_content = (
                    article.summarized_article.filtered_article.raw_article.title + " " +
                    " ".join(article.summarized_article.summary.summary_points)
                ).lower()
                
                # Check for AI-specific keywords
                ai_keywords = {
                    'ai', 'artificial intelligence', 'machine learning', 'neural network',
                    'openai', 'anthropic', 'google ai', 'meta ai', 'microsoft ai', 
                    'chatgpt', 'claude', 'gemini', 'gpt-', 'llama',
                    'llm', 'large language model', 'deep learning', 'transformer'
                }
                
                ai_keyword_count = sum(1 for keyword in ai_keywords if keyword in title_content)
                if ai_keyword_count < 3:  # Require at least 3 AI keywords for broad sources
                    broad_news_penalty = -0.5 # Increased penalty
            
            # Add bonus for longer, more detailed summaries
            summary_length = sum(len(p) for p in article.summarized_article.summary.summary_points)
            length_bonus = 0.1 if summary_length > 400 else 0.0

            return relevance + confidence + priority_boost + broad_news_penalty + length_bonus
        
        return max(articles, key=score_article)
    
    def _filter_ai_relevant_articles(self, articles: List[ProcessedArticle]) -> List[ProcessedArticle]:
        """Filter articles to ensure AI relevance, especially for broad news sources."""
        
        filtered_articles = []
        
        for article in articles:
            source_id = article.summarized_article.filtered_article.raw_article.source_id
            
            # For broad news sources, apply stricter AI relevance check
            if source_id in {"bay_area_times", "techcrunch", "wired", "venturebeat", "ieee_spectrum_ai"}:
                title_content = (
                    article.summarized_article.filtered_article.raw_article.title + " " +
                    article.summarized_article.filtered_article.raw_article.content[:500] + " " +
                    " ".join(article.summarized_article.summary.summary_points)
                ).lower()
                
                # Define AI keywords for broad sources (expanded to include behavioral AI)
                strict_ai_keywords = {
                    'artificial intelligence', 'machine learning', 'neural network', 'deep learning',
                    'openai', 'anthropic', 'google ai', 'meta ai', 'microsoft ai',
                    'chatgpt', 'claude', 'gemini', 'gpt-', 'llm', 'large language model',
                    'transformer', 'generative ai', 'ai model', 'ai training',
                    # Behavioral and emotional AI keywords
                    'empathetic', 'empathy', 'emotional intelligence', 'sentiment analysis',
                    'conversational ai', 'language model', 'natural language', 'nlp',
                    'human-ai interaction', 'behavioral ai', 'social ai',
                    'agi', 'artificial general intelligence'
                }
                
                # Check for content patterns that indicate non-AI focus
                # Only exclude if the content is clearly non-AI AND lacks strong AI context
                weak_ai_indicators = {
                    'sports', 'entertainment', 'celebrity', 'movie', 'music',
                    'real estate', 'housing market', 'property', 'mortgage',
                    'automotive', 'car', 'vehicle', 'transportation'
                }
                
                # Patterns that suggest geopolitical focus WITHOUT AI context
                geopolitical_focus_patterns = [
                    r'\b(israel|palestine|iran|gaza)\b.*\b(ceasefire|war|conflict|military)\b',
                    r'\b(ukraine|russia)\b.*\b(invasion|war|sanctions)\b',
                    r'\b(election|politics|senate|congress)\b.*\b(vote|campaign|policy)\b',
                    r'\b(climate change|renewable energy|solar|carbon)\b.*\b(emissions|environmental|green)\b'
                ]
                
                # Count AI keywords and check for non-AI focus patterns
                ai_keyword_count = sum(1 for keyword in strict_ai_keywords if keyword in title_content)
                
                # Check for weak AI indicators (clearly non-AI topics)
                has_weak_ai_indicator = any(keyword in title_content for keyword in weak_ai_indicators)
                
                # Check for geopolitical focus patterns that lack AI context
                import re
                has_geopolitical_focus = any(re.search(pattern, title_content, re.IGNORECASE) 
                                           for pattern in geopolitical_focus_patterns)
                
                # Extra strict filtering for Bay Area Times due to broad coverage
                if source_id == "bay_area_times":
                    # Require strong AI presence (3+ keywords) and avoid pure business/finance focus
                    business_only_patterns = [
                        r'\b(funding|investment|valuation|ipo)\b.*\b(million|billion|dollars|round)\b',
                        r'\b(revenue|profit|earnings|quarterly)\b.*\b(results|report|growth)\b',
                        r'\b(merger|acquisition)\b.*\b(deal|company|acquisition)\b'
                    ]
                    has_business_only_focus = any(re.search(pattern, title_content, re.IGNORECASE) 
                                                for pattern in business_only_patterns)
                    
                    # Relaxed filtering for Bay Area Times - allow more articles through to clustering
                    if (ai_keyword_count >= 3 and  # Increased from 2 to 3
                        not has_geopolitical_focus):
                        filtered_articles.append(article)
                    else:
                        logger.info(
                            f"Filtered out Bay Area Times article (geopolitical/low AI relevance): "
                            f"{article.summarized_article.filtered_article.raw_article.title[:80]}... "
                            f"(AI: {ai_keyword_count}, geo: {has_geopolitical_focus})"
                        )
                # Relaxed filtering for other broad sources  
                elif ai_keyword_count >= 2 and not has_geopolitical_focus:  # Increased from 1 to 2
                    filtered_articles.append(article)
                else:
                    logger.info(
                        f"Filtered out article from {source_id} due to low AI relevance: "
                        f"{article.summarized_article.filtered_article.raw_article.title[:100]}..."
                    )
            else:
                # For AI-specific sources, keep all articles
                filtered_articles.append(article)
        
        return filtered_articles
    
    async def _generate_topic_name(self, articles: List[ProcessedArticle]) -> str:
        """Generate a meaningful topic name for a cluster using LLM."""
        
        if not articles:
            return "AI News"
        
        # Use LLM for intelligent topic naming if available
        if self.llm_router:
            try:
                # Prepare article titles and summaries for LLM analysis
                article_summaries = []
                for article in articles[:3]:  # Use top 3 articles to avoid token limits
                    raw_article = article.summarized_article.filtered_article.raw_article
                    summary_points = []
                    
                    if (article.summarized_article and 
                        article.summarized_article.summary and 
                        article.summarized_article.summary.summary_points):
                        summary_points = article.summarized_article.summary.summary_points[:2]  # First 2 points
                    
                    article_summary = {
                        "title": raw_article.title,
                        "source": raw_article.source_id,
                        "summary_points": summary_points
                    }
                    article_summaries.append(article_summary)
                
                # Create prompt for topic name generation
                articles_text = ""
                for i, article in enumerate(article_summaries, 1):
                    articles_text += f"\n{i}. 【{article['source']}】{article['title']}"
                    if article['summary_points']:
                        articles_text += f"\n   要点: {' / '.join(article['summary_points'][:2])}"
                
                prompt = f"""以下の関連記事群に最適な統一トピック名を生成してください。

記事一覧:{articles_text}

要件:
- 3-6語の簡潔な日本語で表現
- 記事の共通テーマを正確に表現
- 具体的で分かりやすい名称
- 「AI」「ニュース」のような一般用語は避ける
- 企業名は1つだけ含める場合のみ使用

例：
✓ 良い例: "OpenAIの新機能発表"、"量子コンピューティング進展"、"自動運転安全性議論"
✗ 悪い例: "With & Emergence"、"AI News"、"最新ニュース"

トピック名のみ回答してください："""

                # Generate topic name using LLM
                topic_name = await self.llm_router.generate_simple_text(
                    prompt=prompt,
                    model=self.settings.llm.topic_naming_model
                )
                
                if topic_name and topic_name.strip():
                    # Clean up the response
                    topic_name = topic_name.strip().replace('"', '').replace("'", "")
                    # Validate length and content
                    if 3 <= len(topic_name) <= 30 and not any(bad_word in topic_name.lower() for bad_word in ['ai news', 'ニュース', 'news']):
                        logger.info(f"LLM generated topic name: {topic_name}")
                        return topic_name
                    else:
                        logger.warning(f"LLM topic name validation failed: {topic_name}")
                
            except Exception as e:
                logger.warning(f"LLM topic name generation failed: {e}")
        
        # Fallback to improved keyword-based approach
        return self._generate_fallback_topic_name(articles)
    
    def _generate_fallback_topic_name(self, articles: List[ProcessedArticle]) -> str:
        """Generate fallback topic name using improved keyword analysis."""
        
        # Extract meaningful terms from titles
        important_terms = []
        company_names = []
        
        for article in articles:
            raw_article = article.summarized_article.filtered_article.raw_article
            title = raw_article.title
            
            # Extract company/organization names (capitalized words)
            import re
            capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', title)
            for word in capitalized_words:
                if len(word) > 2 and word not in ['AI', 'The', 'New', 'And']:
                    company_names.append(word)
            
            # Extract key technical terms
            tech_terms = re.findall(r'\b(?:quantum|neural|machine learning|deep learning|llm|gpt|claude|gemini|model|algorithm|data|security|robotics|autonomous|blockchain)\b', title.lower())
            important_terms.extend(tech_terms)
        
        # Find most common elements
        from collections import Counter
        
        if company_names:
            company_counter = Counter(company_names)
            top_company = company_counter.most_common(1)[0][0]
            
            if important_terms:
                term_counter = Counter(important_terms)
                top_term = term_counter.most_common(1)[0][0]
                return f"{top_company}の{top_term.title()}"
            else:
                return f"{top_company}関連"
        
        elif important_terms:
            term_counter = Counter(important_terms)
            top_terms = [term for term, count in term_counter.most_common(2)]
            if len(top_terms) >= 2:
                return f"{top_terms[0].title()}・{top_terms[1].title()}"
            else:
                return f"{top_terms[0].title()}技術"
        
        # Final fallback based on source
        sources = [article.summarized_article.filtered_article.raw_article.source_id for article in articles]
        source_counter = Counter(sources)
        top_source = source_counter.most_common(1)[0][0]
        return f"{top_source.title()}関連"
    
    def _calculate_cluster_confidence(self, embeddings: np.ndarray) -> float:
        """Calculate confidence score for a cluster based on embedding similarity."""
        
        if len(embeddings) < 2:
            return 1.0
        
        try:
            # Calculate pairwise similarities
            similarities = cosine_similarity(embeddings)
            
            # Get upper triangle (excluding diagonal)
            n = len(embeddings)
            similarity_values = []
            
            for i in range(n):
                for j in range(i + 1, n):
                    similarity_values.append(similarities[i][j])
            
            # Return average similarity as confidence
            return float(np.mean(similarity_values)) if similarity_values else 1.0
            
        except Exception as e:
            logger.warning("Failed to calculate cluster confidence", error=str(e))
            return 0.5

    async def identify_multi_source_topics(self, articles: List[ProcessedArticle]) -> Dict[str, Dict]:
        """
        Identify important topics, prioritizing those covered by multiple sources,
        using a direct pairwise similarity approach for robustness.
        
        Returns:
            Dict[topic_id, topic_data]: A dictionary of topics and their detailed data.
        """
        logger.info("Identifying multi-source topics using pairwise similarity.", total_articles=len(articles))
        if len(articles) < 2:
            return {}

        embeddings = await self._generate_article_embeddings(articles)
        
        valid_articles = [art for art, emb in zip(articles, embeddings) if emb is not None]
        valid_embeddings = np.array([emb for emb in embeddings if emb is not None])

        if len(valid_articles) < 2:
            return {}

        # Use density-based clustering for more accurate topic detection
        if HDBSCAN_AVAILABLE and len(valid_embeddings) >= 5:
            # Use HDBSCAN for robust density-based clustering
            logger.info("Using HDBSCAN density-based clustering for topic detection")
            
            # Convert cosine similarity to distance for HDBSCAN. Ensure dtype matches HDBSCAN expectation.
            distance_matrix = (1 - cosine_similarity(valid_embeddings)).astype(np.double)
            
            # Configure HDBSCAN with relaxed parameters for better clustering
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=2,  # Minimum articles per cluster
                min_samples=1,       # Minimum samples to form dense region
                metric='precomputed', # Use our precomputed distance matrix
                cluster_selection_epsilon=0.4,  # Relaxed from 0.3 for more clusters
                cluster_selection_method='leaf'  # More conservative clustering
            )
            
            cluster_labels = clusterer.fit_predict(distance_matrix)
            
            # Group articles by cluster labels
            groups = []
            for cluster_id in set(cluster_labels):
                if cluster_id == -1:  # HDBSCAN noise points (ungrouped articles)
                    continue
                cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
                if len(cluster_indices) >= 2:  # Only keep multi-article clusters
                    groups.append(cluster_indices)
                    
            logger.info(f"HDBSCAN identified {len(groups)} high-quality clusters from {len(valid_articles)} articles")
            
        else:
            # Fallback to improved direct similarity approach (no transitive closure)
            logger.info("Using improved direct similarity clustering (HDBSCAN not available)")
            
            # Calculate pairwise similarity matrix
            sim_matrix = cosine_similarity(valid_embeddings)
            np.fill_diagonal(sim_matrix, 0) # Ignore self-similarity

            # HDBSCAN expects a distance matrix, and it must be of type double.
            distance_matrix = (1 - sim_matrix).astype(np.double)
            
            # Use configurable threshold from settings, much more lenient for multi-source detection
            similarity_threshold = self.settings.embedding.multi_source_detection_threshold
            
            groups = []
            processed_indices = set()

            for i in range(len(valid_articles)):
                if i in processed_indices:
                    continue

                # Find all articles DIRECTLY similar to the current one (NO transitive closure)
                similar_indices = np.where(sim_matrix[i] > similarity_threshold)[0]
                
                if len(similar_indices) > 0:
                    # Only group articles that are DIRECTLY similar to the current article
                    # This eliminates the dangerous transitive closure that caused citation mix-ups
                    current_group_indices = {i} | set(similar_indices)
                    
                    # CRITICAL: Remove transitive closure expansion to prevent unrelated article grouping
                    # Previous logic caused "Meta research" + "AI business" + "LinkedIn hiring" groupings
                    # Now: only articles directly similar to article[i] are grouped together
                    
                    groups.append(list(current_group_indices))
                    processed_indices.update(current_group_indices)

        # Build topic data from groups with semantic validation
        topics = {}
        topic_id_counter = 0
        for group_indices in groups:
            cluster_articles = [valid_articles[i] for i in group_indices]
            
            unique_sources = {art.summarized_article.filtered_article.raw_article.source_id for art in cluster_articles}
            
            # Relaxed criteria: Allow single-source clusters if they have multiple articles
            # This ensures we get citations even when data is from similar sources
            if len(unique_sources) < 2 and len(cluster_articles) < 3:
                continue

            # CRITICAL: Semantic validation to ensure cluster coherence (relaxed threshold)
            cluster_embeddings = np.array([valid_embeddings[i] for i in group_indices])
            is_coherent_cluster, filtered_articles, filtered_embeddings = self._validate_cluster_coherence(
                cluster_articles, cluster_embeddings, coherence_threshold=0.75  # Balanced for quality and quantity
            )
            
            if not is_coherent_cluster or len(filtered_articles) < 2:
                logger.warning(f"Rejected incoherent cluster with {len(cluster_articles)} articles")
                continue
                
            # Use filtered, validated articles
            cluster_articles = filtered_articles
            cluster_embeddings = filtered_embeddings
            unique_sources = {art.summarized_article.filtered_article.raw_article.source_id for art in cluster_articles}
            
            # Relaxed recheck: Accept if we have multiple articles even from same source
            if len(unique_sources) < 2 and len(cluster_articles) < 3:
                continue

            representative_article = self._select_representative_article(cluster_articles)
            topic_name = await self._generate_topic_name(cluster_articles)
            
            confidence_score = self._calculate_cluster_confidence(cluster_embeddings)

            importance_score = self._calculate_topic_importance(
                unique_sources, 
                cluster_articles, 
                confidence_score
            )
            
            topic_id = f"multi_source_{topic_id_counter}"
            topics[topic_id] = {
                'articles': cluster_articles,
                'sources': list(unique_sources),
                'topic_title': topic_name,
                'importance_score': importance_score,
                'confidence_score': confidence_score,
                'representative_article': representative_article,
                'source_count': len(unique_sources),
                'article_count': len(cluster_articles)
            }
            topic_id_counter += 1
            logger.info(f"Validated and accepted multi-source topic '{topic_name}' with {len(unique_sources)} sources.")

        # Sort topics by importance
        sorted_topics = dict(sorted(
            topics.items(), 
            key=lambda x: x[1]['importance_score'], 
            reverse=True
        ))

        return sorted_topics

    def _validate_cluster_coherence(
        self, 
        cluster_articles: List[ProcessedArticle], 
        cluster_embeddings: np.ndarray,
        coherence_threshold: float = 0.75
    ) -> Tuple[bool, List[ProcessedArticle], np.ndarray]:
        """
        Validate semantic coherence of a cluster and filter out outliers.
        
        Args:
            cluster_articles: Articles in the cluster
            cluster_embeddings: Embeddings for the articles
            coherence_threshold: Minimum average similarity within cluster
            
        Returns:
            Tuple of (is_coherent, filtered_articles, filtered_embeddings)
        """
        if len(cluster_articles) < 2:
            return False, [], np.array([])
            
        # CRITICAL: Domain-based semantic validation before similarity checks
        if not self._validate_topic_domain_coherence(cluster_articles):
            logger.info(f"Rejected cluster due to topic domain incoherence: {[a.summarized_article.filtered_article.raw_article.title[:30] + '...' for a in cluster_articles]}")
            return False, [], np.array([])
        
        # Calculate pairwise similarities within cluster
        similarities = cosine_similarity(cluster_embeddings)
        np.fill_diagonal(similarities, 0)  # Ignore self-similarity
        
        # Calculate average similarity for each article to others in cluster
        avg_similarities = np.mean(similarities, axis=1)
        
        # Overall cluster coherence
        overall_coherence = np.mean(avg_similarities)
        
        # Filter out articles that don't fit well with the cluster
        coherent_indices = np.where(avg_similarities >= coherence_threshold * 0.8)[0]  # Slightly lower threshold for individual articles
        
        if len(coherent_indices) < 2:
            # Not enough coherent articles
            return False, [], np.array([])
        
        filtered_articles = [cluster_articles[i] for i in coherent_indices]
        filtered_embeddings = cluster_embeddings[coherent_indices]
        
        # CRITICAL: Re-validate domain coherence after filtering
        if not self._validate_topic_domain_coherence(filtered_articles):
            logger.info(f"Rejected filtered cluster due to remaining domain incoherence")
            return False, [], np.array([])
        
        # Calculate final coherence score
        if len(coherent_indices) < len(cluster_articles):
            # Some articles were filtered out
            final_similarities = cosine_similarity(filtered_embeddings)
            np.fill_diagonal(final_similarities, 0)
            final_coherence = np.mean(final_similarities)
        else:
            final_coherence = overall_coherence
        
        is_coherent = final_coherence >= coherence_threshold
        
        logger.info(
            f"Cluster coherence validation: {len(cluster_articles)} → {len(filtered_articles)} articles, "
            f"coherence: {final_coherence:.3f} (threshold: {coherence_threshold})"
        )
        
        return is_coherent, filtered_articles, filtered_embeddings
    
    def _validate_topic_domain_coherence(self, articles: List[ProcessedArticle]) -> bool:
        """
        Validate that all articles in a cluster belong to the same topic domain.
        
        Args:
            articles: List of articles to validate
            
        Returns:
            True if articles are domain-coherent, False otherwise
        """
        if len(articles) < 2:
            return True
            
        # Define mutually exclusive topic domains
        topic_domains = {
            'hr_recruitment': ['hiring', 'recruitment', '採用', '人材', 'linkedin', '求人', 'job search', 'talent acquisition'],
            'research_technical': ['research', 'researcher', '研究', '技術', 'model', 'モデル', 'algorithm', 'api', 'technical'],
            'economic_policy': ['economy', 'economic', '経済', '失業', '雇用喪失', 'job losses', 'policy', '政策'],
            'business_finance': ['investment', 'funding', 'ipo', 'valuation', '投資', 'venture', 'startup', 'business'],
            'product_tools': ['cli', 'api', 'tool', 'ツール', 'product', '製品', 'feature', '機能'],
            'local_infrastructure': ['ollama', 'local', 'ローカル', 'infrastructure', 'self-hosted']
        }
        
        # Classify each article by domain
        article_domains = []
        for article in articles:
            raw_article = article.summarized_article.filtered_article.raw_article
            article_text = (raw_article.title + " " + (raw_article.content or "")).lower()
            
            detected_domains = []
            for domain, keywords in topic_domains.items():
                if any(keyword in article_text for keyword in keywords):
                    detected_domains.append(domain)
            
            article_domains.append(detected_domains)
        
        # Check for domain conflicts
        mutually_exclusive_pairs = [
            ('hr_recruitment', 'research_technical'),
            ('economic_policy', 'hr_recruitment'),
            ('business_finance', 'research_technical'),
            ('local_infrastructure', 'economic_policy'),
        ]
        
        for i, domains1 in enumerate(article_domains):
            for j, domains2 in enumerate(article_domains):
                if i >= j:
                    continue
                    
                for domain1 in domains1:
                    for domain2 in domains2:
                        for exclusive1, exclusive2 in mutually_exclusive_pairs:
                            if (domain1 == exclusive1 and domain2 == exclusive2) or \
                               (domain1 == exclusive2 and domain2 == exclusive1):
                                logger.info(
                                    f"Domain conflict detected: {domain1} vs {domain2} "
                                    f"between articles '{articles[i].summarized_article.filtered_article.raw_article.title[:50]}...' "
                                    f"and '{articles[j].summarized_article.filtered_article.raw_article.title[:50]}...'"
                                )
                                return False
        
        return True

    def _calculate_topic_importance(
        self, 
        unique_sources: set, 
        articles: List[ProcessedArticle], 
        confidence_score: float
    ) -> float:
        """
        トピックの重要度スコアを計算
        
        Args:
            unique_sources: 異なるソースのセット
            articles: トピックに関連する記事リスト
            confidence_score: クラスタリング信頼度
            
        Returns:
            重要度スコア (0.0-1.0)
        """
        # ソース多様性: 複数ソースほど重要
        source_diversity_score = min(len(unique_sources) / 5.0, 1.0)  # 5ソース以上で最大
        
        # 記事数: より多くの記事があるトピックが重要
        article_count_score = min(len(articles) / 10.0, 0.5)  # 最大0.5, 10記事以上で最大
        
        # ソース品質: 高品質ソースからの記事は重要度が高い
        high_quality_sources = {
            'openai_news', 'anthropic_news', 'google_research_blog', 
            'the_decoder', 'semianalysis', 'stratechery'
        }
        
        quality_bonus = 0.0
        for source in unique_sources:
            if source in high_quality_sources:
                quality_bonus += 0.1
        quality_bonus = min(quality_bonus, 0.3)  # 最大0.3のボーナス
        
        # 記事の平均AI関連度
        total_relevance = 0.0
        for article in articles:
            relevance = article.summarized_article.filtered_article.ai_relevance_score
            total_relevance += relevance
        
        avg_relevance = total_relevance / len(articles) if articles else 0.0
        relevance_score = avg_relevance * 0.3  # 最大0.3の重み
        
        # 最終スコア計算
        final_score = (
            source_diversity_score * 0.4 +  # ソース多様性が最重要
            article_count_score * 0.2 +     # 記事数
            confidence_score * 0.2 +        # クラスタリング信頼度
            relevance_score * 0.2 +         # AI関連度
            quality_bonus                    # 品質ボーナス
        )
        
        return min(final_score, 1.0)

    def _generate_topic_title(self, articles: List[ProcessedArticle]) -> str:
        """クラスター記事から代表的なトピックタイトルを生成"""
        titles = []
        for article in articles:
            title = article.summarized_article.filtered_article.raw_article.title
            titles.append(title)
        
        # 最も多く言及されるキーワードからタイトル生成
        words = []
        for title in titles:
            words.extend(title.lower().split())
        
        word_freq = {}
        for word in words:
            if len(word) > 3:  # 短い単語は除外
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 最頻出単語でタイトル作成
        if word_freq:
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            return " ".join([word.title() for word, _ in top_words])
        else:
            if articles:
                return articles[0].summarized_article.filtered_article.raw_article.title
            else:
                return "Unknown Topic"


async def cluster_articles_with_multi_source_priority(
    articles: List[ProcessedArticle],
    max_articles_target: int = 7
) -> List[ProcessedArticle]:
    """
    Multi-source topic prioritization for newsletter generation.
    
    Args:
        articles: Input processed articles
        max_articles_target: Maximum articles to include in newsletter
        
    Returns:
        Prioritized articles with multi-source topics first
    """
    
    clusterer = TopicClusterer()
    
    # Identify multi-source topics
    multi_source_topics = await clusterer.identify_multi_source_topics(articles)
    
    final_articles = []
    articles_added = 0
    
    # Add articles from multi-source topics first (highest priority)
    for topic_id, topic_data in multi_source_topics.items():
        if articles_added >= max_articles_target:
            break
            
        representative = topic_data['representative_article']
        
        # Only enhance multi-source topics
        if 'multi_source' in topic_id:
            # Mark as multi-source for consolidation
            representative.is_multi_source = True
            
            # --- multi-source enhancement情報を代表記事に埋め込む ---
            # 1) Filter only truly related articles (> 0.75 AI relevance) and ensure source diversity
            high_relevance_articles = [
                art for art in topic_data['articles']
                if art.summarized_article.filtered_article.ai_relevance_score > 0.75
            ]
            
            # 2) F-15 compliance: Ensure different sources for citations
            used_sources = {representative.summarized_article.filtered_article.raw_article.source_id}
            diverse_articles = [representative]  # Start with representative
            
            for article in high_relevance_articles:
                source_id = article.summarized_article.filtered_article.raw_article.source_id
                if source_id not in used_sources and len(diverse_articles) < 3:
                    diverse_articles.append(article)
                    used_sources.add(source_id)
            
            # If we don't have enough diverse sources, fill with any high relevance articles
            if len(diverse_articles) < 3:
                for article in high_relevance_articles:
                    if article not in diverse_articles and len(diverse_articles) < 3:
                        diverse_articles.append(article)
            
            # 3) Sort by AI relevance and take top articles (ensuring representative is first)
            top_articles = diverse_articles[:3]

            representative.source_urls = [
                art.summarized_article.filtered_article.raw_article.url for art in top_articles
            ]

            # 4) 集約処理用に上位記事を保存
            #    後段で NewsletterGenerator が参照したあとに削除することで循環参照を防止する
            representative._multi_articles_tmp = top_articles  # private 属性扱い
            
            logger.info(
                f"Enhanced multi-source topic with {len(used_sources)} different sources",
                topic_title=topic_data['topic_title'],
                sources_used=list(used_sources)
            )
        
        final_articles.append(representative)
        articles_added += 1
        
        logger.info(
            "Added topic to newsletter",
            topic_title=topic_data['topic_title'],
            importance=topic_data['importance_score'],
            sources=topic_data['source_count'],
            multi_source='multi_source' in topic_id
        )
    
    # If we still need more articles, add remaining high-quality singles
    if articles_added < max_articles_target:
        remaining_articles = []
        added_article_ids = {a.summarized_article.filtered_article.raw_article.id for a in final_articles}
        
        for article in articles:
            article_id = article.summarized_article.filtered_article.raw_article.id
            if article_id not in added_article_ids:
                remaining_articles.append(article)
        
        # Sort remaining by AI relevance and add up to target
        remaining_articles.sort(
            key=lambda a: a.summarized_article.filtered_article.ai_relevance_score,
            reverse=True
        )
        
        needed_articles = max_articles_target - articles_added
        selected_remaining = remaining_articles[:needed_articles]
        
        # For single articles, try to find related sources for better citations
        for article in selected_remaining:
            # Find similar articles that could serve as related sources
            similar_articles = []
            for potential_related in articles:
                if (potential_related != article and 
                    potential_related.summarized_article.filtered_article.raw_article.id not in added_article_ids):
                    # Simple similarity check based on title keywords
                    article_title = article.summarized_article.filtered_article.raw_article.title.lower()
                    potential_title = potential_related.summarized_article.filtered_article.raw_article.title.lower()
                    
                    # Check for common keywords (simple heuristic)
                    article_words = set(article_title.split())
                    potential_words = set(potential_title.split())
                    common_words = article_words.intersection(potential_words)
                    
                    # If they share significant words, consider them related
                    if len(common_words) >= 2 and any(len(word) > 3 for word in common_words):
                        similar_articles.append(potential_related)
            
            # Store up to 2 related articles for citation purposes
            if similar_articles:
                article._related_articles_tmp = similar_articles[:2]
        
        final_articles.extend(selected_remaining)
    
    logger.info(
        "Multi-source prioritization completed",
        total_articles=len(final_articles),
        multi_source_topics=len([t for t in multi_source_topics if 'multi_source' in t]),
        single_source_topics=len([t for t in multi_source_topics if 'single_source' in t])
    )
    
    return final_articles

async def cluster_articles_for_newsletter(
    articles: List[ProcessedArticle],
    max_clusters: int = 5,
    max_articles_per_cluster: int = 3
) -> List[ProcessedArticle]:
    """
    Cluster articles and return final selection for newsletter.
    
    Args:
        articles: Input processed articles
        max_clusters: Maximum number of topic clusters
        max_articles_per_cluster: Maximum articles to include per cluster
        
    Returns:
        Final selection of articles with clustering metadata
    """
    
    clusterer = TopicClusterer()
    
    # Perform clustering
    clusters = await clusterer.cluster_articles(
        articles=articles,
        max_clusters=max_clusters,
        min_cluster_size=2
    )
    
    final_articles = []
    
    for cluster in clusters:
        # Add representative article with enhanced citations
        rep_article = cluster.representative_article
        
        # Add citations from cluster
        citations = cluster.get_citations(max_citations=3)
        rep_article.citations = citations
        
        # Add cluster metadata
        if hasattr(rep_article.summarized_article.filtered_article.raw_article, 'metadata'):
            rep_article.summarized_article.filtered_article.raw_article.metadata.update({
                'topic_cluster': cluster.topic_name,
                'cluster_confidence': cluster.confidence_score,
                'cluster_size': cluster.article_count
            })
        
        final_articles.append(rep_article)
        
        # Add related articles if space allows
        articles_from_cluster = 1
        for related_article in cluster.related_articles:
            if articles_from_cluster >= max_articles_per_cluster:
                break
            
            # Add minimal citations for related articles
            related_citations = [citations[0]]  # Just the main source
            related_article.citations = related_citations
            
            final_articles.append(related_article)
            articles_from_cluster += 1
    
    # Limit total articles for newsletter
    max_newsletter_articles = 10
    final_articles = final_articles[:max_newsletter_articles]
    
    logger.info(
        "Newsletter clustering completed",
        input_articles=len(articles),
        clusters_created=len(clusters),
        final_articles=len(final_articles)
    )
    
    return final_articles