"""
Common text processing utilities for Japanese text normalization and cleaning.

This module provides centralized text processing functions used across
the application for consistent text handling.
"""

import re
from typing import List, Dict, Any

from src.constants.settings import TEXT_LIMITS, QUALITY_CONTROLS
from src.constants.messages import CLEANING_PATTERNS


def normalize_japanese_text(text: str) -> str:
    """
    Normalize Japanese text by removing redundant expressions and ensuring consistent polite form.
    
    Args:
        text: Input Japanese text
        
    Returns:
        Normalized Japanese text
    """
    if not text:
        return ""
    
    # Remove redundant expressions
    redundant_patterns = [
        (r'ことができます。.*?ことができます。', 'ことができます。'),
        (r'ことになります。.*?ことになります。', 'ことになります。'),
        (r'と思われます。.*?と思われます。', 'と思われます。'),
        (r'することが可能です。.*?することが可能です。', 'することが可能です。'),
        (r'に関しては、', 'については、'),
        (r'について述べると、', 'については、'),
        (r'という形で', ''),
        (r'といった感じで', ''),
        (r'のような状況です', 'です'),
        (r'ということが言えます', 'と言えます')
    ]
    
    for pattern, replacement in redundant_patterns:
        text = re.sub(pattern, replacement, text)
    
    # Ensure consistent polite form (desu/masu)
    polite_patterns = [
        (r'である。', 'です。'),
        (r'だ。', 'です。'),
        (r'([^ます])る。', r'\1ます。'),
        (r'した。', 'しました。'),
        (r'([^あり])ない。', r'\1ません。'),
    ]
    
    for pattern, replacement in polite_patterns:
        text = re.sub(pattern, replacement, text)
    
    # Clean up multiple periods and whitespace
    text = re.sub(r'。+', '。', text)
    text = re.sub(r'\s+', ' ', text.strip())
    
    return text


def clean_llm_response(text: str) -> str:
    """
    Clean LLM response to extract only the relevant content.
    
    Args:
        text: Raw LLM response text
        
    Returns:
        Cleaned text content
    """
    if not text:
        return ""
    
    text = text.strip()
    
    # Handle multi-line responses intelligently
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    
    # Apply meta-pattern removal
    best_line = ""
    for line in lines[:3]:  # Check first 3 lines only
        cleaned_line = line
        
        # Apply meta-patterns to this line
        for pattern in CLEANING_PATTERNS['meta_removal']:
            cleaned_line = re.sub(pattern, r'\1' if r'\1' in pattern else '', cleaned_line, flags=re.IGNORECASE)
        
        cleaned_line = cleaned_line.strip()
        
        # Skip if line is primarily English meta-text
        if re.search(r'^[A-Za-z\s\.\,\:\!\?]+$', cleaned_line):
            continue
        
        # Skip common Japanese meta-responses
        if re.search(r'^(はい|承知|以下|要約|翻訳|作成)', cleaned_line) and not re.search(r'(発表|技術|投資|企業|サービス)', cleaned_line):
            continue
            
        # Check for Japanese content that seems like actual content
        if re.search(QUALITY_CONTROLS['japanese_char_patterns'], cleaned_line) and len(cleaned_line) > 10:
            best_line = cleaned_line
            break
    
    # Fallback to first line if no Japanese found
    if not best_line and lines:
        best_line = lines[0]
        # Apply meta-patterns to fallback
        for pattern in CLEANING_PATTERNS['meta_removal']:
            best_line = re.sub(pattern, r'\1' if r'\1' in pattern else '', best_line, flags=re.IGNORECASE)
    
    text = best_line.strip()
    
    # Remove only paired quote marks at start and end
    text = re.sub(r'^[「『"](.*?)[」』"]$', r'\1', text)
    
    # Remove trailing template phrases
    template_phrases = [
        r'という.*?があります。?$',
        r'について.*?です。?$',
        r'に関する.*?記事$',
        r'の詳細.*?$',
    ]
    
    for phrase in template_phrases:
        text = re.sub(phrase, '', text)
    
    return text.strip()


