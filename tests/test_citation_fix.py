#!/usr/bin/env python3
"""
Test script to verify the citation compatibility fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.citation_generator import CitationGenerator

def test_citation_compatibility():
    """Test the citation compatibility checker"""
    generator = CitationGenerator()
    
    # Test cases that should be blocked
    test_cases = [
        ("Anthropic、AI経済フューチャープログラム始動", "Meta CTO confirms massive offers for top AI executives", True),
        ("雇用喪失への懸念に対応", "top AI executives", True),
        ("Economic Futures Program", "massive offers", True),
        ("OpenAI announces new model", "Google releases Gemini update", True),
        ("Claude 3.5 Sonnet release", "ChatGPT-4 improvements", True),
        
        # Test cases that should be allowed
        ("Meta announces new hiring", "Meta CTO confirms massive offers", False),
        ("OpenAI research paper", "OpenAI GPT-4 update", False),
        ("AI safety research", "AI ethics guidelines", False),
    ]
    
    print("Testing citation compatibility checker...")
    
    for main_title, citation_title, should_block in test_cases:
        result = generator._is_incompatible_citation(main_title, citation_title)
        status = "✅ PASS" if result == should_block else "❌ FAIL"
        block_text = "BLOCKED" if result else "ALLOWED"
        expected_text = "should block" if should_block else "should allow"
        
        print(f"{status} {block_text} - {expected_text}")
        print(f"  Main: '{main_title}'")
        print(f"  Citation: '{citation_title}'")
        print()

if __name__ == "__main__":
    test_citation_compatibility()