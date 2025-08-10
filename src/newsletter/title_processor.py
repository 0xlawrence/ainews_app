"""
Title processing and generation for newsletter articles.

This module handles Japanese title generation, validation, formatting,
and quality checking for newsletter articles.
"""

import logging
import re
from typing import Any, Dict, Union, Optional

try:
    from src.models.schemas import ProcessedArticle
    from src.config.settings import get_settings
    from src.utils.text_processing import remove_duplicate_patterns, fix_inappropriate_period_insertions, fix_particle_duplication
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

logger = logging.getLogger(__name__)


class TitleProcessor:
    """Processor for generating and formatting newsletter article titles."""
    
    def __init__(self, llm_router=None):
        """Initialize title processor.
        
        Args:
            llm_router: Optional LLM router for advanced title generation
        """
        self.llm_router = llm_router
        if HAS_DEPENDENCIES:
            self.settings = get_settings()
        else:
            self.settings = None
        
        logger.info("Title Processor initialized")
    
    async def generate_article_title_integrated(
        self,
        article: 'ProcessedArticle',
        is_update: bool = False
    ) -> str:
        """
        Integrated title generation with proper update handling.

        Args:
            article: Processed article
            is_update: Whether this is an update article (determines emoji usage)

        Returns:
            Generated Japanese title with proper update handling
        """
        # First try LLM-based generation if available
        if self.llm_router:
            try:
                # LLM generates a base summary sentence
                base_summary = await self.llm_router.generate_japanese_title(article)

                if base_summary:
                    logger.debug(f"LLM generated base summary for title: {base_summary}")
                    # Apply integrated formatting with update context
                    return self.format_headline_integrated(base_summary, is_update)
            except Exception as e:
                logger.warning(f"LLM title generation failed, falling back: {e}")

        # Fallback to using the first summary point with integrated logic
        return self.generate_integrated_fallback_title(article, is_update)
    
    def validate_title_quality(self, title: str) -> Dict[str, Any]:
        """
        Validate title quality and detect common issues.

        Args:
            title: Generated title to validate

        Returns:
            Dictionary with validation results and suggested improvements
        """
        issues = []
        suggestions = []
        score = 100  # Start with perfect score

        # Check 1: Duplicate word patterns
        duplicate_patterns = [
            (r'(\w+)\s+\1\b', '同じ単語が連続しています'),
            # Fix broken Union[...] to proper alternation
            (r'(?:LLM|AI|GPT)の技術.*?(LLM|AI|GPT)', 'LLM/AI用語の重複があります'),
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
        emoji_count = len(re.findall(r'[😀-🿿☀-⟿]', title))
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
            'needs_improvement': len(issues) > 0
        }
    
    def improve_title_based_on_validation(self, title: str, validation_result: Dict[str, Any]) -> str:
        """
        Improve title based on validation results.

        Args:
            title: Original title
            validation_result: Result from validate_title_quality

        Returns:
            Improved title
        """
        improved_title = title

        # Fix duplicate patterns
        if any('重複' in issue for issue in validation_result.get('issues', [])):
            # Remove common duplicate patterns
            duplicate_fixes = [
                (r'(\w+)の技術\1', r'\1の技術'),
                (r'(AI|LLM|GPT).*?\1', r'\1'),
                (r'(\w+)\s+\1\b', r'\1')
            ]
            
            for pattern, replacement in duplicate_fixes:
                improved_title = re.sub(pattern, replacement, improved_title)

        # Fix incomplete titles
        if improved_title.endswith('...'):
            improved_title = improved_title.rstrip('.')

        # Apply text processing fixes
        if HAS_DEPENDENCIES:
            improved_title = remove_duplicate_patterns(improved_title)
            improved_title = fix_inappropriate_period_insertions(improved_title)
            improved_title = fix_particle_duplication(improved_title)

        # Limit emoji count
        emojis = re.findall(r'[😀-🿿☀-⟿]', improved_title)
        if len(emojis) > 2:
            # Keep only first 2 emojis
            for emoji in emojis[2:]:
                improved_title = improved_title.replace(emoji, '', 1)

        return improved_title.strip()
    
    async def generate_article_title(self, article: 'ProcessedArticle') -> str:
        """Generate title for an article using available methods."""
        is_update = getattr(article, 'is_update', False)
        # 1) まず通常生成
        title = await self.generate_article_title_integrated(article, is_update)

        # 2) 検証→改善
        validation = self.validate_title_quality(title)
        if validation.get('needs_improvement'):
            improved = self.improve_title_based_on_validation(title, validation)
            # 再検証
            revalidation = self.validate_title_quality(improved)
            if not revalidation.get('needs_improvement'):
                return improved

        # 3) フォールバック（特に短すぎ/汎用的すぎる場合）
        if not title or self.is_highly_generic_title(title):
            return self.generate_integrated_fallback_title(article, is_update)

        return title
    
    def format_headline_integrated(self, summary_sentence: str, is_update: bool) -> str:
        """
        Format headline with integrated update handling to prevent duplication.

        Args:
            summary_sentence: Base summary sentence
            is_update: Whether this is an update article

        Returns:
            Formatted headline with proper update indicators
        """
        # Clean the input sentence first
        cleaned = self.clean_llm_generated_title(summary_sentence)
        
        # Check if it already has update indicators
        has_update_emoji = cleaned.startswith('🆙')
        has_update_text = any(keyword in cleaned for keyword in ['続報', '更新', '新展開'])
        
        # If it's an update but lacks indicators, add emoji
        if is_update and not has_update_emoji and not has_update_text:
            # Add 🆙 emoji for updates
            cleaned = f"🆙 {cleaned}"
        
        # If it has both emoji and text, prioritize emoji (remove redundant text)
        if has_update_emoji and has_update_text:
            # Remove redundant update text when emoji is present
            cleaned = re.sub(r'【?続報】?|【?更新】?|【?新展開】?', '', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return self.intelligent_truncate(cleaned, max_chars=70)
    
    def format_headline_from_summary(self, summary_sentence: str) -> str:
        """Format headline from summary sentence."""
        return self.format_headline_integrated(summary_sentence, False)
    
    def generate_integrated_fallback_title(self, article: 'ProcessedArticle', is_update: bool) -> str:
        """
        Generate fallback title with integrated update logic.

        Args:
            article: Article to generate title for
            is_update: Whether this is an update article

        Returns:
            Generated fallback title
        """
        try:
            # Extract summary points
            summary_points = []
            if (hasattr(article, 'summarized_article') and
                article.summarized_article and
                hasattr(article.summarized_article, 'summary') and
                article.summarized_article.summary and
                hasattr(article.summarized_article.summary, 'summary_points')):
                summary_points = article.summarized_article.summary.summary_points

            if not summary_points:
                # Use original title as last resort
                if (hasattr(article, 'summarized_article') and
                    article.summarized_article and
                    hasattr(article.summarized_article, 'filtered_article') and
                    article.summarized_article.filtered_article and
                    hasattr(article.summarized_article.filtered_article, 'raw_article') and
                    article.summarized_article.filtered_article.raw_article):
                    original_title = article.summarized_article.filtered_article.raw_article.title
                    return self.intelligent_truncate(original_title, max_chars=70)
                return "AI関連ニュース"

            # Use first summary point as base
            base_summary = summary_points[0]
            
            # Apply integrated formatting
            return self.format_headline_integrated(base_summary, is_update)

        except Exception as e:
            logger.warning(f"Fallback title generation failed: {e}")
            return "AI関連ニュース"
    
    def generate_improved_fallback_title(self, article: 'ProcessedArticle') -> str:
        """Generate improved fallback title."""
        return self.generate_integrated_fallback_title(article, False)
    
    def clean_llm_generated_title(self, title: str) -> str:
        """
        Clean LLM-generated title from artifacts and formatting issues.

        Args:
            title: Raw LLM generated title

        Returns:
            Cleaned title
        """
        if not title:
            return ""

        # Remove common LLM conversation artifacts
        conversation_artifacts = [
            r'^はい、?承知(?:いた)?しました。?.*?',
            r'^以下.*見出し.*[：:].*?',
            r'^魅力的.*見出し.*[：:].*?', 
            r'^記事.*要約.*見出し.*[：:].*?',
            r'^プロ.*編集者.*',
            r'^あなたは.*です.*',
            r'^【?見出し】?[：:].*?',
            r'^「.*」$',  # Remove quotation marks
            r'^\d+\.\s*',  # Remove numbering
            r'^[-•]\s*'    # Remove bullet points
        ]

        cleaned = title
        for pattern in conversation_artifacts:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Clean up whitespace and formatting
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()

        # Remove trailing punctuation except periods that are part of content
        cleaned = re.sub(r'[.。]+$', '', cleaned)

        # Apply duplicate pattern removal if available
        if HAS_DEPENDENCIES:
            cleaned = remove_duplicate_patterns(cleaned)

        return cleaned
    
    def is_highly_generic_title(self, title: str) -> bool:
        """
        Check if title is highly generic and lacks specificity.

        Args:
            title: Title to check

        Returns:
            True if title is generic, False otherwise
        """
        generic_patterns = [
            r'^AI.*技術$',
            r'^LLM.*モデル$',
            r'^新.*技術$',
            r'^最新.*情報$',
            r'^技術.*進展$',
            r'^.*について$',
            r'^.*に関して$'
        ]

        for pattern in generic_patterns:
            if re.search(pattern, title):
                return True

        # Check for very short titles
        if len(title) < 15:
            return True

        return False
    
    def generate_specific_title_from_content(self, article: 'ProcessedArticle') -> str:
        """
        Generate specific title from article content.

        Args:
            article: Article to generate title for

        Returns:
            Generated specific title
        """
        try:
            # Extract key information from summary points
            summary_points = []
            if (hasattr(article, 'summarized_article') and
                article.summarized_article and
                hasattr(article.summarized_article, 'summary') and
                article.summarized_article.summary):
                summary_points = article.summarized_article.summary.summary_points

            if not summary_points:
                return "AI関連ニュース"

            # Extract key topic from first summary point
            key_topic = self.extract_key_topic_from_summary(summary_points[0])
            
            if key_topic:
                # Create specific title using key topic
                return self.intelligent_truncate(key_topic, max_chars=70)
            else:
                # Fallback to shortened first summary point
                return self.intelligent_truncate(summary_points[0], max_chars=70)

        except Exception as e:
            logger.warning(f"Specific title generation failed: {e}")
            return "AI関連ニュース"
    
    def generate_japanese_title(self, article: 'ProcessedArticle') -> str:
        """
        Generate Japanese title for article (synchronous version).

        Args:
            article: Article to generate title for

        Returns:
            Generated Japanese title
        """
        try:
            # This is a synchronous wrapper - use fallback logic
            return self.generate_integrated_fallback_title(article, getattr(article, 'is_update', False))
        except Exception as e:
            logger.warning(f"Japanese title generation failed: {e}")
            return "AI関連ニュース"
    
    def extract_key_topic_from_summary(self, summary_point: str) -> Optional[str]:
        """
        Extract key topic from summary point.

        Args:
            summary_point: Summary point to extract topic from

        Returns:
            Extracted key topic or None
        """
        if not summary_point:
            return None

        # Patterns to extract key topics (company/product names, key actions)
        topic_patterns = [
            r'(OpenAI|Google|Microsoft|Meta|Anthropic|Tesla|NVIDIA)\s*(?:が|は|の)?\s*([^。]+)',
            r'(GPT|ChatGPT|Gemini|Claude|LLaMA|PaLM)\s*(?:が|は|の)?\s*([^。]+)',
            r'^([^。]{20,60})(?:します|しました|されます|されました)',
            r'^([^。]{15,50})(?:を|が)([^。]+)'
        ]

        for pattern in topic_patterns:
            match = re.search(pattern, summary_point)
            if match:
                if len(match.groups()) == 2:
                    # Company/product + action
                    return f"{match.group(1)}{match.group(2)}"
                else:
                    # First substantial phrase
                    return match.group(1).strip()

        # Fallback: return first 50 characters
        return summary_point[:50] + "..." if len(summary_point) > 50 else summary_point
    
    def sanitize_heading(self, heading: str) -> str:
        """
        Sanitize heading for safe use in markdown.

        Args:
            heading: Heading to sanitize

        Returns:
            Sanitized heading
        """
        if not heading:
            return ""

        # Remove markdown special characters
        sanitized = re.sub(r'[#*`_\\]', '', heading)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Remove leading/trailing whitespace
        sanitized = sanitized.strip()
        
        return sanitized
    
    def normalize_terminology(self, text: str) -> str:
        """
        Normalize AI/tech terminology for consistency.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Terminology mappings
        normalizations = {
            'AI': 'AI',
            'ai': 'AI', 
            'A.I.': 'AI',
            'LLM': 'LLM',
            'llm': 'LLM',
            'GPT': 'GPT',
            'gpt': 'GPT',
            'ChatGPT': 'ChatGPT',
            'chatgpt': 'ChatGPT',
            'OpenAI': 'OpenAI',
            'openai': 'OpenAI'
        }

        normalized = text
        for old_term, new_term in normalizations.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(old_term) + r'\b'
            normalized = re.sub(pattern, new_term, normalized)

        return normalized
    
    def intelligent_truncate(self, text: str, max_chars: int = 70) -> str:
        """
        Intelligently truncate text at natural breaking points.

        Args:
            text: Text to truncate
            max_chars: Maximum characters allowed

        Returns:
            Truncated text
        """
        if not text or len(text) <= max_chars:
            return text

        # Try to truncate at natural breaking points
        breaking_points = ['、', '。', 'を', 'が', 'に', 'で', 'と']
        
        for i in range(max_chars, max(0, max_chars - 20), -1):
            if i < len(text) and text[i] in breaking_points:
                truncated = text[:i+1]
                # Ensure it doesn't end with hanging particles
                if not truncated.endswith(('を', 'が', 'に', 'で', 'の')):
                    return truncated

        # Fallback: hard truncate
        return text[:max_chars-3] + "..."