def normalize_title_for_comparison(title: str) -> str:
    """
    Normalize title for better comparison by removing common prefixes/suffixes.
    
    Args:
        title: Original title
        
    Returns:
        Normalized title
    """
    # Convert to lowercase for comparison
    normalized = title.lower()
    
    # Remove common prefixes that might differ between sources
    for prefix_pattern in CLEANING_PATTERNS['title_prefixes']:
        normalized = re.sub(prefix_pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove common suffixes
    for suffix_pattern in CLEANING_PATTERNS['title_suffixes']:
        normalized = re.sub(suffix_pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove extra whitespace and normalize
    normalized = re.sub(r'\s+', ' ', normalized.strip())
    
    return normalized


def truncate_at_sentence_boundary(text: str, max_length: int, placeholder: str = '…') -> str:
    """
    Truncate text at sentence boundaries when possible.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        placeholder: Placeholder for truncated text
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    # Try to find sentence break points within limit
    sentence_breaks = list(re.finditer(r'[。、]', text[:max_length + 10]))
    if sentence_breaks:
        # Take the last sentence break within reasonable range
        last_break = sentence_breaks[-1]
        if last_break.end() <= max_length - len(placeholder):
            return text[:last_break.end()]
    
    # Fallback to simple truncation
    return text[:max_length - len(placeholder)] + placeholder


def extract_japanese_sentences(text: str, min_length: int = 30, max_length: int = 300) -> List[str]:
    """
    Extract meaningful Japanese sentences from text.
    
    Args:
        text: Input text
        min_length: Minimum sentence length
        max_length: Maximum sentence length
        
    Returns:
        List of extracted sentences
    """
    # Split by sentences
    sentences = re.split(r'[。.!?]', text)
    meaningful_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if (min_length <= len(sentence) <= max_length and 
            not any(word in sentence.lower() for word in [
                "申し訳", "すみません", "sorry", "i apologize", "i cannot",
                "以下に", "要約します", "まとめると", "について説明"
            ])):
            meaningful_sentences.append(sentence)
    
    return meaningful_sentences


def ensure_sentence_completeness(text: str, target_length: int) -> str:
    """
    Ensure text is complete sentences within target length.
    
    Args:
        text: Input text
        target_length: Target length
        
    Returns:
        Text with complete sentences
    """
    if len(text) <= target_length:
        return text
    
    # Find last complete sentence within limit
    sentences = re.split(r'[。、]', text)
    if sentences:
        result = ""
        for sentence in sentences:
            if len(result + sentence) < target_length - 5:  # Leave room for punctuation
                result += sentence + "。"
            else:
                break
        return result.rstrip("。。") + "。" if result else text[:target_length - 3] + "..."
    
    return text[:target_length - 3] + "..."


def detect_language_ratio(text: str) -> Dict[str, float]:
    """
    Detect the ratio of Japanese vs other characters in text.
    
    Args:
        text: Input text
        
    Returns:
        Dictionary with language ratios
    """
    japanese_chars = re.findall(QUALITY_CONTROLS['japanese_char_patterns'], text)
    english_chars = re.findall(r'[a-zA-Z]', text)
    total_chars = len(re.findall(r'[a-zA-Z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))
    
    if total_chars == 0:
        return {'japanese': 0.0, 'english': 0.0, 'other': 0.0}
    
    japanese_ratio = len(japanese_chars) / total_chars
    english_ratio = len(english_chars) / total_chars
    other_ratio = 1.0 - japanese_ratio - english_ratio
    
    return {
        'japanese': japanese_ratio,
        'english': english_ratio, 
        'other': max(0.0, other_ratio)
    }


def standardize_punctuation(text: str) -> str:
    """
    Standardize punctuation in Japanese text.
    
    Args:
        text: Input text
        
    Returns:
        Text with standardized punctuation
    """
    # Standardize punctuation marks
    punctuation_map = {
        '，': '、',
        '．': '。',
        '！': '!',
        '？': '?',
        '（': '(',
        '）': ')',
        '「': '「',
        '」': '」'
    }
    
    for old, new in punctuation_map.items():
        text = text.replace(old, new)
    
    # Clean up spacing around punctuation
    text = re.sub(r'\s+([。、!?])', r'\1', text)
    text = re.sub(r'([。、!?])\s+', r'\1 ', text)
    
    return text.strip()