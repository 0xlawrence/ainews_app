"""
LLM response parsing and validation utilities.

This module handles parsing LLM responses into structured formats,
validating outputs, and estimating costs for different models.
"""

import json
import logging
import re
from typing import Union

from src.models.schemas import SummaryOutput
from src.utils.text_processing import (
    fix_inappropriate_period_insertions,
    fix_particle_duplication,
    clean_llm_response,
)
from src.constants.messages import CLEANING_PATTERNS

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parser for LLM responses with structured output validation."""
    
    def __init__(self):
        """Initialize the response parser."""
        logger.info("Response Parser initialized")
    
    def extract_summary_from_response(self, content: str, model_name: str) -> Union[SummaryOutput, None]:
        """Extract SummaryOutput from LLM response content."""
        if not content:
            return None

        content = content.strip()

        # Step 0: Remove meta preamble/artifacts before attempting JSON extraction
        content = self._remove_meta_preamble(content)

        # Try to extract JSON from various formats
        json_content = None

        # Method 1: Direct JSON parsing
        try:
            json_content = json.loads(content)
        except:
            pass

        # Method 2: Extract from markdown code blocks
        if json_content is None:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                try:
                    json_content = json.loads(json_match.group(1))
                except:
                    pass

        # Method 3: Find JSON object in text
        if json_content is None:
            json_match = re.search(r'\{[^{}]*"summary_points"[^{}]*\[[^\]]*\][^{}]*\}', content, re.DOTALL)
            if json_match:
                try:
                    json_content = json.loads(json_match.group(0))
                except:
                    pass

        # Method 4: Extract bullet list and convert to JSON
        if json_content is None:
            bullet_lines = re.findall(r'^[\-*•・\u2022]\s*(.+)', content, re.MULTILINE)
            if len(bullet_lines) >= 3:
                json_content = {"summary_points": bullet_lines[:4]}

        # Method 5: Extract meaningful sentences
        if json_content is None:
            sentences = re.split(r'[。.!?]', content)
            meaningful_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if (len(sentence) >= 30 and
                    not any(word in sentence.lower() for word in [
                        "申し訳", "すみません", "sorry", "i apologize", "i cannot",
                        "以下に", "要約します", "まとめると", "について説明", "json", "format"
                    ])):
                    meaningful_sentences.append(sentence)

            if len(meaningful_sentences) >= 3:
                json_content = {"summary_points": meaningful_sentences[:4]}

        # Try creating SummaryOutput
        if json_content:
            try:
                # Apply text processing to all summary points before creating SummaryOutput
                if 'summary_points' in json_content and isinstance(json_content['summary_points'], list):
                    processed_points = []
                    for point in json_content['summary_points']:
                        if isinstance(point, str):
                            # Apply all text processing fixes
                            processed_point = fix_inappropriate_period_insertions(point)
                            processed_point = fix_particle_duplication(processed_point)
                            processed_point = clean_llm_response(processed_point)
                            processed_points.append(processed_point)
                        else:
                            processed_points.append(point)
                    json_content['summary_points'] = processed_points
                
                return SummaryOutput(**json_content)
            except Exception as e:
                logger.warning(f"Pydantic validation failed: {e}, using text parsing")

        # Fallback to text parsing
        return self.parse_text_to_summary(content, model_name)

    def _remove_meta_preamble(self, text: str) -> str:
        """Remove common LLM meta preambles from text while preserving content."""
        try:
            patterns = CLEANING_PATTERNS.get('meta_removal', []) + [
                r'^はい、?承知(?:いた)?しました。?.*',
                r'^プロ.*編集者.*',
                r'^あなたは.*です.*',
                r'^以下が要約です[:：]\s*',
            ]

            cleaned = text
            for pat in patterns:
                cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)

            cleaned = clean_llm_response(cleaned)
            return cleaned
        except Exception:
            return text
    
    def parse_text_to_summary(self, content: str, model_name: str = "unknown") -> SummaryOutput:
        """Parse LLM text response to SummaryOutput when JSON parsing fails.

        This method extracts summary points from free-form text responses.
        """
        if not content or not content.strip():
            raise ValueError("Empty content provided for text parsing")

        lines = [line.strip() for line in content.split('\n') if line.strip()]
        summary_points = []

        # Extract bullet points or numbered items
        for line in lines:
            # Skip common headers/footers
            if any(skip in line.lower() for skip in ['要約', 'summary', '以下', '上記']):
                continue

            # Look for bullet points or numbered items
            if re.match(r'^[-*•]\s*', line) or re.match(r'^\d+\.\s*', line):
                # Remove bullet/number prefix
                clean_line = re.sub(r'^[-*•]\s*', '', line)
                clean_line = re.sub(r'^\d+\.\s*', '', clean_line)
                if len(clean_line) > 15:  # Substantial content
                    summary_points.append(clean_line)
            elif len(line) > 30 and '。' in line:
                # Treat longer sentences as summary points
                summary_points.append(line)

        # If no structured points found, split by sentences
        if not summary_points:
            sentences = re.split(r'[。.!?]', content)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:
                    summary_points.append(sentence + '。')

        # Ensure we have at least some content
        if not summary_points:
            summary_points = [f"記事の要約：{content[:100]}..." if len(content) > 100 else content]

        # Limit to reasonable number of points
        summary_points = summary_points[:5]
        
        # Apply text processing to all summary points before creating SummaryOutput
        processed_points = []
        for point in summary_points:
            if isinstance(point, str):
                # Apply all text processing fixes
                processed_point = fix_inappropriate_period_insertions(point)
                processed_point = fix_particle_duplication(processed_point)
                processed_point = clean_llm_response(processed_point)
                processed_points.append(processed_point)
            else:
                processed_points.append(point)

        return SummaryOutput(
            summary_points=processed_points,
            confidence_score=0.6,  # Lower confidence for text parsing
            source_reliability="medium",
            model_used=model_name,
            fallback_used=True,
            total_tokens=len(content) // 4,  # Rough estimate
            processing_time_seconds=0.1
        )
    
    def validate_summary(self, summary: SummaryOutput) -> None:
        """Lightweight sanity check for SummaryOutput produced via text parsing.

        Raises
        ------
        ValueError
            If the summary does not satisfy basic quality gates.
        """
        if not summary or not summary.summary_points:
            raise ValueError("Summary has no points")
        if not (1 <= len(summary.summary_points) <= 6):
            raise ValueError("Unexpected number of summary points")

        # Ensure each summary point is substantial (>=20 文字／characters)
        for pt in summary.summary_points:
            if len(pt.strip()) < 20:
                raise ValueError("Summary point too short (<20 chars)")


class CostEstimator:
    """Cost estimation utilities for different LLM models."""
    
    def __init__(self):
        """Initialize the cost estimator."""
        # USD per 1K tokens (approx.)
        self.rate_lookup = {
            "gemini-2.5-flash": 0.0005,
            "gemini-2.5-flash-lite": 0.0003,  # Even more cost-effective
            "claude-3-7-sonnet-20250219": 0.0008,
            "gpt-4o-mini": 0.0006,
        }
        logger.info("Cost Estimator initialized")
    
    def estimate_cost(self, model_name: str, prompt: str, response_content: str) -> float:
        """Very coarse cost estimation based on token count heuristics.

        Note: This is *not* an accurate billing estimator – it is only used for
        logging／monitoring. We approximate tokens ≈ characters / 4 and apply
        publicly-known $/1K‐token rates as of 2025-06 for major models. If the
        model is unknown, we return 0.0 to avoid crashing.
        """
        # Fallback safe-guard
        if not prompt or not response_content:
            return 0.0

        # Rough token count (characters / 4)
        prompt_tokens = max(1, len(prompt) // 4)
        response_tokens = max(1, len(response_content) // 4)
        total_tokens = prompt_tokens + response_tokens

        rate = self.rate_lookup.get(model_name, 0.0)
        return round(total_tokens / 1000 * rate, 4)
    
    def add_model_rate(self, model_name: str, rate_per_1k_tokens: float):
        """Add or update a model's cost rate."""
        self.rate_lookup[model_name] = rate_per_1k_tokens
        logger.info(f"Updated cost rate for {model_name}: ${rate_per_1k_tokens}/1K tokens")
    
    def get_supported_models(self) -> list:
        """Get list of supported models for cost estimation."""
        return list(self.rate_lookup.keys())