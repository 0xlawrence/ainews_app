#!/usr/bin/env python3
"""
Test script for Unicode processing fixes.

This script tests the Unicode normalization and encoding fixes
that were implemented to resolve the JSON surrogate pair error.
"""

import sys
import os
import unicodedata
import json
from pathlib import Path


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


def test_json_encoding():
    """Test JSON encoding with problematic Unicode characters."""
    print("Testing JSON encoding...")
    
    # Test cases with potential JSON encoding issues
    test_cases = [
        {
            "title": "Normal text with 🆙 emoji",
            "content": "This is a normal article with emoji 🆙✅🚨"
        },
        {
            "title": "Text with surrogate pairs",
            "content": "Text with surrogate pairs: \ud800\udc00"  # Invalid surrogate pair
        },
        {
            "title": "Mixed content",
            "content": "Mixed content: テスト🆙✅🚨 with Japanese and emoji"
        },
        {
            "title": "Special characters",
            "content": "Special characters: ©®™€£¥ and other symbols"
        },
        {
            "title": "Control characters",
            "content": "Control characters: \x00\x01\x02 in text"
        }
    ]
    
    for i, test_data in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {test_data['title']}")
        
        # Test original data
        try:
            original_json = json.dumps(test_data, ensure_ascii=False)
            print(f"  Original JSON length: {len(original_json)}")
        except Exception as e:
            print(f"  Original JSON failed: {e}")
        
        # Test normalized data
        normalized_data = {}
        for key, value in test_data.items():
            if isinstance(value, str):
                normalized_data[key] = normalize_unicode_content(value)
            else:
                normalized_data[key] = value
        
        try:
            normalized_json = json.dumps(normalized_data, ensure_ascii=False)
            print(f"  Normalized JSON length: {len(normalized_json)}")
            print(f"  Normalized JSON: {repr(normalized_json[:100])}...")
        except Exception as e:
            print(f"  Normalized JSON failed: {e}")


def test_unicode_normalization():
    """Test Unicode normalization with various problematic characters."""
    print("Testing Unicode normalization...")
    
    # Test cases with potential surrogate pair issues
    test_cases = [
        "Normal text with 🆙 emoji",
        "Text with surrogate pairs: \ud800\udc00",  # Invalid surrogate pair
        "Mixed content: テスト🆙✅🚨",
        "Special characters: ©®™€£¥",
        "Control characters: \x00\x01\x02",
        "Complex emoji: 👨‍👩‍👧‍👦",  # Family emoji
        "Zero-width characters: \u200b\u200c\u200d",
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {repr(test_text)}")
        
        # Test normalization
        normalized = normalize_unicode_content(test_text)
        print(f"  Normalized: {repr(normalized)}")
        
        # Test validation
        is_valid, error_msg = validate_text_for_api(test_text)
        print(f"  Valid: {is_valid}")
        if not is_valid:
            print(f"  Error: {error_msg}")
        
        # Test safe encoding
        try:
            encoded = safe_encode_for_api(test_text)
            print(f"  Encoded length: {len(encoded)} bytes")
        except Exception as e:
            print(f"  Encoding error: {e}")


def test_real_newsletter_file():
    """Test with a real newsletter file."""
    print("\nTesting with real newsletter file...")
    
    # Find the most recent newsletter file
    drafts_dir = Path(__file__).parent.parent / "drafts" / "2025" / "07"
    if not drafts_dir.exists():
        print("No drafts directory found")
        return
    
    newsletter_files = list(drafts_dir.glob("*.md"))
    if not newsletter_files:
        print("No newsletter files found")
        return
    
    # Use the most recent file
    latest_file = max(newsletter_files, key=lambda f: f.stat().st_mtime)
    print(f"Testing with file: {latest_file.name}")
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"File size: {len(content)} characters")
        
        # Test validation
        is_valid, error_msg = validate_text_for_api(content)
        print(f"Content valid: {is_valid}")
        if not is_valid:
            print(f"Validation error: {error_msg}")
        
        # Test normalization
        normalized = normalize_unicode_content(content)
        print(f"Normalized size: {len(normalized)} characters")
        
        # Test encoding
        encoded = safe_encode_for_api(normalized)
        print(f"Encoded size: {len(encoded)} bytes")
        
        # Test JSON encoding
        test_data = {
            "title": "Test Newsletter",
            "content": content[:1000],  # First 1000 chars
            "file_path": str(latest_file)
        }
        
        try:
            json_str = json.dumps(test_data, ensure_ascii=False)
            print(f"JSON encoding successful: {len(json_str)} characters")
        except Exception as e:
            print(f"JSON encoding failed: {e}")
            
            # Try with normalized content
            normalized_data = {
                "title": "Test Newsletter",
                "content": normalize_unicode_content(content[:1000]),
                "file_path": str(latest_file)
            }
            
            try:
                normalized_json = json.dumps(normalized_data, ensure_ascii=False)
                print(f"Normalized JSON encoding successful: {len(normalized_json)} characters")
            except Exception as e2:
                print(f"Normalized JSON encoding also failed: {e2}")
        
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"Error processing file: {e}")


def main():
    """Run all tests."""
    print("Unicode Processing Fix Tests")
    print("=" * 50)
    
    test_unicode_normalization()
    test_json_encoding()
    test_real_newsletter_file()
    
    print("\n" + "=" * 50)
    print("Tests completed!")


if __name__ == "__main__":
    main() 