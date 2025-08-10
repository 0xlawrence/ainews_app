"""
Common text processing utilities for Japanese text normalization and cleaning.

This module provides centralized text processing functions used across
the application for consistent text handling.
"""

import re
import unicodedata
from typing import Union, List, Optional

from src.constants.messages import CLEANING_PATTERNS
from src.config.settings import get_settings


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

    # CRITICAL FIX: Remove inappropriate period insertions before other processing
    text = fix_inappropriate_period_insertions(text)
    
    # Remove redundant expressions
    redundant_patterns = [
        # 連続出現の2回目以降を削除（最初の1回は保持）
        (r'ことができます。(\s*ことができます。)+', 'ことができます。'),
        (r'ことになります。.*?ことになります。', 'ことになります。'),
        (r'と思われます。.*?と思われます。', 'と思われます。'),
        # Make this less aggressive to keep first occurrence intact
        (r'(することが可能です。)(?:.*?することが可能です。)+', r'\1'),
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

    # Ensure exactly one occurrence of "ことができます。"
    try:
        occurrences = list(re.finditer(r'ことができます。', text))
        if len(occurrences) >= 2:
            # Keep the first occurrence intact; replace the rest with a shorter form
            # Replace from second onward
            def _replace_after_first(m_iter, s: str) -> str:
                first_end = occurrences[0].end()
                prefix = s[:first_end]
                suffix = s[first_end:]
                suffix = re.sub(r'ことができます。', 'できます。', suffix)
                return prefix + suffix
            text = _replace_after_first(occurrences, text)

        # If phrase was altered elsewhere (e.g., "ことできます。"), restore the first to desired form
        if re.search(r'ことできます。', text) and 'ことができます。' not in text:
            text = re.sub(r'ことできます。', 'ことができます。', text, count=1)
    except Exception:
        pass

    return text


def remove_duplicate_patterns(title: str) -> str:
    """
    Remove duplicate patterns from titles like 'LLMの技術LLM' -> 'LLMの技術'.

    Args:
        title: Input title text

    Returns:
        Title with duplications removed
    """
    if not title:
        return ""

    # Import duplicate patterns
    duplicate_patterns = CLEANING_PATTERNS.get('duplicate_patterns', [])

    cleaned_title = title
    for pattern in duplicate_patterns:
        try:
            # Apply the pattern with replacement that preserves the good part
            if 'の' in pattern and '\\1' in pattern:
                # For patterns like "(LLM)の([^のLLM]+)\\1", replace with "$1の$2"
                cleaned_title = re.sub(pattern, r'\1の\2', cleaned_title)
            elif 'で\\1' in pattern or 'が\\1' in pattern or 'を\\1' in pattern:
                # For patterns like "(Union[LLM, AI])で\\1", replace with just "$1"
                cleaned_title = re.sub(pattern, r'\1', cleaned_title)
            else:
                # For other patterns, replace with the first group
                cleaned_title = re.sub(pattern, r'\1\2', cleaned_title)
        except Exception:
            # If pattern fails, continue with next pattern
            continue

    # Remove any resulting double spaces or punctuation
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title.strip())

    return cleaned_title


