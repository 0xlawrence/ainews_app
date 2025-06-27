"""
Newsletter Quality Checker - Comprehensive quality validation system.

This module provides automated quality checks for generated newsletters,
including grammar validation, content structure verification, and overall
readability assessment.
"""

import re
import asyncio
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from src.utils.logger import setup_logging

logger = setup_logging()


@dataclass
class QualityIssue:
    """Represents a quality issue found in the newsletter."""
    severity: str  # 'critical', 'major', 'minor'
    category: str  # 'grammar', 'structure', 'content', 'formatting'
    location: str  # Where the issue was found
    description: str  # What the issue is
    suggestion: str  # How to fix it
    line_number: Optional[int] = None


@dataclass
class QualityReport:
    """Complete quality assessment report."""
    overall_score: float  # 0.0 - 1.0
    requires_regeneration: bool
    issues: List[QualityIssue]
    section_scores: Dict[str, float]
    metrics: Dict[str, Any]


class NewsletterQualityChecker:
    """Comprehensive newsletter quality validation system."""
    
    def __init__(self):
        """Initialize quality checker."""
        self.min_acceptable_score = 0.5
        self.critical_threshold = 0.3
        
        # Grammar patterns for Japanese text validation
        self.grammar_patterns = {
            'incomplete_sentences': [
                r'[A-Za-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+が。',  # "Googleが。"
                r'[はがをにでと]$',  # Ends with particles
                r'[はがをにでと]。\s*[^。！？]*$',  # Particle followed by incomplete text
            ],
            'redundant_expressions': [
                r'(されています|しています).*?(と発表|と報告|と説明)',
                r'発表を発表',
                r'報告を報告',
                r'説明を説明',
            ],
            'inappropriate_endings': [
                r'と発表しました。?$',
                r'と述べました。?$', 
                r'と語りました。?$',
                r'と報告しました。?$',
            ]
        }
    
    async def check_newsletter_quality(self, content: str, metadata: Dict[str, Any] = None) -> QualityReport:
        """
        Perform comprehensive quality check on newsletter content.
        
        Args:
            content: Newsletter markdown content
            metadata: Additional metadata about the newsletter
            
        Returns:
            QualityReport with detailed assessment
        """
        logger.info("Starting comprehensive quality check")
        
        issues = []
        section_scores = {}
        metrics = {}
        
        # Parse newsletter sections
        sections = self._parse_newsletter_sections(content)
        
        # Check each section
        lead_issues, lead_score = await self._check_lead_text(sections.get('lead', ''))
        issues.extend(lead_issues)
        section_scores['lead'] = lead_score
        
        toc_issues, toc_score = self._check_table_of_contents(sections.get('toc', ''))
        issues.extend(toc_issues)
        section_scores['toc'] = toc_score
        
        articles_issues, articles_score = await self._check_article_sections(sections.get('articles', []))
        issues.extend(articles_issues)
        section_scores['articles'] = articles_score
        
        citations_issues, citations_score = self._check_citations(sections.get('citations', []))
        issues.extend(citations_issues)
        section_scores['citations'] = citations_score
        
        # Overall structure check
        structure_issues, structure_score = self._check_overall_structure(content)
        issues.extend(structure_issues)
        section_scores['structure'] = structure_score
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(section_scores, issues)
        
        # Determine if regeneration is required
        requires_regeneration = (
            overall_score < self.min_acceptable_score or
            any(issue.severity == 'critical' for issue in issues)
        )
        
        # Collect metrics
        metrics = {
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i.severity == 'critical']),
            'major_issues': len([i for i in issues if i.severity == 'major']),
            'minor_issues': len([i for i in issues if i.severity == 'minor']),
            'article_count': len(sections.get('articles', [])),
            'content_length': len(content),
            'check_timestamp': datetime.now().isoformat()
        }
        
        logger.info(
            f"Quality check completed: score={overall_score:.2f}, "
            f"issues={len(issues)}, regeneration_required={requires_regeneration}"
        )
        
        return QualityReport(
            overall_score=overall_score,
            requires_regeneration=requires_regeneration,
            issues=issues,
            section_scores=section_scores,
            metrics=metrics
        )
    
    def _parse_newsletter_sections(self, content: str) -> Dict[str, Any]:
        """Parse newsletter into identifiable sections."""
        sections = {
            'lead': '',
            'toc': '',
            'articles': [],
            'citations': []
        }
        
        lines = content.split('\n')
        current_section = None
        current_article = None
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Identify section headers
            if line_stripped.startswith('# '):
                continue  # Main title
            elif line_stripped.startswith('## ') and '目次' in line_stripped:
                current_section = 'toc'
                continue
            elif line_stripped.startswith('## ') and not line_stripped.startswith('## '):
                # Article section
                if current_article:
                    sections['articles'].append(current_article)
                current_article = {
                    'title': line_stripped[3:],
                    'content': '',
                    'line_number': i + 1
                }
                current_section = 'article'
                continue
            elif line_stripped == '---':
                current_section = 'articles_start'
                continue
            
            # Collect content based on current section
            if current_section == 'toc' and line_stripped and not line_stripped.startswith('#'):
                sections['toc'] += line + '\n'
            elif current_section == 'article' and current_article:
                current_article['content'] += line + '\n'
            elif current_section is None and line_stripped and not line_stripped.startswith('#'):
                # This is likely lead text
                sections['lead'] += line + '\n'
        
        # Add final article if exists
        if current_article:
            sections['articles'].append(current_article)
        
        return sections
    
    async def _check_lead_text(self, lead_text: str) -> Tuple[List[QualityIssue], float]:
        """Check lead text quality."""
        issues = []
        score = 1.0
        
        if not lead_text.strip():
            issues.append(QualityIssue(
                severity='critical',
                category='content',
                location='lead_text',
                description='リード文が存在しません',
                suggestion='リード文を生成してください'
            ))
            return issues, 0.0
        
        # Check for grammar issues
        for pattern_name, patterns in self.grammar_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, lead_text)
                for match in matches:
                    issues.append(QualityIssue(
                        severity='critical',
                        category='grammar',
                        location='lead_text',
                        description=f'文法エラー: {pattern_name} - "{match.group()}"',
                        suggestion='文法的に正しい文に修正してください'
                    ))
                    score -= 0.3
        
        # Check paragraph count
        paragraphs = [p.strip() for p in lead_text.split('\n') if p.strip()]
        if len(paragraphs) < 2:
            issues.append(QualityIssue(
                severity='major',
                category='structure',
                location='lead_text',
                description='リード文の段落数が不足しています',
                suggestion='2-3段落でリード文を構成してください'
            ))
            score -= 0.2
        
        # Check paragraph length
        for i, para in enumerate(paragraphs):
            if len(para) > 200:
                issues.append(QualityIssue(
                    severity='minor',
                    category='formatting',
                    location=f'lead_paragraph_{i+1}',
                    description='段落が長すぎます',
                    suggestion='150文字以内に収めてください'
                ))
                score -= 0.1
        
        return issues, max(0.0, score)
    
    def _check_table_of_contents(self, toc_content: str) -> Tuple[List[QualityIssue], float]:
        """Check table of contents quality."""
        issues = []
        score = 1.0
        
        if not toc_content.strip():
            issues.append(QualityIssue(
                severity='major',
                category='structure',
                location='table_of_contents',
                description='目次が存在しません',
                suggestion='目次を生成してください'
            ))
            return issues, 0.0
        
        # Check for incomplete entries (ending with particles or mid-sentence)
        toc_lines = [line.strip() for line in toc_content.split('\n') if line.strip() and re.match(r'^\d+\.', line.strip())]
        
        for i, line in enumerate(toc_lines):
            # Remove numbering
            content = re.sub(r'^\d+\.\s*', '', line)
            
            # Check for problematic endings
            if content.endswith(('は', 'が', 'を', 'に', 'で', 'と')):
                issues.append(QualityIssue(
                    severity='major',
                    category='grammar',
                    location=f'toc_entry_{i+1}',
                    description=f'目次項目が助詞で終わっています: "{content[-10:]}"',
                    suggestion='完全な表現に修正してください'
                ))
                score -= 0.15
            
            # Check for unnatural truncation
            if '、…' in content or content.endswith('、'):
                issues.append(QualityIssue(
                    severity='minor',
                    category='formatting',
                    location=f'toc_entry_{i+1}',
                    description='不自然な切断位置です',
                    suggestion='自然な文境界で切断してください'
                ))
                score -= 0.05
        
        return issues, max(0.0, score)
    
    async def _check_article_sections(self, articles: List[Dict]) -> Tuple[List[QualityIssue], float]:
        """Check individual article sections."""
        issues = []
        total_score = 0.0
        
        if not articles:
            issues.append(QualityIssue(
                severity='critical',
                category='content',
                location='articles',
                description='記事が存在しません',
                suggestion='記事コンテンツを生成してください'
            ))
            return issues, 0.0
        
        for i, article in enumerate(articles):
            article_score = 1.0
            
            # Check title quality
            title = article.get('title', '')
            if not title:
                issues.append(QualityIssue(
                    severity='critical',
                    category='content',
                    location=f'article_{i+1}_title',
                    description='記事タイトルが存在しません',
                    suggestion='タイトルを生成してください'
                ))
                article_score -= 0.5
            else:
                # Check for title quality issues
                if title.endswith(('は', 'が', 'を', 'に')):
                    issues.append(QualityIssue(
                        severity='major',
                        category='grammar',
                        location=f'article_{i+1}_title',
                        description=f'タイトルが助詞で終わっています: "{title}"',
                        suggestion='完全な表現に修正してください'
                    ))
                    article_score -= 0.3
                
                if len(title) > 80:
                    issues.append(QualityIssue(
                        severity='minor',
                        category='formatting',
                        location=f'article_{i+1}_title',
                        description='タイトルが長すぎます',
                        suggestion='60文字以内に収めてください'
                    ))
                    article_score -= 0.1
            
            # Check content quality
            content = article.get('content', '')
            if not content.strip():
                issues.append(QualityIssue(
                    severity='major',
                    category='content',
                    location=f'article_{i+1}_content',
                    description='記事本文が存在しません',
                    suggestion='記事内容を生成してください'
                ))
                article_score -= 0.4
            
            total_score += max(0.0, article_score)
        
        average_score = total_score / len(articles) if articles else 0.0
        return issues, average_score
    
    def _check_citations(self, citations: List[str]) -> Tuple[List[QualityIssue], float]:
        """Check citation quality."""
        issues = []
        score = 1.0
        
        # This is a placeholder - citations are embedded in articles
        # In actual implementation, would parse citations from article content
        
        return issues, score
    
    def _check_overall_structure(self, content: str) -> Tuple[List[QualityIssue], float]:
        """Check overall newsletter structure."""
        issues = []
        score = 1.0
        
        # Check for required sections
        required_sections = ['# ', '## 目次', '---']
        
        for section in required_sections:
            if section not in content:
                issues.append(QualityIssue(
                    severity='major',
                    category='structure',
                    location='overall_structure',
                    description=f'必須セクションが不足: {section}',
                    suggestion='必要なセクションを追加してください'
                ))
                score -= 0.2
        
        # Check for proper markdown formatting
        if not re.search(r'^# .+', content, re.MULTILINE):
            issues.append(QualityIssue(
                severity='major',
                category='formatting',
                location='overall_structure',
                description='メインタイトルが適切にフォーマットされていません',
                suggestion='# でメインタイトルを設定してください'
            ))
            score -= 0.2
        
        return issues, max(0.0, score)
    
    def _calculate_overall_score(self, section_scores: Dict[str, float], issues: List[QualityIssue]) -> float:
        """Calculate overall quality score."""
        # Base score from section averages
        if section_scores:
            base_score = sum(section_scores.values()) / len(section_scores)
        else:
            base_score = 0.0
        
        # Penalty for issues
        critical_penalty = len([i for i in issues if i.severity == 'critical']) * 0.2
        major_penalty = len([i for i in issues if i.severity == 'major']) * 0.1
        minor_penalty = len([i for i in issues if i.severity == 'minor']) * 0.05
        
        total_penalty = critical_penalty + major_penalty + minor_penalty
        
        final_score = max(0.0, base_score - total_penalty)
        return final_score
    
    def generate_quality_report(self, quality_report: QualityReport) -> str:
        """Generate human-readable quality report."""
        report_lines = [
            "# ニュースレター品質レポート",
            f"",
            f"**総合スコア**: {quality_report.overall_score:.2f}/1.0",
            f"**再生成が必要**: {'はい' if quality_report.requires_regeneration else 'いいえ'}",
            f"**問題の総数**: {quality_report.metrics.get('total_issues', 0)}",
            f"",
            "## セクション別スコア"
        ]
        
        for section, score in quality_report.section_scores.items():
            report_lines.append(f"- {section}: {score:.2f}")
        
        if quality_report.issues:
            report_lines.extend([
                "",
                "## 発見された問題",
                ""
            ])
            
            # Group issues by severity
            for severity in ['critical', 'major', 'minor']:
                severity_issues = [i for i in quality_report.issues if i.severity == severity]
                if severity_issues:
                    report_lines.append(f"### {severity.title()} Issues")
                    for issue in severity_issues:
                        report_lines.append(f"- **{issue.location}**: {issue.description}")
                        report_lines.append(f"  *提案*: {issue.suggestion}")
                    report_lines.append("")
        
        return '\n'.join(report_lines)


# Convenience function for easy integration
async def check_newsletter_quality(content: str, metadata: Dict[str, Any] = None) -> QualityReport:
    """Convenience function to check newsletter quality."""
    checker = NewsletterQualityChecker()
    return await checker.check_newsletter_quality(content, metadata)