"""
Content validation and style checking for newsletter articles.

This module provides comprehensive validation for content quality,
style guidelines, and automated quality assurance.
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum

import src.models.enhanced_schemas as es
from src.models.enhanced_schemas import ValidationResult, ValidationRule, QualityLevel
from src.utils.logger import setup_logging

logger = setup_logging()


class ViolationSeverity(str, Enum):
    """Severity levels for validation violations."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class StyleRule:
    """Represents a style validation rule."""
    name: str
    description: str
    pattern: Optional[str] = None
    check_function: Optional[callable] = None
    severity: ViolationSeverity = ViolationSeverity.WARNING
    category: str = "style"


class ContentValidator:
    """Comprehensive content validation system."""
    
    def __init__(self):
        """Initialize content validator with rules."""
        self.rules = self._initialize_rules()
        self.forbidden_phrases = self._load_forbidden_phrases()
        self.preferred_terms = self._load_preferred_terms()
    
    def _initialize_rules(self) -> List[StyleRule]:
        """Initialize validation rules."""
        rules = []
        
        # Japanese style rules
        rules.extend([
            StyleRule(
                name="no_demonstrative_pronouns",
                description="指示語（この、その、あの、どの）の使用禁止",
                pattern=r'\b(この|その|あの|どの)\b',
                severity=ViolationSeverity.ERROR,
                category="japanese_style"
            ),
            StyleRule(
                name="proper_sentence_ending",
                description="適切な文末表現（です・ます・した・きます・。）",
                check_function=self._check_sentence_endings,
                severity=ViolationSeverity.WARNING,
                category="japanese_style"
            ),
            StyleRule(
                name="consistent_politeness",
                description="敬語の一貫性",
                check_function=self._check_politeness_consistency,
                severity=ViolationSeverity.INFO,
                category="japanese_style"
            )
        ])
        
        # Content structure rules
        rules.extend([
            StyleRule(
                name="bullet_point_count",
                description="箇条書きの数（3-4項目）",
                check_function=self._check_bullet_point_count,
                severity=ViolationSeverity.ERROR,
                category="structure"
            ),
            StyleRule(
                name="bullet_point_length",
                description="各項目の文字数（20-150文字）",
                check_function=self._check_bullet_point_length,
                severity=ViolationSeverity.WARNING,
                category="structure"
            ),
            StyleRule(
                name="specific_information",
                description="具体的な情報の含有（数値、固有名詞）",
                check_function=self._check_specific_information,
                severity=ViolationSeverity.WARNING,
                category="content_quality"
            )
        ])
        
        # Readability rules
        rules.extend([
            StyleRule(
                name="sentence_complexity",
                description="文の複雑さ",
                check_function=self._check_sentence_complexity,
                severity=ViolationSeverity.INFO,
                category="readability"
            ),
            StyleRule(
                name="repetitive_expressions",
                description="重複表現の回避",
                check_function=self._check_repetitive_expressions,
                severity=ViolationSeverity.WARNING,
                category="readability"
            ),
            StyleRule(
                name="foreign_term_usage",
                description="外来語の適切な使用",
                check_function=self._check_foreign_terms,
                severity=ViolationSeverity.INFO,
                category="terminology"
            )
        ])
        
        # Technical content rules
        rules.extend([
            StyleRule(
                name="ai_terminology_consistency",
                description="AI用語の一貫性",
                check_function=self._check_ai_terminology,
                severity=ViolationSeverity.WARNING,
                category="terminology"
            ),
            StyleRule(
                name="number_format_consistency",
                description="数値表記の一貫性",
                check_function=self._check_number_formats,
                severity=ViolationSeverity.INFO,
                category="formatting"
            )
        ])
        
        return rules
    
    def _load_forbidden_phrases(self) -> List[str]:
        """Load forbidden phrases and expressions."""
        return [
            # Demonstrative pronouns
            "この記事", "その技術", "あの会社", "どの製品",
            
            # Vague expressions
            "いくつかの", "多くの", "様々な", "いろいろな",
            "かなりの", "相当な", "それなりの",
            
            # Uncertain expressions
            "と思われます", "のようです", "らしいです", "みたいです",
            "かもしれません", "だろうと思います",
            
            # Overly casual expressions
            "すごい", "やばい", "まじで", "ちょっと",
            
            # Redundant expressions
            "〜することができます", "〜することが可能です"
        ]
    
    def _load_preferred_terms(self) -> Dict[str, str]:
        """Load preferred terminology mappings."""
        return {
            # AI terminology
            "人工知能": "AI",
            "機械学習": "機械学習（ML）",
            "深層学習": "ディープラーニング",
            "自然言語処理": "NLP",
            "大規模言語モデル": "LLM",
            
            # Company names
            "オープンエーアイ": "OpenAI",
            "グーグル": "Google",
            "マイクロソフト": "Microsoft",
            "メタ": "Meta",
            
            # Technical terms
            "アルゴリズム": "アルゴリズム",
            "データセット": "データセット",
            "トレーニング": "学習",
            "ファインチューニング": "ファインチューニング"
        }
    
    def validate_content(
        self, 
        content: Union[str, List[str]], 
        content_type: str = "summary"
    ) -> es.ValidationResult:
        """
        Validate content against all rules.
        
        Args:
            content: Content to validate (string or list of bullet points)
            content_type: Type of content (summary, title, description)
            
        Returns:
            ValidationResult with detailed findings
        """
        
        result = es.ValidationResult(
            is_valid=True,
            quality_level=es.QualityLevel.GOOD,
            quality_score=1.0,
            violations=[],
            metrics={}
        )
        
        # Convert content to standard format
        if isinstance(content, list):
            text_content = "\n".join(content)
            bullet_points = content
        else:
            text_content = content
            bullet_points = self._extract_bullet_points(content)
        
        # Run all validation rules
        for rule in self.rules:
            violations = self._apply_rule(rule, text_content, bullet_points)
            for violation in violations:
                result.add_violation(
                    rule_id=rule.name,
                    severity=rule.severity.value,
                    message=violation["message"],
                    details=violation.get("details", {})
                )
        
        # Calculate overall quality
        result.quality_score = self._calculate_quality_score(result.violations)
        result.quality_level = self._determine_quality_level(result.quality_score, result.violations)
        result.is_valid = len([v for v in result.violations if v["severity"] == "error"]) == 0
        
        # Add metrics
        result.metrics = self._calculate_metrics(text_content, bullet_points)
        
        logger.info(
            "Content validation completed",
            quality_score=result.quality_score,
            quality_level=result.quality_level.value,
            violations_count=len(result.violations),
            is_valid=result.is_valid
        )
        
        return result
    
    def _apply_rule(
        self, 
        rule: StyleRule, 
        text_content: str, 
        bullet_points: List[str]
    ) -> List[Dict[str, Any]]:
        """Apply a single validation rule."""
        violations = []
        
        try:
            if rule.pattern:
                # Regex-based rule
                matches = re.finditer(rule.pattern, text_content)
                for match in matches:
                    violations.append({
                        "message": f"{rule.description}: '{match.group()}'",
                        "details": {
                            "match": match.group(),
                            "position": match.start(),
                            "rule_type": "regex"
                        }
                    })
            
            elif rule.check_function:
                # Function-based rule
                function_violations = rule.check_function(text_content, bullet_points)
                violations.extend(function_violations)
                
        except Exception as e:
            logger.warning(f"Rule {rule.name} validation failed: {e}")
        
        return violations
    
    def _check_sentence_endings(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check for proper sentence endings."""
        violations = []
        proper_endings = ['です', 'ます', 'した', 'きます', '。', 'だ', 'である']
        
        for i, point in enumerate(bullet_points):
            point = point.strip()
            if not any(point.endswith(ending) for ending in proper_endings):
                violations.append({
                    "message": f"項目{i+1}の文末が不適切: '{point[-10:]}'",
                    "details": {"bullet_index": i, "ending": point[-10:]}
                })
        
        return violations
    
    def _check_politeness_consistency(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check for consistent politeness level."""
        violations = []
        
        polite_patterns = ['です', 'ます', 'でした', 'ました']
        casual_patterns = ['だ', 'である', 'する', 'した']
        
        polite_count = sum(1 for pattern in polite_patterns if pattern in text)
        casual_count = sum(1 for pattern in casual_patterns if pattern in text)
        
        if polite_count > 0 and casual_count > 0:
            ratio = min(polite_count, casual_count) / max(polite_count, casual_count)
            if ratio > 0.3:  # Mixed politeness levels
                violations.append({
                    "message": f"敬語レベルが混在（丁寧語:{polite_count}, 常体:{casual_count}）",
                    "details": {"polite_count": polite_count, "casual_count": casual_count}
                })
        
        return violations
    
    def _check_bullet_point_count(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check bullet point count (3-4 items)."""
        violations = []
        count = len(bullet_points)
        
        if count < 3:
            violations.append({
                "message": f"箇条書きが少なすぎます（{count}項目、最低3項目必要）",
                "details": {"count": count, "minimum": 3}
            })
        elif count > 4:
            violations.append({
                "message": f"箇条書きが多すぎます（{count}項目、最大4項目）",
                "details": {"count": count, "maximum": 4}
            })
        
        return violations
    
    def _check_bullet_point_length(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check bullet point length (20-150 characters)."""
        violations = []
        
        for i, point in enumerate(bullet_points):
            length = len(point.strip())
            if length < 20:
                violations.append({
                    "message": f"項目{i+1}が短すぎます（{length}文字、最低20文字）",
                    "details": {"bullet_index": i, "length": length, "minimum": 20}
                })
            elif length > 150:
                violations.append({
                    "message": f"項目{i+1}が長すぎます（{length}文字、最大150文字）",
                    "details": {"bullet_index": i, "length": length, "maximum": 150}
                })
        
        return violations
    
    def _check_specific_information(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check for specific information (numbers, proper nouns)."""
        violations = []
        
        # Check for numbers
        number_pattern = r'\d+(?:[.,]\d+)*(?:%|円|ドル|件|個|台|人|社|年|月|日|時間|分|秒|MB|GB|TB)?'
        
        # Check for proper nouns (capitalized words, katakana companies)
        proper_noun_pattern = r'[A-Z][a-zA-Z]+|[ァ-ヶー]+(?:社|会社|Corporation|Inc|LLC|Ltd)?'
        
        for i, point in enumerate(bullet_points):
            numbers = re.findall(number_pattern, point)
            proper_nouns = re.findall(proper_noun_pattern, point)
            
            if len(numbers) == 0 and len(proper_nouns) == 0:
                violations.append({
                    "message": f"項目{i+1}に具体的な情報（数値・固有名詞）が不足",
                    "details": {"bullet_index": i, "numbers": 0, "proper_nouns": 0}
                })
        
        return violations
    
    def _check_sentence_complexity(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check sentence complexity."""
        violations = []
        
        for i, point in enumerate(bullet_points):
            # Count clauses (separated by commas, conjunctions)
            clause_separators = ['、', 'が', 'し', 'て', 'で', 'に', 'を', 'は']
            clause_count = 1 + sum(point.count(sep) for sep in clause_separators)
            
            if clause_count > 4:
                violations.append({
                    "message": f"項目{i+1}の文が複雑すぎます（{clause_count}節）",
                    "details": {"bullet_index": i, "clause_count": clause_count}
                })
        
        return violations
    
    def _check_repetitive_expressions(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check for repetitive expressions."""
        violations = []
        
        # Extract common phrases (2-4 character sequences)
        phrases = []
        for point in bullet_points:
            # Remove particles and extract content words
            content_words = re.findall(r'[a-zA-Zァ-ヶー一-龯]{2,}', point)
            phrases.extend(content_words)
        
        # Count phrase frequency
        from collections import Counter
        phrase_counts = Counter(phrases)
        
        repeated_phrases = [phrase for phrase, count in phrase_counts.items() if count > 2]
        
        if repeated_phrases:
            violations.append({
                "message": f"重複表現があります: {', '.join(repeated_phrases[:3])}",
                "details": {"repeated_phrases": repeated_phrases}
            })
        
        return violations
    
    def _check_foreign_terms(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check foreign term usage."""
        violations = []
        
        # Common foreign terms that should be consistent
        foreign_terms = {
            'AI': ['人工知能', 'エーアイ'],
            'ML': ['機械学習', 'マシンラーニング'],
            'API': ['アプリケーションプログラミングインターフェース', 'エーピーアイ'],
            'ChatGPT': ['チャットジーピーティー'],
            'OpenAI': ['オープンエーアイ']
        }
        
        for preferred, alternatives in foreign_terms.items():
            for alt in alternatives:
                if alt in text and preferred in text:
                    violations.append({
                        "message": f"表記揺れ: '{preferred}'と'{alt}'が混在",
                        "details": {"preferred": preferred, "alternative": alt}
                    })
        
        return violations
    
    def _check_ai_terminology(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check AI terminology consistency."""
        violations = []
        
        ai_terms = {
            'LLM': '大規模言語モデル',
            'NLP': '自然言語処理',
            'GPT': 'Generative Pre-trained Transformer',
            'API': 'Application Programming Interface'
        }
        
        # Check if both acronym and full form are used inconsistently
        for acronym, full_form in ai_terms.items():
            if acronym in text and full_form in text:
                violations.append({
                    "message": f"AI用語の表記統一: '{acronym}'と'{full_form}'",
                    "details": {"acronym": acronym, "full_form": full_form}
                })
        
        return violations
    
    def _check_number_formats(self, text: str, bullet_points: List[str]) -> List[Dict[str, Any]]:
        """Check number format consistency."""
        violations = []
        
        # Find different number formats
        formats = {
            'comma_separated': re.findall(r'\d{1,3}(?:,\d{3})+', text),
            'plain_numbers': re.findall(r'\b\d{4,}\b', text),
            'percentages': re.findall(r'\d+(?:\.\d+)?%', text),
            'currencies': re.findall(r'\d+(?:円|ドル|USD|JPY)', text)
        }
        
        # Check for inconsistent large number formatting
        comma_numbers = formats['comma_separated']
        plain_numbers = [n for n in formats['plain_numbers'] if len(n) >= 4]
        
        if comma_numbers and plain_numbers:
            violations.append({
                "message": "大きな数値の表記が不統一（カンマ区切りと非区切り）",
                "details": {
                    "comma_format": comma_numbers[:3],
                    "plain_format": plain_numbers[:3]
                }
            })
        
        return violations
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from text."""
        # Look for common bullet point patterns
        patterns = [
            r'^[-*•]\s*(.+)$',  # - or * or • bullets
            r'^\d+\.\s*(.+)$',   # numbered lists
            r'^・(.+)$'          # Japanese bullet
        ]
        
        bullet_points = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    bullet_points.append(match.group(1))
                    break
            else:
                # If no bullet pattern matches, treat as regular sentence
                if len(line) > 20:  # Ignore very short lines
                    bullet_points.append(line)
        
        return bullet_points
    
    def _calculate_quality_score(self, violations: List[Dict[str, Any]]) -> float:
        """Calculate overall quality score based on violations."""
        if not violations:
            return 1.0
        
        # Weight violations by severity
        severity_weights = {
            "error": 0.3,
            "warning": 0.1,
            "info": 0.05
        }
        
        total_penalty = sum(
            severity_weights.get(v["severity"], 0.1) 
            for v in violations
        )
        
        # Cap the penalty to ensure score doesn't go below 0
        quality_score = max(0.0, 1.0 - total_penalty)
        
        return quality_score
    
    def _determine_quality_level(
        self, 
        quality_score: float, 
        violations: List[Dict[str, Any]]
    ) -> es.QualityLevel:
        """Determine quality level based on score and violations."""
        error_count = len([v for v in violations if v["severity"] == "error"])
        
        if error_count > 0:
            return es.QualityLevel.FAILED
        elif quality_score >= 0.9:
            return es.QualityLevel.EXCELLENT
        elif quality_score >= 0.8:
            return es.QualityLevel.GOOD
        elif quality_score >= 0.6:
            return es.QualityLevel.ACCEPTABLE
        else:
            return es.QualityLevel.POOR
    
    def _calculate_metrics(self, text: str, bullet_points: List[str]) -> Dict[str, Any]:
        """Calculate content metrics."""
        return {
            "character_count": len(text),
            "bullet_point_count": len(bullet_points),
            "avg_bullet_length": sum(len(bp) for bp in bullet_points) / len(bullet_points) if bullet_points else 0,
            "sentence_count": len(re.findall(r'[。！？]', text)),
            "comma_count": text.count('、'),
            "specific_numbers": len(re.findall(r'\d+', text)),
            "proper_nouns": len(re.findall(r'[A-Z][a-zA-Z]+|[ァ-ヶー]{2,}', text))
        }


def validate_article_content(
    summary_points: List[str],
    title: str = None,
    source_content: str = None,
    production_mode: bool = True
) -> es.ValidationResult:
    """
    Validate article content with comprehensive checks and production-grade standards.
    
    Args:
        summary_points: List of summary bullet points
        title: Article title (optional)
        source_content: Source article content (optional)
        production_mode: Enable stricter production quality standards
        
    Returns:
        ValidationResult with detailed analysis and rejection recommendations
    """
    validator = ContentValidator()
    
    # Validate summary points with enhanced production standards
    result = validator.validate_content(summary_points, "summary")
    
    # Add title validation if provided
    if title:
        title_result = validator.validate_content(title, "title")
        # Merge results (simplified)
        result.violations.extend(title_result.violations)
        result.quality_score = (result.quality_score + title_result.quality_score) / 2
    
    # Apply production-grade quality enhancements
    if production_mode:
        result = _enhance_validation_for_production(result, summary_points, title)
    
    return result


def _enhance_validation_for_production(
    result: es.ValidationResult, 
    summary_points: List[str], 
    title: str = None
) -> es.ValidationResult:
    """
    Apply enhanced validation criteria for production quality.
    
    Args:
        result: Initial validation result
        summary_points: Summary points to validate
        title: Article title
        
    Returns:
        Enhanced validation result with production standards
    """
    # Check for critical production quality issues
    critical_issues = []
    
    # 1. Check for meta-text artifacts that escaped cleaning
    meta_patterns = [
        r'はい、?承知.*?しました',
        r'以下.*?翻訳',
        r'こちら.*?要約',
        r'について.*?です$',
        r'AI技術.*?です$',
        r'として.*?注目されています$'
    ]
    
    for point in summary_points:
        for pattern in meta_patterns:
            if re.search(pattern, point):
                critical_issues.append(
                    es.ValidationViolation(
                        rule_id="PROD_META_TEXT",
                        severity=es.Severity.ERROR,
                        message=f"Meta-text artifact detected: {point[:50]}...",
                        suggestion="Remove meta-commentary and provide factual content"
                    )
                )
                break
    
    # 2. Check for insufficient detail (production requires specific information)
    for i, point in enumerate(summary_points):
        if len(point) < 50:  # Stricter minimum for production
            critical_issues.append(
                es.ValidationViolation(
                    rule_id="PROD_INSUFFICIENT_DETAIL",
                    severity=es.Severity.ERROR,
                    message=f"Summary point {i+1} too brief for production quality",
                    suggestion="Expand with specific details, numbers, or context"
                )
            )
        
        # Check for lack of specific information
        if not re.search(r'(\d+|発表|リリース|開発|投資|企業|製品|技術|AI|研究|実装|導入|提供|改善|向上)', point):
            critical_issues.append(
                es.ValidationViolation(
                    rule_id="PROD_VAGUE_CONTENT",
                    severity=es.Severity.WARNING,
                    message=f"Summary point {i+1} lacks specific information",
                    suggestion="Include concrete details, company names, or technical specifics"
                )
            )
    
    # 3. Check title quality (if provided)
    if title:
        if len(title) < 20:
            critical_issues.append(
                es.ValidationViolation(
                    rule_id="PROD_TITLE_TOO_SHORT",
                    severity=es.Severity.ERROR,
                    message="Title too short for production quality",
                    suggestion="Expand title with specific company/technology names"
                )
            )
        
        if not re.search(r'(AI|技術|開発|企業|製品|サービス|リリース|発表)', title):
            critical_issues.append(
                es.ValidationViolation(
                    rule_id="PROD_TITLE_VAGUE",
                    severity=es.Severity.WARNING,
                    message="Title lacks specific AI/tech terminology",
                    suggestion="Include specific technology or company references"
                )
            )
    
    # 4. Overall content consistency check
    if len(summary_points) < 3:
        critical_issues.append(
            es.ValidationViolation(
                rule_id="PROD_INSUFFICIENT_POINTS",
                severity=es.Severity.ERROR,
                message="Insufficient summary points for production article",
                suggestion="Generate at least 3 comprehensive summary points"
            )
        )
    
    # Add critical issues to result
    result.violations.extend(critical_issues)
    
    # Adjust quality score based on production criteria
    error_count = sum(1 for v in critical_issues if v.severity == es.Severity.ERROR)
    warning_count = sum(1 for v in critical_issues if v.severity == es.Severity.WARNING)
    
    # Production penalty scoring
    production_penalty = (error_count * 0.3) + (warning_count * 0.1)
    result.quality_score = max(0.0, result.quality_score - production_penalty)
    
    # Set quality level based on enhanced criteria
    if error_count > 0:
        result.quality_level = es.QualityLevel.POOR
    elif warning_count > 2:
        result.quality_level = es.QualityLevel.ACCEPTABLE
    else:
        result.quality_level = es.QualityLevel.EXCELLENT
    
    return result