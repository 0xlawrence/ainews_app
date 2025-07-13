"""
AI relevance filtering for news articles.

This module implements filtering logic to identify AI-related content
using keyword matching and scoring algorithms.
"""

import re

from src.models.schemas import FilteredArticle, RawArticle
from src.utils.logger import setup_logging

logger = setup_logging()


class AIContentFilter:
    """Filters articles based on AI relevance."""

    def __init__(self):
        """Initialize the AI content filter with keyword sets."""

        # High-priority AI keywords (higher weight)
        self.high_priority_keywords = {
            # Core AI terms
            "artificial intelligence", "ai", "machine learning", "ml", "deep learning",
            "neural network", "transformer", "llm", "large language model",

            # AI Companies/Products
            "openai", "gpt", "chatgpt", "claude", "anthropic", "gemini", "bard",
            "copilot", "github copilot", "midjourney", "stable diffusion",
            "dall-e", "dalle", "hugging face", "langchain",

            # AI Techniques
            "natural language processing", "nlp", "computer vision", "cv",
            "reinforcement learning", "rl", "generative ai", "gan",
            "diffusion model", "attention mechanism", "embedding",
            "fine-tuning", "prompt engineering", "rlhf",

            # AI Applications
            "ai assistant", "chatbot", "voice assistant", "ai model",
            "ai training", "ai inference", "ai safety", "ai alignment",
            "ai automated", "ai automation", "intelligent ai", "smart ai",

            # Human-Centered AI & Behavioral AI
            "empathetic", "empathy", "emotion", "emotional", "emotional intelligence",
            "sentiment analysis", "affective computing", "behavioral", "behavior",
            "human-centered ai", "human-ai interaction", "social ai", "conversational ai",
            "dialogue", "personality", "persona", "tone", "communication",
            "user experience", "ux", "human-computer interaction", "hci",
            "psychology", "psychological", "social", "interpersonal",

            # Japanese AI terms
            "人工知能", "機械学習", "深層学習", "ニューラルネットワーク",
            "自然言語処理", "チャットボット", "生成ai", "生成AI"
        }

        # Medium-priority AI keywords
        self.medium_priority_keywords = {
            "algorithm", "data science", "analytics", "prediction", "classification",
            "clustering", "regression", "supervised learning", "unsupervised learning",
            "feature engineering", "model training", "inference", "deployment",
            "edge computing", "cloud ai", "ai chip", "gpu", "tensor",
            "pytorch", "tensorflow", "keras", "scikit-learn", "pandas",
            "jupyter", "notebook", "api", "sdk", "framework",
            "optimization", "hyperparameter", "cross-validation",
            "bias", "fairness", "explainable", "interpretable",

            # Extended behavioral and applied AI
            "personalization", "recommendation", "cognitive", "simulation",
            "speech recognition", "text-to-speech", "multimodal", "reasoning",
            "knowledge graph", "semantic", "contextual", "adaptive",
            "interactive", "responsive", "intuitive", "assistance"
        }

        # Low-priority AI keywords (context dependent)
        self.low_priority_keywords = {
            "technology", "tech", "software", "programming", "coding",
            "development", "innovation", "digital", "data", "analytics",
            "platform", "service", "application", "system", "solution",
            "research", "science", "academic", "paper", "study",
            "startup", "company", "product", "business", "industry",
            "future", "trend", "advancement", "breakthrough", "discovery"
        }

        # Negative keywords (reduce relevance) - reduced to avoid false negatives
        self.negative_keywords = {
            "blockchain", "cryptocurrency", "bitcoin", "crypto", "nft",
            "web3", "defi", "metaverse", "gaming", "game", "sports",
            "entertainment", "music", "fashion", "food", "travel",
            "politics", "election", "weather", "finance", "banking",
            "real estate", "property", "automobile", "car",
            # iPhone/mobile development keywords that are not AI-related
            "tailscale", "ssh", "termius", "iphone setup", "mac setup",
            "network configuration", "mobile development", "ios development",
            "xcode", "swift", "objective-c", "terminal setup"
        }

        # High-value keywords with significant bonus
        self.high_priority_keywords.update({
            'gpt-5', 'gpt-4.5', 'gpt-4o', 'gemini 2.5', 'claude 3.7', 'llama 4',
            'agi', 'artificial general intelligence', 'sora', 'superintelligence',
            '自主性ai', '汎用人工知能', 'モデル発表', '新モデル', '次世代ai'
        })

        # Penalty keywords for non-core AI topics
        self.penalty_keywords = {
            'drone', 'uav', 'military', '軍事', 'ドローン', '地政学', 'geopolitical'
        }

        # STRICT BLACKLIST: Articles with these keywords are immediately rejected
        self.blacklist_keywords = {
            # Product reviews and consumer goods
            '上履き', 'キャリオット', 'レビュー・口コミ', '商品レビュー', '製品テスト',
            '洗えて使いやすい', '実力を徹底検証', '使用感', '耐久性',

            # Fashion and lifestyle
            'ファッション', '衣類', 'アクセサリー', '美容', '化粧品', 'スキンケア',
            '料理', 'レシピ', '食材', 'グルメ', 'レストラン',

            # Travel and leisure
            '旅行', '観光地', 'ホテル', '航空券', '宿泊予約',

            # Sports and entertainment
            'スポーツ', '野球', 'サッカー', 'バスケ', '選手', '試合結果',

            # Shoes and clothing specifically
            '靴', '履物', 'シューズ', 'スニーカー', 'ブーツ', 'サンダル',
            'キッズ', '子供用品', '子供靴', 'ホワイト', '15cm',

            # Home appliances (non-AI)
            'ファン', '扇風機', 'ヒートプロテクタント', 'スプレー', 'ヘアケア',

            # Business process articles without AI context
            '週次レビュー', 'PDCA', '振り返り', 'レポート自動化', '業務改善',
            'KPI分析', 'ダッシュボード', '業務プロセス', 'ワークフロー改善',
            'PDCAサイクル', 'PDCA高速化', '形骸化', '振り返りが３分', '自動レポート'
        }

        # Compile regex patterns for efficiency
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for keyword matching."""

        def create_pattern(keywords: set[str]) -> re.Pattern:
            # Sort by length (longest first) to avoid partial matches
            sorted_keywords = sorted(keywords, key=len, reverse=True)
            escaped_keywords = [re.escape(kw) for kw in sorted_keywords]
            pattern = r'\b(?:' + '|'.join(escaped_keywords) + r')\b'
            return re.compile(pattern, re.IGNORECASE)

        self.high_pattern = create_pattern(self.high_priority_keywords)
        self.medium_pattern = create_pattern(self.medium_priority_keywords)
        self.low_pattern = create_pattern(self.low_priority_keywords)
        self.negative_pattern = create_pattern(self.negative_keywords)
        self.penalty_pattern = create_pattern(self.penalty_keywords)
        self.blacklist_pattern = create_pattern(self.blacklist_keywords)

    def filter_articles(
        self,
        articles: list[RawArticle],
        relevance_threshold: float = 0.7,
        min_articles_target: int = 5,
        dynamic_threshold: bool = True
    ) -> list[FilteredArticle]:
        """
        Filter articles based on AI relevance with dynamic threshold adjustment.

        Args:
            articles: List of raw articles to filter
            relevance_threshold: Initial minimum relevance score to pass
            min_articles_target: Minimum number of articles to try to achieve
            dynamic_threshold: Whether to lower threshold if too few articles pass

        Returns:
            List of filtered articles that passed the threshold
        """

        logger.info(
            "Starting AI relevance filtering",
            total_articles=len(articles),
            threshold=relevance_threshold,
            min_target=min_articles_target,
            dynamic_enabled=dynamic_threshold
        )

        # First pass with original threshold
        filtered_articles = []
        article_scores = []  # Store (article, score, keywords, reason) for potential second pass

        for article in articles:
            try:
                relevance_score, keywords, reason = self._calculate_relevance(article)

                # Store all scored articles for potential dynamic threshold adjustment
                article_scores.append((article, relevance_score, keywords, reason))

                if relevance_score >= relevance_threshold:
                    filtered_article = FilteredArticle(
                        raw_article=article,
                        ai_relevance_score=relevance_score,
                        ai_keywords=keywords,
                        filter_reason=reason
                    )
                    filtered_articles.append(filtered_article)

                    logger.debug(
                        "Article passed AI filter",
                        article_id=article.id,
                        score=relevance_score,
                        keywords=keywords[:5]  # Log first 5 keywords
                    )

            except Exception as e:
                logger.error(
                    "Error filtering article",
                    article_id=article.id,
                    error=str(e)
                )
                continue

        # Dynamic threshold adjustment if too few articles passed
        if dynamic_threshold and len(filtered_articles) < min_articles_target and len(article_scores) > 0:
            # Sort articles by score and select top candidates
            article_scores.sort(key=lambda x: x[1], reverse=True)  # Sort by relevance_score

            # Calculate new threshold to get desired number of articles
            target_articles = min(min_articles_target, len(article_scores))
            if target_articles > len(filtered_articles):
                # Find the score that would give us the target number of articles
                new_threshold = article_scores[target_articles - 1][1]  # Score of the target_articles-th article
                new_threshold = max(0.15, new_threshold)  # Minimum 15% to prevent non-AI articles

                logger.info(
                    "Applying dynamic threshold adjustment",
                    original_threshold=relevance_threshold,
                    new_threshold=new_threshold,
                    original_count=len(filtered_articles),
                    target_count=target_articles
                )

                # Add articles that now pass with the lower threshold
                for article, score, keywords, reason in article_scores:
                    if score >= new_threshold and score < relevance_threshold:
                        filtered_article = FilteredArticle(
                            raw_article=article,
                            ai_relevance_score=score,
                            ai_keywords=keywords,
                            filter_reason=f"{reason} [Dynamic threshold: {new_threshold:.3f}]"
                        )
                        filtered_articles.append(filtered_article)

                        logger.debug(
                            "Article added via dynamic threshold",
                            article_id=article.id,
                            score=score,
                            new_threshold=new_threshold
                        )

        logger.info(
            "AI filtering completed",
            passed_articles=len(filtered_articles),
            filtered_out=len(articles) - len(filtered_articles),
            pass_rate=f"{len(filtered_articles)/len(articles)*100:.1f}%"
        )

        return filtered_articles

    def _calculate_relevance(self, article: RawArticle) -> tuple[float, list[str], str]:
        """
        Calculate AI relevance score for an article.

        Args:
            article: Raw article to analyze

        Returns:
            Tuple of (relevance_score, found_keywords, reason)
        """

        # Combine title and content for analysis
        text = f"{article.title} {article.content}".lower()

        # CRITICAL: Check blacklist first - immediate rejection
        blacklist_matches = self.blacklist_pattern.findall(text)
        if blacklist_matches:
            logger.debug(f"Article rejected due to blacklist keywords: {blacklist_matches[:3]} in '{article.title[:50]}...'")
            return 0.0, [], f"Blacklisted content detected: {', '.join(blacklist_matches[:3])}"

        # Find keyword matches
        high_matches = self.high_pattern.findall(text)
        medium_matches = self.medium_pattern.findall(text)
        low_matches = self.low_pattern.findall(text)
        negative_matches = self.negative_pattern.findall(text)
        penalty_matches = self.penalty_pattern.findall(text)

        # Enhanced YouTube processing with channel-specific handling
        youtube_ai_bonus = 0.0
        youtube_penalty = 0.0

        if hasattr(article, 'source_type') and article.source_type == 'youtube':
            # Check for YouTube Shorts - only exclude obvious shorts
            if any(indicator in str(article.url).lower() for indicator in ['shorts/', '/shorts']):
                logger.debug(f"YouTube Shorts detected, filtering out: {article.title}")
                return 0.0, [], "YouTube Shorts are excluded from newsletter"

            # More targeted title check for shorts
            if any(indicator in article.title.lower() for indicator in ['#shorts', '[shorts]']):
                logger.debug(f"YouTube Shorts detected in title, filtering out: {article.title}")
                return 0.0, [], "YouTube Shorts are excluded from newsletter"

            source_id = getattr(article, 'source_id', '').lower()

            # High-value AI specialist channels
            high_value_ai_channels = {
                'anthropic', 'openai', 'googledeepmind'
            }

            # Medium-value AI-related channels
            medium_value_ai_channels = {
                'lexfridman'
            }

            # Business/VC channels requiring stricter AI relevance
            business_channels = {
                'ycombinator', 'a16z', 'sequoia', 'lennys_podcast'
            }

            if any(channel in source_id for channel in high_value_ai_channels):
                youtube_ai_bonus = 0.6  # Increased from 0.4 to 0.6 for specialist channels
                logger.debug(f"High-value AI channel bonus applied: {source_id}")

            elif any(channel in source_id for channel in medium_value_ai_channels):
                youtube_ai_bonus = 0.35  # Increased from 0.25 to 0.35 for AI-adjacent channels
                logger.debug(f"Medium-value AI channel bonus applied: {source_id}")

            elif any(channel in source_id for channel in business_channels):
                # Business channels: more lenient evaluation
                if not high_matches and not medium_matches:
                    youtube_penalty = -0.2  # Reduced penalty from -0.3 to -0.2
                    logger.debug(f"Business channel penalty applied (no AI keywords): {source_id}")
                elif high_matches:
                    youtube_ai_bonus = 0.25  # Increased from 0.15 to 0.25 for high-priority AI content
                    logger.debug(f"Business channel high AI bonus applied: {source_id}")
                elif medium_matches:
                    youtube_ai_bonus = 0.15  # Increased from 0.05 to 0.15 for medium-priority AI content
                    logger.debug(f"Business channel medium AI bonus applied: {source_id}")

            # Detect non-AI content patterns
            youtube_negative_keywords = {
                'interview about', 'personal journey', 'lifestyle', 'motivation',
                'general business', 'fundraising tips', 'networking', 'career advice',
                'company culture', 'leadership', 'management', 'hiring'
            }

            # More sophisticated negative content detection
            negative_content_score = 0
            for neg_keyword in youtube_negative_keywords:
                if neg_keyword in text.lower():
                    negative_content_score += 1

            # Apply penalty for non-AI content, especially if no AI keywords found
            if negative_content_score > 0 and len(high_matches) == 0:
                return 0.15, [], f"YouTube non-AI content detected: {negative_content_score} negative patterns"
            elif negative_content_score > 2:  # Multiple negative patterns
                youtube_penalty -= 0.2

        # Calculate source quality bonus based on domain reputation
        source_quality_bonus = self._calculate_source_quality_bonus(article)

        # Calculate base score
        high_score = len(set(high_matches)) * 3.0    # High weight
        medium_score = len(set(medium_matches)) * 1.5  # Medium weight
        low_score = len(set(low_matches)) * 0.5        # Low weight
        negative_score = len(set(negative_matches)) * -1.0  # Negative weight

        raw_score = high_score + medium_score + low_score + negative_score + youtube_ai_bonus + youtube_penalty + source_quality_bonus

        # Apply text length normalization
        text_length = len(text.split())
        if text_length > 0:
            normalized_score = raw_score / (text_length / 100)  # Per 100 words
        else:
            normalized_score = 0.0

        # Ensure score is between 0 and 1
        final_score = max(0.0, min(1.0, normalized_score))

        # Collect all found keywords
        all_keywords = list(set(high_matches + medium_matches + low_matches))

        # Generate reason
        reason = self._generate_filter_reason(
            final_score, high_matches, medium_matches, low_matches, negative_matches
        )

        return final_score, all_keywords, reason

    def _generate_filter_reason(
        self,
        score: float,
        high_matches: list[str],
        medium_matches: list[str],
        low_matches: list[str],
        negative_matches: list[str]
    ) -> str:
        """Generate human-readable reason for filtering decision."""

        if score >= 0.8:
            return f"High AI relevance: {len(set(high_matches))} high-priority keywords"
        elif score >= 0.6:
            return f"Good AI relevance: {len(set(high_matches))} high + {len(set(medium_matches))} medium keywords"
        elif score >= 0.4:
            return "Moderate AI relevance: Mix of AI-related terms"
        elif score >= 0.2:
            return "Low AI relevance: Few AI keywords, mostly general tech"
        else:
            neg_count = len(set(negative_matches))
            if neg_count > 0:
                return f"Non-AI content: {neg_count} negative keywords detected"
            else:
                return "Non-AI content: No significant AI keywords found"

    def _calculate_source_quality_bonus(self, article: RawArticle) -> float:
        """
        Calculate source quality bonus based on domain reputation.

        Args:
            article: Raw article to analyze

        Returns:
            Source quality bonus score (0.0 to 0.3)
        """
        try:
            # Import constants for domain checking
            try:
                from urllib.parse import urlparse

                from src.constants.mappings import OFFICIAL_DOMAINS, REPUTABLE_DOMAINS
            except ImportError:
                # Fallback to manual domain lists if constants not available
                OFFICIAL_DOMAINS = {
                    'openai.com', 'google.com', 'meta.com', 'anthropic.com',
                    'microsoft.com', 'apple.com', 'amazon.com', 'nvidia.com'
                }
                REPUTABLE_DOMAINS = {
                    'techcrunch.com', 'theverge.com', 'wired.com', 'venturebeat.com',
                    'arstechnica.com', 'engadget.com', 'zdnet.com', 'cnet.com'
                }
                from urllib.parse import urlparse

            # Extract domain from article URL
            if hasattr(article, 'url') and article.url:
                try:
                    parsed_url = urlparse(str(article.url))
                    domain = parsed_url.netloc.lower()

                    # Remove www. prefix
                    if domain.startswith('www.'):
                        domain = domain[4:]

                    # Check for official company domains (highest priority)
                    for official_domain in OFFICIAL_DOMAINS:
                        if official_domain in domain:
                            logger.debug(f"Official domain bonus applied: {domain}")
                            return 0.3  # 30% bonus for official sources

                    # Check for reputable news domains (medium priority)
                    for reputable_domain in REPUTABLE_DOMAINS:
                        if reputable_domain in domain:
                            logger.debug(f"Reputable domain bonus applied: {domain}")
                            return 0.15  # 15% bonus for reputable news sources

                    # Check for academic/research domains
                    academic_indicators = ['.edu', '.ac.', 'arxiv.org', 'research.', 'papers.']
                    for indicator in academic_indicators:
                        if indicator in domain:
                            logger.debug(f"Academic domain bonus applied: {domain}")
                            return 0.2  # 20% bonus for academic sources

                    # Check for known quality tech sources not in reputable list
                    additional_quality_domains = {
                        'spectrum.ieee.org', 'research.google', 'blog.google',
                        'huggingface.co', 'zenn.dev', 'github.com', 'medium.com'
                    }

                    for quality_domain in additional_quality_domains:
                        if quality_domain in domain:
                            logger.debug(f"Quality tech domain bonus applied: {domain}")
                            return 0.1  # 10% bonus for quality tech sources

                except Exception as url_error:
                    logger.debug(f"Failed to parse URL for source quality bonus: {url_error}")

            # Check source_id for special cases (e.g., YouTube channels)
            if hasattr(article, 'source_id'):
                source_id = str(article.source_id).lower()

                # High-quality YouTube channels already handled in YouTube processing
                # But add bonus for official RSS feeds
                official_source_ids = {
                    'openai_news', 'anthropic_news', 'google_research_blog',
                    'google_gemini_blog', 'huggingface_blog'
                }

                if source_id in official_source_ids:
                    logger.debug(f"Official source ID bonus applied: {source_id}")
                    return 0.25  # 25% bonus for official RSS feeds

                # Medium quality curated sources
                curated_source_ids = {
                    'the_decoder', 'ai_newsletter_saravia', 'semianalysis',
                    'tldr_ai', 'stratechery'
                }

                if source_id in curated_source_ids:
                    logger.debug(f"Curated source bonus applied: {source_id}")
                    return 0.1  # 10% bonus for curated AI sources

            return 0.0  # No bonus for unknown/unrecognized sources

        except Exception as e:
            logger.debug(f"Error calculating source quality bonus: {e}")
            return 0.0

    def get_keyword_stats(self) -> dict[str, int]:
        """Get statistics about keyword sets."""

        return {
            "high_priority": len(self.high_priority_keywords),
            "medium_priority": len(self.medium_priority_keywords),
            "low_priority": len(self.low_priority_keywords),
            "negative": len(self.negative_keywords),
            "total": (
                len(self.high_priority_keywords) +
                len(self.medium_priority_keywords) +
                len(self.low_priority_keywords) +
                len(self.negative_keywords)
            )
        }


def filter_ai_content(
    articles: list[RawArticle],
    relevance_threshold: float = 0.01,  # Lowered threshold to 1% to allow legitimate AI articles
    min_articles_target: int = 10,      # PRD-compliant target for 7-10 articles
    dynamic_threshold: bool = True
) -> list[FilteredArticle]:
    """
    Convenience function to filter articles for AI relevance.

    Args:
        articles: List of raw articles
        relevance_threshold: Minimum relevance score (lowered to 0.55)
        min_articles_target: Target minimum number of articles
        dynamic_threshold: Enable dynamic threshold adjustment

    Returns:
        List of filtered articles
    """

    filter_instance = AIContentFilter()
    return filter_instance.filter_articles(
        articles,
        relevance_threshold,
        min_articles_target,
        dynamic_threshold
    )