def clean_llm_response(text: str) -> str:
    """Clean and normalize LLM response text."""
    if not text:
        return ""
    
    # Remove common LLM artifacts
    text = re.sub(r'^```(?:json|markdown)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    # Remove enclosing Japanese quotes if the whole text is wrapped
    text = re.sub(r'^「(.+?)」$', r'\1', text)
    
    # Remove common meta preambles and labels
    text = re.sub(r'^(?:以下が要約です|要約|Summary|概要)[：:]?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:翻訳|Japanese\s+translation)[：:]?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:\d+\.|[-\*•・])\s*', '', text)
    
    # Remove leading colon if present after cleaning
    text = re.sub(r'^[:：]\s*', '', text)
    
    # Remove specific trailing templates (keep core noun phrase)
    text = re.sub(r'に関して重要な報告をしています。?$', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


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


def intelligent_truncate(text: str, max_chars: int = 70) -> str:
    """
    Intelligently truncate Japanese text at natural breaking points suitable for
    titles/TOC, avoiding unnatural endings (particles, trailing comma).

    - Prefer sentence boundaries and punctuation within range
    - Avoid ending with hanging particles like 'は', 'が', 'を', 'に', 'で', 'と'
    - Avoid ending with '、' and roll back to a safer position

    Args:
        text: Input text to truncate
        max_chars: Maximum allowed characters

    Returns:
        Truncated text with natural ending
    """
    if not text or len(text) <= max_chars:
        return text

    # Expand window slightly to search for better natural breakpoints
    window = text[: max_chars + 20]

    # Candidate breakpoints ordered by preference
    breakpoint_patterns: list[tuple[str, bool]] = [
        # pattern, include_match
        (r'。', True),                 # sentence end
        (r'」', True),                 # closing quote
        (r'）', True),                 # closing paren
        (r'、', True),                 # comma (less preferred)
    ]

    best_cut = -1
    for pattern, include in breakpoint_patterns:
        matches = list(re.finditer(pattern, window))
        # Choose the last breakpoint that is <= max_chars
        for m in reversed(matches):
            cut_pos = m.end() if include else m.start()
            if cut_pos <= max_chars:
                best_cut = cut_pos
                break
        if best_cut != -1:
            break

    # If no good breakpoint, hard cut with ellipsis
    result = window[:max_chars]
    if best_cut != -1:
        result = window[:best_cut]

    result = result.rstrip()

    # Roll back if ends with undesirable particles or comma
    bad_endings = ('は', 'が', 'を', 'に', 'で', 'と', '、')
    if result.endswith(bad_endings):
        # Remove the final character and trim
        result = result[:-1].rstrip()

    # Ensure we end nicely; add ellipsis if we cut mid-sentence without punctuation
    if not result.endswith(('。', '」', '）')):
        # Add ellipsis only when there is remaining content beyond the cut
        if len(text) > len(result):
            result += '…'

    return result

def extract_japanese_sentences(text: str, min_length: int = 30, max_length: int = 300) -> list[str]:
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
    🔥 ULTRA THINK: 自然言語境界保持切断（文意を壊さない切断）

    Args:
        text: Input text
        target_length: Target length

    Returns:
        Text with complete sentences preserving meaning
    """
    if len(text) <= target_length:
        return text

    # Phase 1: 完全な文単位での切断を試行（「。」で終わる文）
    complete_sentences = re.split(r'(?<=。)', text)
    if len(complete_sentences) > 1:
        result = ""
        for sentence in complete_sentences:
            if len(result + sentence) <= target_length:
                result += sentence
            else:
                break
        if result and result.endswith('。'):
            return result

    # Phase 2: 自然な切断点を探索（文意を保持）
    if len(text) > target_length:
        # 自然な切断点の優先順位 (タイトル特化版)
        natural_breaks = [
            (r'。(?=[^」』])', 1),      # 文末の句点（引用外）
            (r'、(?=\w{8,})', 1),      # 読点（後に8文字以上ある場合）
            (r'(です)(?=。)', 1),       # 「です」の後（後読み回避）
            (r'(ます)(?=。)', 1),       # 「ます」の後
            (r'(ました)(?=。)', 1),     # 「ました」の後
            (r'(される)(?=。)', 1),     # 「される」の後
            (r'(?<=\d)(?=％|%)', 2),   # 数字の後の％記号前で切断（固定幅LB）
            (r'(?<=％|%)(?=[^」』])', 2), # ％記号の後で切断（固定幅LB）
            (r'(億|万|千|百)(?=(?:ドル|円)|人)', 2), # 単位の後で切断（前方一致）
            (r'((?:ドル|円)|人)(?=[^」』])', 2),     # 通貨・人の直後（後読み回避）
            (r'(により)(?=[^」』])', 1), # 「により」の後
            (r'(として)(?=[^」』])', 1), # 「として」の後
            (r'(において)(?=[^」』])', 1), # 「において」の後
            (r'([A-Z]{2,})(?=[^A-Z])', 3), # 英語略語の直後で切断
        ]

        best_cut_pos = -1
        best_priority = 999

        # 優先度順に切断点を探索（数字の小さい方が高優先度）
        for pattern, priority in natural_breaks:
            matches = list(re.finditer(pattern, text[:target_length + 20]))
            if matches and priority <= best_priority:
                # 最も後ろの（文字数制限に近い）切断点を選択
                for match in reversed(matches):
                    # グループ1がある場合はその末尾で切断（後読み回避パターン対応）
                    cut_end = match.end(1) if (match.lastindex and match.lastindex >= 1) else match.end()
                    if cut_end <= target_length - 3:  # 余裕を持たせる
                        if priority < best_priority or match.end() > best_cut_pos:
                            best_cut_pos = cut_end
                            best_priority = priority
                        break

        if best_cut_pos > 0:
            cut_text = text[:best_cut_pos].strip()
            # 適切な終端処理
            if not cut_text.endswith(('。', '、', 'です', 'ます', 'した')):
                cut_text += '。'
            return cut_text

    # Phase 3: 最後の手段 - 単語境界での切断
    if len(text) > target_length:
        # 助詞・動詞語尾等の不適切な切断を避ける
        bad_endings = ['の', 'が', 'を', 'に', 'で', 'と', 'は', 'も', 'し', 'て', 'れ', 'け']
        safe_cut = target_length - 10

        while safe_cut > target_length // 2:
            if text[safe_cut] in '、。' or not any(text[safe_cut-2:safe_cut].endswith(bad) for bad in bad_endings):
                return text[:safe_cut] + '。'
            safe_cut -= 1

    # Fallback: 元の動作
    return text[:target_length - 3] + "…"


def fix_inappropriate_period_insertions(text: str) -> str:
    """
    Fix inappropriate period insertions in Japanese text.
    
    This function addresses the critical issue where periods are being inserted
    in inappropriate locations like "1000。億ドル" or "Claude Code。の".
    
    Args:
        text: Input Japanese text with potential period insertion issues
        
    Returns:
        Text with period insertions fixed
    """
    if not text:
        return text
        
    # Pattern 1: Numbers followed by periods before units
    # Fix: "1000。億ドル" -> "1000億ドル"
    text = re.sub(r'(\d+)。(億|万|千|百|十)(ドル|円|人|台|件|社|年|月|日)', r'\1\2\3', text)
    
    # Pattern 2: Product/company names with periods before particles
    # Fix: "Claude Code。の" -> "Claude Codeの"
    text = re.sub(r'([A-Za-z]+[A-Za-z0-9]*|[\u30A0-\u30FF\u4E00-\u9FAF]+)。([のがをにでとは])', r'\1\2', text)
    
    # Pattern 3: Words followed by periods before continuation
    # Fix: "ダッシュボー。ド" -> "ダッシュボード"
    text = re.sub(r'([\u30A0-\u30FF\u4E00-\u9FAF]+)。([\u30A0-\u30FF\u4E00-\u9FAF]+)', r'\1\2', text)
    
    # Pattern 4: Decimal numbers with periods
    # Fix: "5.5。倍" -> "5.5倍"
    text = re.sub(r'(\d+\.\d+)。(倍|%|％)', r'\1\2', text)
    
    # Pattern 5: Periods followed by comma (incorrect punctuation)
    # Fix: "なり、。創作" -> "なり、創作"
    text = re.sub(r'、。', '、', text)
    
    # Pattern 6: Fix duplicate particle issues
    # Fix: "2025年にが" -> "2025年に"
    text = re.sub(r'(に|を|が|は|で|と|から)(が|は|を|に|で|と|から)', r'\1', text)
    
    # Pattern 7: Fix incomplete verb forms
    # Fix: "生み出しておりが" -> "生み出しており"
    text = re.sub(r'(ており|ており)が', r'\1', text)
    
    return text


def fix_particle_duplication(text: str) -> str:
    """
    Fix particle duplication issues in Japanese text.
    
    Args:
        text: Input Japanese text with potential particle duplication
        
    Returns:
        Text with particle duplication fixed
    """
    if not text:
        return text
        
    # Common particle duplication patterns
    particle_patterns = [
        (r'にが', 'に'),
        (r'をが', 'を'),
        (r'でが', 'で'),
        (r'とが', 'と'),
        (r'からが', 'から'),
        (r'ておりが', 'ており'),
        (r'ているが', 'ている'),
        (r'ましたが', 'ました'),
        (r'ですが', 'です'),
        (r'、は([^、。]*)', r'、\1'),  # Fix "、は動画" → "、動画"
        (r'この新機能が([^。]*)', r'この新機能は\1'),  # Fix "この新機能が" → "この新機能は" 
    ]
    
    for pattern, replacement in particle_patterns:
        text = re.sub(pattern, replacement, text)
        
    return text


def normalize_unicode_content(text: str) -> str:
    """Normalize Unicode content to prevent encoding issues."""
    if not text:
        return text
    
    try:
        # Normalize to NFC form
        normalized = unicodedata.normalize('NFC', text)
        
        # Handle surrogate pairs and invalid characters
        cleaned = ''
        i = 0
        while i < len(normalized):
            char = normalized[i]
            category = unicodedata.category(char)
            
            # Skip surrogate characters
            if category == 'Cs':
                i += 1
                continue
            
            # Replace control characters (except newlines and tabs)
            if category == 'Cc' and char not in '\n\t\r':
                cleaned += ' '
                i += 1
                continue
            
            cleaned += char
            i += 1
        
        return cleaned
    except Exception:
        # Fallback: return original text if normalization fails
        return text


def safe_encode_for_api(text: str) -> bytes:
    """Safely encode text for API transmission."""
    if not text:
        return b''
    
    # Normalize Unicode first
    normalized = normalize_unicode_content(text)
    
    # Encode with error handling
    try:
        return normalized.encode('utf-8', errors='replace')
    except Exception:
        # Fallback: encode as ASCII with replacement
        return normalized.encode('ascii', errors='replace')


def clean_emoji_and_special_chars(text: str) -> str:
    """Clean emoji and special characters that might cause encoding issues."""
    if not text:
        return text
    
    # Keep common emoji that are safe
    safe_emoji = ['🆙', '✅', '🚨', '⚠️', '📝', '🤖', '💡', '🔧', '📊', '🎯']
    
    cleaned = ''
    for char in text:
        # Keep safe emoji
        if char in safe_emoji:
            cleaned += char
            continue
        
        # Keep basic punctuation and alphanumeric
        if char.isalnum() or char in ' .,!?;:()[]{}"\'-_':
            cleaned += char
            continue
        
        # Check if it's a safe Unicode character
        try:
            category = unicodedata.category(char)
            # Keep letters, numbers, punctuation, symbols, and marks
            if category.startswith(('L', 'N', 'P', 'S', 'M')):
                # Additional check for surrogate pairs
                if not (0xD800 <= ord(char) <= 0xDFFF):
                    cleaned += char
            else:
                # Replace other characters with space
                cleaned += ' '
        except Exception:
            # If we can't determine the category, replace with space
            cleaned += ' '
    
    return cleaned


def validate_text_for_api(text: str) -> tuple[bool, str]:
    """Validate text for API transmission and return (is_valid, error_message)."""
    if not text:
        return True, ""
    
    try:
        # Try to encode the text
        encoded = text.encode('utf-8')
        
        # Check for surrogate pairs
        for i, char in enumerate(text):
            if 0xD800 <= ord(char) <= 0xDFFF:
                return False, f"Surrogate pair found at position {i}"
        
        return True, ""
    except UnicodeEncodeError as e:
        return False, f"Unicode encoding error: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"


def apply_quality_controls(text: str) -> str:
    """Apply quality control rules to text."""
    if not text:
        return text
    
    # Apply all text processing functions
    text = clean_llm_response(text)
    text = fix_inappropriate_period_insertions(text)
    text = fix_particle_duplication(text)
    text = normalize_unicode_content(text)
    
    return text


def extract_safe_text_for_api(text: str, max_length: Optional[int] = None) -> str:
    """Extract safe text for API transmission with optional length limit."""
    if not text:
        return ""
    
    # Apply all cleaning functions
    cleaned = apply_quality_controls(text)
    cleaned = clean_emoji_and_special_chars(cleaned)
    
    # Apply length limit if specified
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length-3] + "..."
    
    return cleaned


def detect_language_ratio(text: str) -> dict[str, float]:
    """
    Detect the ratio of Japanese vs other characters in text.

    Args:
        text: Input text

    Returns:
        Dictionary with language ratios
    """
    settings = get_settings()
    japanese_chars = re.findall(settings.processing.japanese_char_pattern, text)
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
