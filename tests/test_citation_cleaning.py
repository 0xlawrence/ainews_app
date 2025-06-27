#!/usr/bin/env python3
"""Test citation cleaning functionality with pytest."""

import pytest
import re
from unittest.mock import AsyncMock

# Import the citation generator
try:
    from src.utils.citation_generator import CitationGenerator
    HAS_CITATION_GENERATOR = True
except ImportError:
    HAS_CITATION_GENERATOR = False


@pytest.mark.skipif(not HAS_CITATION_GENERATOR, reason="CitationGenerator not available")
class TestCitationCleaning:
    """Test citation cleaning functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock the LLM router to avoid dependencies
        self.generator = CitationGenerator(llm_router=None)
    
    @pytest.mark.parametrize("input_text,expected_pattern", [
        # Test meta-response removal
        (
            "はい、承知いたしました。以下に、ご要望に沿った形で要約翻訳を作成します。**翻訳:** OpenAIが新しいGPT-5モデルを発表しました。",
            r"OpenAIが新しいGPT-5モデルを発表しました。?"
        ),
        # Test translation prefix removal
        (
            "翻訳: GoogleのGemini 2.5が大幅な性能向上を実現。",
            r"GoogleのGemini 2\.5が大幅な性能向上を実現。?"
        ),
        # Test bracket prefix removal
        (
            "【翻訳】Microsoftが10億ドルの追加投資を発表。",
            r"Microsoftが10億ドルの追加投資を発表。?"
        ),
        # Test template phrase removal
        (
            "このAI技術は画期的な進歩という特徴があります。",
            r"このAI技術は画期的な進歩$"
        ),
        # Test numbering removal
        (
            "1. GoogleのGemini 2.5 Proが発表され、推論能力が大幅に向上。",
            r"GoogleのGemini 2\.5 Proが発表され、推論能力が大幅に向上。?"
        ),
        # Test empty result for full quotes
        (
            "「OpenAIが次世代言語モデルを発表」",
            r"OpenAIが次世代言語モデルを発表$"
        ),
    ])
    def test_clean_llm_response(self, input_text, expected_pattern):
        """Test LLM response cleaning with various inputs."""
        cleaned = self.generator._clean_llm_response(input_text)
        assert re.match(expected_pattern, cleaned), f"Cleaned text '{cleaned}' doesn't match pattern '{expected_pattern}'"
        
        # Ensure output is not empty for valid inputs
        if "OpenAI" in input_text or "Google" in input_text or "Microsoft" in input_text:
            assert len(cleaned) > 0, f"Valid input should not result in empty output: '{input_text}'"
    
    def test_multiline_processing(self):
        """Test multi-line text processing."""
        multiline_input = """はい、承知しました。
以下に要約翻訳を作成いたします。

翻訳: Microsoftによる大規模投資発表について詳細記事"""
        
        cleaned = self.generator._clean_llm_response(multiline_input)
        assert "Microsoftによる大規模投資発表について詳細記事" in cleaned
        assert "承知しました" not in cleaned
        assert "以下に" not in cleaned
    
    def test_japanese_content_preference(self):
        """Test that Japanese content is preferred over English meta-text."""
        mixed_input = """Processing your request...
