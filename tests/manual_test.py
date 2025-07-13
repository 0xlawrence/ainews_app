#!/usr/bin/env python3
"""
Manual test for citation validation logic without full module imports.
"""

def test_domain_validation():
    """Test domain validation logic."""
    
    print("Testing Domain Validation Logic...")
    print("=" * 50)
    
    # Define topic domains (copy from our fix)
    topic_domains = {
        'hr_recruitment': ['hiring', 'recruitment', '採用', '人材', 'linkedin', '求人', 'job search', 'talent acquisition', 'massive offers'],
        'research_technical': ['research', 'researcher', '研究', '技術', 'model', 'モデル', 'algorithm', 'api', 'technical', 'poaches', 'scientists'],
        'economic_policy': ['economy', 'economic', '経済', '失業', '雇用喪失', 'job losses', 'policy', '政策', 'futures program'],
        'business_finance': ['investment', 'funding', 'ipo', 'valuation', '投資', 'venture', 'startup'],
        'product_tools': ['cli', 'api', 'tool', 'ツール', 'product', '製品', 'feature', '機能'],
        'local_infrastructure': ['ollama', 'local', 'ローカル', 'infrastructure', 'self-hosted']
    }
    
    def get_article_domains(title, content=""):
        """Get domains for an article."""
        article_text = (title + " " + content).lower()
        detected_domains = []
        for domain, keywords in topic_domains.items():
            if any(keyword in article_text for keyword in keywords):
                detected_domains.append(domain)
        return detected_domains
    
    def validate_same_topic_domain(main_title, main_content, citation_title, citation_content):
        """Validate domain compatibility."""
        main_domains = get_article_domains(main_title, main_content)
        citation_domains = get_article_domains(citation_title, citation_content)
        
        # If either article has no clear domain, be conservative and allow
        if not main_domains or not citation_domains:
            return True
        
        # Check for domain overlap
        has_overlap = bool(set(main_domains) & set(citation_domains))
        
        # Check for mutually exclusive domains
        mutually_exclusive_pairs = [
            ('hr_recruitment', 'research_technical'),
            ('economic_policy', 'hr_recruitment'),
            ('business_finance', 'research_technical'),
            ('local_infrastructure', 'economic_policy'),
        ]
        
        for main_domain in main_domains:
            for citation_domain in citation_domains:
                for exclusive1, exclusive2 in mutually_exclusive_pairs:
                    if (main_domain == exclusive1 and citation_domain == exclusive2) or \
                       (main_domain == exclusive2 and citation_domain == exclusive1):
                        print(f"Domain exclusion: {main_domain} vs {citation_domain}")
                        return False
        
        return has_overlap
    
    # Test cases
    test_cases = [
        {
            "name": "Meta research vs LinkedIn hiring",
            "main": ("MetaがOpenAIからトップAI研究者3名を獲得、元DeepMindの精鋭集結", "Meta research acquisition"),
            "citation": ("LinkedIn hiring assistant、LinkedInの科学者たちは、人材の…", "LinkedIn hiring tools"),
            "expected": False
        },
        {
            "name": "Economic policy vs hiring offers",
            "main": ("Anthropic、AI経済フューチャープログラムで雇用喪失への懸念を表明", "AI economic impact"),
            "citation": ("Meta CTO confirms massive offers to top AI executives", "Meta hiring executives"),
            "expected": False
        },
        {
            "name": "OpenAI model vs OpenAI API (should allow)",
            "main": ("OpenAI releases new GPT-4 Turbo with improved reasoning", "OpenAI model release"),
            "citation": ("OpenAI expands API access to deep research models", "OpenAI API access"),
            "expected": True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        main_title, main_content = test_case["main"]
        citation_title, citation_content = test_case["citation"]
        expected = test_case["expected"]
        
        result = validate_same_topic_domain(main_title, main_content, citation_title, citation_content)
        
        print(f"Test {i}: {test_case['name']}")
        print(f"  Main domains: {get_article_domains(main_title, main_content)}")
        print(f"  Citation domains: {get_article_domains(citation_title, citation_content)}")
        print(f"  Result: {result}, Expected: {expected}")
        print(f"  {'✅ PASS' if result == expected else '❌ FAIL'}")
        print()

def test_incompatible_patterns():
    """Test incompatible citation patterns."""
    
    print("Testing Incompatible Citation Patterns...")
    print("=" * 50)
    
    def is_incompatible_citation(main_title, citation_title):
        """Check for incompatible citations."""
        main_lower = main_title.lower()
        citation_lower = citation_title.lower()
        
        # Topic domain incompatibility checks
        topic_domains = [
            # HR/Recruitment vs Research/Technical
            (["hiring", "recruitment", "採用", "人材", "linkedin", "求人"], ["research", "researcher", "研究", "技術", "model", "モデル"]),
            # Economic policy vs Technical implementation  
            (["economy", "economic", "経済", "失業", "雇用喪失", "job losses"], ["hiring", "recruitment", "採用", "人材獲得", "massive offers"]),
            # Business/Finance vs Technical research
            (["investment", "funding", "ipo", "valuation", "投資"], ["api", "cli", "model", "algorithm", "研究"]),
            # Local tools vs Cloud services
            (["ollama", "local", "ローカル", "cli"], ["anthropic", "openai", "cloud", "クラウド"]),
        ]
        
        for domain1_keywords, domain2_keywords in topic_domains:
            has_domain1 = any(keyword in main_lower for keyword in domain1_keywords)
            has_domain2 = any(keyword in citation_lower for keyword in domain2_keywords)
            if has_domain1 and has_domain2:
                return True
                
            # Check reverse direction
            has_domain1_cite = any(keyword in citation_lower for keyword in domain1_keywords)
            has_domain2_main = any(keyword in main_lower for keyword in domain2_keywords)
            if has_domain1_cite and has_domain2_main:
                return True
        
        # Specific problematic combinations
        incompatible_patterns = [
            ("meta", "linkedin"),  # Meta research vs LinkedIn hiring
            ("anthropic", "meta"),
            ("economic futures", "massive offers"),
            ("雇用喪失", "massive offers"),
            ("経済影響", "cto confirms"),
            ("経済プログラム", "top ai executives"),
        ]
        
        for pattern1, pattern2 in incompatible_patterns:
            if (pattern1 in main_lower and pattern2 in citation_lower) or \
               (pattern2 in main_lower and pattern1 in citation_lower):
                return True
        
        return False
    
    # Test cases for incompatible patterns
    incompatible_test_cases = [
        {
            "name": "Meta vs LinkedIn",
            "main": "MetaがOpenAIからトップAI研究者3名を獲得",
            "citation": "LinkedIn hiring assistant、LinkedInの科学者たちは、人材の…",
            "expected": True
        },
        {
            "name": "Economic vs Hiring",
            "main": "Anthropic、AI経済フューチャープログラムで雇用喪失への懸念",
            "citation": "Meta CTO confirms massive offers to top AI executives",
            "expected": True
        },
        {
            "name": "Same company (should allow)",
            "main": "OpenAI releases new GPT-4 Turbo",
            "citation": "OpenAI expands API access to research models",
            "expected": False
        }
    ]
    
    for i, test_case in enumerate(incompatible_test_cases, 1):
        result = is_incompatible_citation(test_case["main"], test_case["citation"])
        expected = test_case["expected"]
        
        print(f"Test {i}: {test_case['name']}")
        print(f"  Main: {test_case['main'][:50]}...")
        print(f"  Citation: {test_case['citation'][:50]}...")
        print(f"  Incompatible: {result}, Expected: {expected}")
        print(f"  {'✅ PASS' if result == expected else '❌ FAIL'}")
        print()

def main():
    """Run all tests."""
    test_domain_validation()
    test_incompatible_patterns()
    
    print("=" * 60)
    print("SUMMARY OF FIXES:")
    print("- Raised clustering similarity threshold to 0.85")
    print("- Added domain-based topic validation")
    print("- Enhanced citation incompatibility checks")
    print("- Added specific blocks for Meta vs LinkedIn citations")
    print("- These fixes should prevent unrelated article clustering and citations")
    print("=" * 60)

if __name__ == "__main__":
    main()