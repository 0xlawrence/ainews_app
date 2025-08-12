"""
Content formatting and template processing for newsletters.

This module handles Jinja2 template rendering, markdown generation, citation formatting,
and various content enhancement utilities for newsletter creation.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import jinja2
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
    jinja2 = None

try:
    from src.models.schemas import Citation, ProcessedArticle, NewsletterOutput
    from src.config.settings import get_settings
    from src.utils.text_processing import (
        fix_inappropriate_period_insertions, 
        fix_particle_duplication,
        intelligent_truncate
    )
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

logger = logging.getLogger(__name__)


class ContentFormatter:
    """Handles newsletter content formatting and template processing."""
    
    def __init__(self, templates_dir: str = "src/templates"):
        """Initialize content formatter.
        
        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        self.templates_dir = Path(templates_dir)
        if HAS_DEPENDENCIES:
            self.settings = get_settings()
        else:
            self.settings = None
        
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
        
        logger.info("Content Formatter initialized")
    
    def render_newsletter_content(
        self,
        context: Dict[str, Any],
        edition: str = "daily"
    ) -> str:
        """
        Render newsletter content using Jinja2 templates or fallback markdown.

        Args:
            context: Template context with all necessary data
            edition: Newsletter edition type

        Returns:
            Rendered newsletter content as markdown
        """
        template_name = f"{edition}_newsletter.jinja2"
        template = None

        if self.jinja_env:
            # Use Jinja2 template rendering
            try:
                template = self.jinja_env.get_template(template_name)
            except Exception:  # jinja2.TemplateNotFound etc.
                logger.warning(
                    f"Template not found: {template_name}, using default: daily_newsletter.jinja2"
                )
                try:
                    template = self.jinja_env.get_template("daily_newsletter.jinja2")
                except Exception:
                    # Fall back to basic markdown generation
                    logger.warning("Default template also not found, using basic markdown")
                    template = None
        else:
            logger.info("Jinja2 not available, using basic markdown generation")

        # Render template (if available)
        if template:
            try:
                newsletter_content = template.render(**context)
                logger.info(f"Successfully rendered template: {template_name}")
            except Exception as e:
                logger.error(f"Template rendering failed: template={template_name}, error={str(e)}")
                # Fallback to basic markdown
                newsletter_content = self.generate_basic_markdown(context)
        else:
            # Fallback: Generate basic markdown without template
            newsletter_content = self.generate_basic_markdown(context)

        # Clean up excessive blank lines (3+ -> 2)
        newsletter_content = re.sub(r"\n{3,}", "\n\n", newsletter_content)

        return newsletter_content

    def generate_basic_markdown(self, context: Dict[str, Any]) -> str:
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

            # Add citations
            if hasattr(article, 'citations') and article.citations:
                for citation in article.citations:
                    if hasattr(citation, 'japanese_summary'):  # Citation object
                        lines.extend([self.citation_to_markdown(citation), ""])
                    else:
                        # Legacy string format support
                        lines.extend([str(citation), ""])

        return "\n".join(lines)

    def citation_to_markdown(self, citation: 'Citation') -> str:
        """Convert Citation object to Markdown format."""
        if hasattr(citation, 'japanese_summary') and citation.japanese_summary:
            return f"> **{citation.source_name}** ({citation.url}): {citation.japanese_summary}"
        else:
            return f"> **{citation.source_name}** ({citation.url}): {citation.title}"

    # Jinja2 Custom Filters

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

    def _short_title_filter(self, text: str, max_chars: int = 70) -> str:
        """Jinja2 filter to shorten title text."""
        if HAS_DEPENDENCIES:
            return intelligent_truncate(text, max_chars)
        else:
            # Simple truncation fallback
            return text[:max_chars] + "..." if len(text) > max_chars else text

    def _toc_format_filter(self, text: str) -> str:
        """Jinja2 filter for formatting table of contents entries with improved Japanese truncation."""

        if not text:
            return text

        # Clean hash marks that might leak into title
        text = re.sub(r'^#+\s*', '', text.strip())
        
        # Apply text processing fixes before truncation if available
        if HAS_DEPENDENCIES:
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
                remaining_text = text[quote_end:]
                break_points = ['、', '。', 'を', 'が', 'に', 'で', 'と', 'の']
                
                for i, char in enumerate(remaining_text):
                    if char in break_points and quote_end + i <= max_toc_length:
                        return text[:quote_end + i + 1]
                
                return cut_text

        # Standard intelligent truncation with additional rollback for particles/comma
        if HAS_DEPENDENCIES:
            truncated = intelligent_truncate(text, max_toc_length)
            # Additional guard: avoid particle/comma endings
            if truncated.endswith(('は', 'が', 'を', 'に', 'で', 'と', '、')):
                truncated = truncated[:-1].rstrip()
                if len(text) > len(truncated) and not truncated.endswith(('。', '」', '）')):
                    truncated += '…'
            return truncated
        else:
            # Simple truncation fallback with light rollback
            tmp = text[:max_toc_length]
            if tmp.endswith(('は', 'が', 'を', 'に', 'で', 'と', '、')):
                tmp = tmp[:-1].rstrip()
            return (tmp + '...') if len(text) > len(tmp) else tmp

    # Content Enhancement Utilities

    def extract_article_highlights(self, articles: List['ProcessedArticle']) -> List[str]:
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

    def _prioritize_articles_for_highlights(self, articles: List['ProcessedArticle']) -> List['ProcessedArticle']:
        """Prioritize articles based on impact indicators for highlight generation."""

        def calculate_impact_score(article: 'ProcessedArticle') -> float:
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
                if 15 < len(context) < 100:
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

    def _create_thematic_highlights(self, articles: List['ProcessedArticle']) -> List[str]:
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

    def extract_key_themes(self, articles: List['ProcessedArticle']) -> List[str]:
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

        theme_scores = {}
        
        # Analyze each article for themes
        for article in articles:
            try:
                if (article.summarized_article and
                    article.summarized_article.summary and
                    article.summarized_article.summary.summary_points):
                    
                    summary_text = " ".join(article.summarized_article.summary.summary_points)
                    title = article.summarized_article.filtered_article.raw_article.title
                    combined_text = (summary_text + " " + title).lower()
                    
                    for theme, keywords in theme_keywords.items():
                        score = sum(1 for keyword in keywords if keyword.lower() in combined_text)
                        if score > 0:
                            theme_scores[theme] = theme_scores.get(theme, 0) + score
                            
            except Exception as e:
                logger.warning(f"Failed to extract themes from article: {e}")
                continue
        
        # Return top themes sorted by frequency
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        return [theme for theme, score in sorted_themes[:3]]

    def generate_lead_title_from_articles(self, articles: List['ProcessedArticle'], edition: str) -> str:
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

    def prepare_template_context(
        self,
        articles: List['ProcessedArticle'],
        lead_text: Dict[str, Any],
        edition: str,
        newsletter_date: datetime,
        processing_summary: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Prepare template context for newsletter rendering."""
        
        context = {
            "date": newsletter_date,
            "edition": edition,
            "articles": articles,
            "lead_text": lead_text,
            "article_count": len(articles),
            "update_count": sum(1 for a in articles if getattr(a, 'is_update', False)),
            "processing_summary": processing_summary or {},
            "generation_timestamp": datetime.now().isoformat(),
        }

        # Add theme analysis
        themes = self.extract_key_themes(articles)
        context["themes"] = themes
        context["primary_theme"] = themes[0] if themes else "AI技術"

        # Add highlights for enhanced lead content
        highlights = self.extract_article_highlights(articles)
        context["highlights"] = highlights

        return context

    def validate_and_fix_newsletter_content(
        self, 
        content: str, 
        articles: List['ProcessedArticle']
    ) -> str:
        """Perform final quality validation and fixes on generated newsletter content."""
        
        if not content:
            logger.warning("Empty newsletter content provided for validation")
            return content

        # Basic content fixes
        fixes_applied = []

        # 1. Fix excessive spacing
        original_length = len(content)
        content = re.sub(r'\n{4,}', '\n\n\n', content)  # Max 3 consecutive newlines
        content = re.sub(r'[ \t]+\n', '\n', content)  # Remove trailing spaces
        if len(content) != original_length:
            fixes_applied.append("spacing")

        # 2. Fix malformed headers
        content = re.sub(r'^#{4,}', '###', content, flags=re.MULTILINE)  # Max 3 hash levels
        content = re.sub(r'^(#+)\s*$', '', content, flags=re.MULTILINE)  # Remove empty headers

        # 3. Fix list formatting
        content = re.sub(r'^-\s*$', '', content, flags=re.MULTILINE)  # Remove empty list items
        content = re.sub(r'^(\s*)-\s*([^-\n])', r'\1- \2', content, flags=re.MULTILINE)  # Fix list spacing

        # 4. Ensure proper sentence endings in summary points
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            if line.strip().startswith('- ') and line.strip() != '-':
                # This is a summary point
                point = line.strip()[2:].strip()  # Remove '- ' prefix
                if point and not point.endswith(('。', '.', '!', '?', '！', '？')):
                    # Add proper ending if missing
                    if any(word in point for word in ['発表', '開始', '公開', '導入', '提供']):
                        point += 'しました。'
                    elif any(word in point for word in ['予定', '見込み', '計画']):
                        point += 'です。'
                    else:
                        point += '。'
                    line = line.replace(line.strip()[2:].strip(), point)
                    if 'summary_points' not in fixes_applied:
                        fixes_applied.append('summary_points')
            
            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 5. Gate against meta text and invalid citation URLs
        #    - メタ文言/禁止語/指示語の簡易チェック
        meta_like_patterns = [
            r'^はい、?承知', r'^以下が要約です[:：]', r'^プロ.*編集者', r'^あなたは.*です',
        ]
        content_lines = content.split('\n')
        cleaned_lines: list[str] = []
        for ln in content_lines:
            cleaned = ln
            for pat in meta_like_patterns:
                cleaned = re.sub(pat, '', cleaned)
            cleaned_lines.append(cleaned)
        content = '\n'.join(cleaned_lines)

        # 6. 引用URLの妥当性検証（dummy/非httpや不正なYouTube ID排除）
        try:
            from src.utils.url_validation import validate_citation_url
        except Exception:
            validate_citation_url = None

        if validate_citation_url:
            def _clean_blockquote(line: str) -> str:
                # 形式: "> **source** (url): text"
                m = re.match(r'^>\s*\*\*[^*]+\*\*\s*\(([^)]+)\):\s*(.+)$', line)
                if not m:
                    return line
                url = m.group(1)
                if not validate_citation_url(url):
                    # URLが不正なら引用行ごと除去
                    return ''
                return line

            content = '\n'.join(_clean_blockquote(ln) for ln in content.split('\n'))

        # 7. 軽微なKPI警告（構造的な異常の検知）
        if '### ' not in content:
            logger.warning("No section headers found in newsletter content")
        if len([line for line in content.split('\n') if line.strip().startswith('- ')]) < 3:
            logger.warning("Very few summary points found in newsletter content")

        # 8. 目次の簡易再生成（重大違反を緩和するための非LLM対処）
        try:
            if '### 目次' in content:
                bullet_count = len([l for l in content.split('\n') if l.strip().startswith('- ')])
                if bullet_count < 3 and articles:
                    toc_lines = ['### 目次', '']
                    visible_articles = [a for a in articles if getattr(a, 'japanese_title', None)]
                    for i, a in enumerate(visible_articles[:10], 1):
                        title = a.japanese_title[:45] if len(a.japanese_title) > 45 else a.japanese_title
                        update_indicator = " 🆙" if getattr(a, 'is_update', False) else ""
                        toc_lines.append(f"{i}. {title}{update_indicator}")
                        toc_lines.append("")
                    new_toc = "\n".join(toc_lines) + "\n\n---"
                    content = re.sub(r'### 目次[\s\S]*?(?:\n\n|---)', new_toc, content, flags=re.MULTILINE)
                    fixes_applied.append('toc_regenerated')
        except Exception:
            pass

        if fixes_applied:
            logger.info(f"Applied content fixes: {', '.join(fixes_applied)}")

        return content