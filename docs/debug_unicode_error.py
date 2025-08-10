#!/usr/bin/env python3
"""
Debug script to identify Unicode encoding issues in the newsletter generation process.
"""

import json
import unicodedata
import sys
from pathlib import Path

def analyze_unicode_content(text: str, context: str = "unknown") -> dict:
    """Analyze Unicode content for potential issues."""
    analysis = {
        "context": context,
        "length": len(text),
        "issues": [],
        "problematic_positions": [],
        "surrogate_pairs": [],
        "control_chars": [],
        "emoji_positions": []
    }
    
    for i, char in enumerate(text):
        try:
            category = unicodedata.category(char)
            code_point = ord(char)
            
            # Check for surrogate pairs
            if 0xD800 <= code_point <= 0xDFFF:
                analysis["surrogate_pairs"].append({
                    "position": i,
                    "char": repr(char),
                    "code_point": hex(code_point),
                    "category": category
                })
                analysis["problematic_positions"].append(i)
            
            # Check for control characters
            elif category == 'Cc' and char not in '\n\t\r':
                analysis["control_chars"].append({
                    "position": i,
                    "char": repr(char),
                    "code_point": hex(code_point)
                })
                analysis["problematic_positions"].append(i)
            
            # Check for emojis and symbols
            elif category in ['So', 'Sm', 'Sc', 'Sk']:
                analysis["emoji_positions"].append({
                    "position": i,
                    "char": char,
                    "code_point": hex(code_point),
                    "category": category
                })
        
        except Exception as e:
            analysis["issues"].append(f"Error at position {i}: {e}")
    
    return analysis

def test_json_encoding(text: str, context: str = "unknown") -> dict:
    """Test JSON encoding of text."""
    result = {
        "context": context,
        "length": len(text),
        "json_encoding_success": False,
        "json_length": 0,
        "error": None
    }
    
    try:
        # Test simple JSON encoding
        json_str = json.dumps({"content": text}, ensure_ascii=False)
        result["json_encoding_success"] = True
        result["json_length"] = len(json_str)
        
        # Check if the error position (61405) is within our JSON
        if len(json_str) > 61405:
            char_at_error = json_str[61405] if len(json_str) > 61405 else None
            result["char_at_error_position"] = repr(char_at_error) if char_at_error else None
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def analyze_newsletter_file(file_path: str) -> dict:
    """Analyze a newsletter file for Unicode issues."""
    print(f"Analyzing file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Analyze the content
        unicode_analysis = analyze_unicode_content(content, f"file: {file_path}")
        json_test = test_json_encoding(content, f"file: {file_path}")
        
        return {
            "unicode_analysis": unicode_analysis,
            "json_test": json_test,
            "file_size": len(content)
        }
        
    except Exception as e:
        return {"error": str(e)}

def main():
    """Main debug function."""
    print("Unicode Error Debug Analysis")
    print("=" * 50)
    
    # Find the most recent newsletter file
    drafts_dir = Path("drafts/2025/07")
    if not drafts_dir.exists():
        print("No drafts directory found")
        return
    
    newsletter_files = list(drafts_dir.glob("*.md"))
    if not newsletter_files:
        print("No newsletter files found")
        return
    
    # Use the most recent file
    latest_file = max(newsletter_files, key=lambda f: f.stat().st_mtime)
    print(f"Analyzing latest file: {latest_file.name}")
    
    # Analyze the file
    analysis = analyze_newsletter_file(str(latest_file))
    
    if "error" in analysis:
        print(f"Error analyzing file: {analysis['error']}")
        return
    
    # Print results
    print(f"\nFile size: {analysis['file_size']} characters")
    
    unicode_analysis = analysis['unicode_analysis']
    print(f"\nUnicode Analysis:")
    print(f"  Surrogate pairs found: {len(unicode_analysis['surrogate_pairs'])}")
    print(f"  Control characters found: {len(unicode_analysis['control_chars'])}")
    print(f"  Emoji/symbols found: {len(unicode_analysis['emoji_positions'])}")
    print(f"  Problematic positions: {len(unicode_analysis['problematic_positions'])}")
    
    if unicode_analysis['surrogate_pairs']:
        print(f"\nSurrogate pairs:")
        for sp in unicode_analysis['surrogate_pairs'][:5]:  # Show first 5
            print(f"  Position {sp['position']}: {sp['char']} (U+{sp['code_point'][2:].upper()})")
    
    if unicode_analysis['emoji_positions']:
        print(f"\nEmoji/symbols:")
        for emoji in unicode_analysis['emoji_positions'][:10]:  # Show first 10
            print(f"  Position {emoji['position']}: {emoji['char']} (U+{emoji['code_point'][2:].upper()})")
    
    json_test = analysis['json_test']
    print(f"\nJSON Encoding Test:")
    print(f"  Success: {json_test['json_encoding_success']}")
    if json_test['json_encoding_success']:
        print(f"  JSON length: {json_test['json_length']}")
        if 'char_at_error_position' in json_test and json_test['char_at_error_position']:
            print(f"  Character at error position (61405): {json_test['char_at_error_position']}")
    else:
        print(f"  Error: {json_test['error']}")
    
    # Test specific positions around the error
    if json_test['json_encoding_success'] and json_test['json_length'] > 61405:
        print(f"\nAnalyzing around error position (61405):")
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the approximate position in the original content
            # This is a rough estimate - the actual position depends on JSON structure
            test_json = json.dumps({"content": content}, ensure_ascii=False)
            if len(test_json) > 61405:
                # Find the content part around position 61405
                content_start = test_json.find('"content": "') + 11
                content_end = test_json.rfind('"')
                content_in_json = test_json[content_start:content_end]
                
                # Estimate the position in original content
                error_in_content = 61405 - content_start
                if 0 <= error_in_content < len(content_in_json):
                    print(f"  Error position in content: approximately {error_in_content}")
                    print(f"  Characters around error: {repr(content_in_json[max(0, error_in_content-10):error_in_content+10])}")
        except Exception as e:
            print(f"  Error analyzing error position: {e}")

if __name__ == "__main__":
    main() 