翻訳: Googleの最新AI技術が企業向けに提供開始
Please wait for completion."""
        
        cleaned = self.generator._clean_llm_response(mixed_input)
        assert "Googleの最新AI技術が企業向けに提供開始" == cleaned
        assert "Processing" not in cleaned
        assert "Please wait" not in cleaned
    
    def test_empty_and_invalid_inputs(self):
        """Test handling of empty and invalid inputs."""
        assert self.generator._clean_llm_response("") == ""
        assert self.generator._clean_llm_response("   ") == ""
        assert self.generator._clean_llm_response(None) == ""
    
    def test_quote_handling(self):
        """Test proper quote mark handling."""
        # Should remove surrounding quotes but keep content
        input_with_quotes = "「このAI技術は革新的です」"
        cleaned = self.generator._clean_llm_response(input_with_quotes)
        assert cleaned == "このAI技術は革新的です"
        
        # Should not remove quotes that are part of content
        input_with_internal_quotes = "AIが「人間を超えた」と評価される"
        cleaned = self.generator._clean_llm_response(input_with_internal_quotes)
        assert "「人間を超えた」" in cleaned
    
    def test_length_validation(self):
        """Test that cleaned responses have reasonable length."""
        long_input = "翻訳: " + "とても長い文章が続きます。" * 20
        cleaned = self.generator._clean_llm_response(long_input)
        
        # Should not be empty
        assert len(cleaned) > 0
        # Should remove the prefix
        assert not cleaned.startswith("翻訳:")


@pytest.mark.skipif(not HAS_CITATION_GENERATOR, reason="CitationGenerator not available") 
def test_citation_generator_initialization():
    """Test that CitationGenerator can be initialized without errors."""
    generator = CitationGenerator(llm_router=None)
    assert generator is not None
    assert hasattr(generator, '_clean_llm_response')


# New test cases for enhanced quality validation

def test_enhanced_meta_pattern_detection():
    """Test enhanced meta pattern detection in citation cleaning."""
    from src.utils.citation_generator import CitationGenerator
    
    generator = CitationGenerator(llm_router=None)
    
    # Test enhanced Japanese meta-patterns
    test_cases = [
        # New acknowledgment patterns
        "承知いたしました。翻訳: OpenAIが新技術を発表しました",
        "分かりました。以下が要約です: AI技術の進歩について報告",
        "理解しました。次のように翻訳いたします: 企業の最新発表", 
        
        # New task completion patterns
        "以下が翻訳結果です: 半導体技術の革新について",
        "次のように要約します: Google AIの新サービス開始",
        "こちらが日本語要約です: Meta社の研究成果発表",
        
        # New task declaration patterns
        "作成いたします。翻訳: Microsoft社のAI戦略発表",
        "生成します。**翻訳**: Anthropic社の新モデル発表",
        "翻訳いたします: Apple社のAI機能統合について"
    ]
    
    expected_results = [
        "OpenAIが新技術を発表しました",
        "AI技術の進歩について報告", 
        "企業の最新発表",
        "半導体技術の革新について",
        "Google AIの新サービス開始",
        "Meta社の研究成果発表",
        "Microsoft社のAI戦略発表",
        "Anthropic社の新モデル発表",
        "Apple社のAI機能統合について"
    ]
    
    for i, test_input in enumerate(test_cases):
        cleaned = generator._clean_llm_response(test_input)
        expected = expected_results[i]
        assert cleaned == expected, f"Failed for case {i}: expected '{expected}', got '{cleaned}'"


def test_enhanced_template_phrase_removal():
    """Test enhanced template phrase removal."""
    from src.utils.citation_generator import CitationGenerator
    
    generator = CitationGenerator(llm_router=None)
    
    # Test enhanced template phrases
    test_cases = [
        "OpenAI社が新しいAI技術を発表したという重要なニュースがあります。",
        "Google DeepMindの研究成果について詳しく説明しています。",
        "Meta社のAI戦略に関して重要な報告をしています。",
        "Microsoft社の最新AI技術として注目されています。",
        "Anthropic社の新モデルが期待されています。",
        "Apple社のAI統合として話題になっています。"
    ]
    
    expected_results = [
        "OpenAI社が新しいAI技術を発表した",
        "Google DeepMindの研究成果",
        "Meta社のAI戦略",
        "Microsoft社の最新AI技術",
        "Anthropic社の新モデル",
        "Apple社のAI統合"
    ]
    
    for i, test_input in enumerate(test_cases):
        cleaned = generator._clean_llm_response(test_input)
        expected = expected_results[i]
        assert cleaned == expected, f"Failed for case {i}: expected '{expected}', got '{cleaned}'"


def test_production_quality_validation():
    """Test production quality validation enhancements."""
    from src.utils.content_validator import validate_article_content
    
    # Test cases with production quality issues
    
    # Case 1: Meta-text artifacts
    meta_text_points = [
        "はい、承知いたしました。OpenAI社が新技術を発表",
        "以下に翻訳いたします。Google AIの進展について",
        "こちらが要約です。Meta社の研究成果"
    ]
    
    result = validate_article_content(meta_text_points, production_mode=True)
    meta_errors = [v for v in result.violations if v.rule_id == "PROD_META_TEXT"]
    assert len(meta_errors) > 0, "Should detect meta-text artifacts"
    
    # Case 2: Insufficient detail
    brief_points = [
        "AI技術が進歩しました",  # Too brief
        "新しいサービスが開始されました", # Too brief 
        "企業が発表を行いました"  # Too brief
    ]
    
    result = validate_article_content(brief_points, production_mode=True)
    detail_errors = [v for v in result.violations if v.rule_id == "PROD_INSUFFICIENT_DETAIL"]
    assert len(detail_errors) > 0, "Should detect insufficient detail"
    
    # Case 3: Good quality content
    good_points = [
        "OpenAI社が2025年にGPT-5の商用リリースを発表し、推論能力が前世代比50%向上すると報告しました",
        "Google DeepMindが量子コンピューティングとAIの融合研究で新たな breakthrough を達成し、計算効率が10倍改善",
        "Microsoft社がAzure AI Studioに新機能を追加し、企業向けAIアプリケーション開発時間を40%短縮する tools を提供開始"
    ]
    
    result = validate_article_content(good_points, production_mode=True)
    assert result.quality_score > 0.7, f"Good content should have high score, got {result.quality_score}"
    critical_errors = [v for v in result.violations if v.severity.value == "ERROR"]
    assert len(critical_errors) == 0, "Good content should not have critical errors"


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])