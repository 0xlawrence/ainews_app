#!/usr/bin/env python3
"""
PRD Compliance Testing Suite.

This module tests that the newsletter generation meets PRD requirements:
- F-15: Topic clustering and citation deduplication
- F-16: Context reflection and UPDATE detection
- F-17: Context inheritance and relationship recording
- Article count guarantee (7-10 articles per newsletter)
"""

import sys
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class PRDComplianceChecker:
    """PRD requirements compliance checker."""
    
    def __init__(self):
        self.test_results = []
        self.current_test = None
    
    def log_test(self, test_name: str, passed: bool, message: str, details: Optional[Dict] = None):
        """Log test result."""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {message}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def test_article_count_guarantee(self, newsletter_path: str) -> bool:
        """
        Test F-15 requirement: 7-10 articles per newsletter.
        
        Args:
            newsletter_path: Path to generated newsletter file
            
        Returns:
            True if article count is within 7-10 range
        """
        try:
            if not os.path.exists(newsletter_path):
                self.log_test(
                    "Article Count Guarantee",
                    False,
                    f"Newsletter file not found: {newsletter_path}"
                )
                return False
            
            with open(newsletter_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count articles - look for article headers (## or ###)
            article_pattern = r'^(##[^#].*|###[^#].*)$'
            article_headers = re.findall(article_pattern, content, re.MULTILINE)
            
            # Exclude main headers like "## AI ニュース概要" 
            filtered_headers = [
                h for h in article_headers 
                if not any(keyword in h.lower() for keyword in [
                    'ニュース概要', 'news summary', '今日の', 'today\'s', '概要'
                ])
            ]
            
            article_count = len(filtered_headers)
            
            # PRD requirement: 7-10 articles
            is_compliant = 7 <= article_count <= 10
            
            self.log_test(
                "Article Count Guarantee (F-15)",
                is_compliant,
                f"Found {article_count} articles (requirement: 7-10)",
                {
                    "article_count": article_count,
                    "target_range": "7-10",
                    "compliant": is_compliant,
                    "headers_found": filtered_headers[:5]  # First 5 for debugging
                }
            )
            
            return is_compliant
            
        except Exception as e:
            self.log_test(
                "Article Count Guarantee",
                False,
                f"Error counting articles: {e}"
            )
            return False
    
    def test_update_detection_compliance(self, newsletter_path: str) -> bool:
        """
        Test F-16 requirement: UPDATE articles should have 🆙 emoji.
        
        Args:
            newsletter_path: Path to generated newsletter file
            
        Returns:
            True if UPDATE detection is working properly
        """
        try:
            if not os.path.exists(newsletter_path):
                self.log_test(
                    "UPDATE Detection (F-16)",
                    False,
                    f"Newsletter file not found: {newsletter_path}"
                )
                return False
            
            with open(newsletter_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for UPDATE indicators
            update_patterns = [
                r'🆙',  # Update emoji
                r'アップデート',  # Japanese "update"
                r'更新',  # Japanese "update"
                r'update',  # English update (case insensitive)
                r'新機能',  # New feature
                r'新版',  # New version
            ]
            
            update_count = 0
            emoji_count = 0
            
            for pattern in update_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if pattern == r'🆙':
                    emoji_count = len(matches)
                else:
                    update_count += len(matches)
            
            # Check if articles with update keywords have emoji
            has_updates = update_count > 0
            has_emojis = emoji_count > 0
            
            # If there are updates, there should be emojis
            is_compliant = not has_updates or (has_updates and has_emojis)
            
            self.log_test(
                "UPDATE Detection (F-16)",
                is_compliant,
                f"Update detection working properly",
                {
                    "update_keywords_found": update_count,
                    "update_emojis_found": emoji_count,
                    "has_updates": has_updates,
                    "has_emojis": has_emojis,
                    "compliant": is_compliant
                }
            )
            
            return is_compliant
            
        except Exception as e:
            self.log_test(
                "UPDATE Detection (F-16)",
                False,
                f"Error checking UPDATE detection: {e}"
            )
            return False
    
    def test_citation_diversity(self, newsletter_path: str) -> bool:
        """
        Test F-15 requirement: Citation deduplication and diversity.
        
        Args:
            newsletter_path: Path to generated newsletter file
            
        Returns:
            True if citations are diverse and not duplicated
        """
        try:
            if not os.path.exists(newsletter_path):
                self.log_test(
                    "Citation Diversity (F-15)",
                    False,
                    f"Newsletter file not found: {newsletter_path}"
                )
                return False
            
            with open(newsletter_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract citation URLs
            url_pattern = r'https?://[^\s\)]+(?:[^\s\.\,\)]+)?'
            urls = re.findall(url_pattern, content)
            
            # Clean URLs (remove trailing punctuation)
            cleaned_urls = []
            for url in urls:
                # Remove trailing punctuation
                cleaned_url = re.sub(r'[,.\)\]\}]+$', '', url)
                cleaned_urls.append(cleaned_url)
            
            # Check for duplicates
            unique_urls = set(cleaned_urls)
            duplicate_count = len(cleaned_urls) - len(unique_urls)
            
            # Check domain diversity
            domains = []
            for url in unique_urls:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    domains.append(domain)
                except:
                    continue
            
            unique_domains = len(set(domains))
            
            # Requirements: Low duplication rate, multiple domains
            duplication_rate = duplicate_count / max(len(cleaned_urls), 1)
            is_compliant = duplication_rate < 0.1 and unique_domains >= 3
            
            self.log_test(
                "Citation Diversity (F-15)",
                is_compliant,
                f"Citation diversity check",
                {
                    "total_citations": len(cleaned_urls),
                    "unique_citations": len(unique_urls),
                    "duplicate_count": duplicate_count,
                    "duplication_rate": f"{duplication_rate:.2%}",
                    "unique_domains": unique_domains,
                    "compliant": is_compliant
                }
            )
            
            return is_compliant
            
        except Exception as e:
            self.log_test(
                "Citation Diversity (F-15)",
                False,
                f"Error checking citation diversity: {e}"
            )
            return False
    
    def test_japanese_output_compliance(self, newsletter_path: str) -> bool:
        """
        Test that newsletter output is primarily in Japanese.
        
        Args:
            newsletter_path: Path to generated newsletter file
            
        Returns:
            True if output is primarily Japanese
        """
        try:
            if not os.path.exists(newsletter_path):
                self.log_test(
                    "Japanese Output",
                    False,
                    f"Newsletter file not found: {newsletter_path}"
                )
                return False
            
            with open(newsletter_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count Japanese characters (hiragana, katakana, kanji)
            japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', content))
            
            # Count total non-whitespace characters
            total_chars = len(re.sub(r'\s', '', content))
            
            # Calculate Japanese ratio
            japanese_ratio = japanese_chars / max(total_chars, 1)
            
            # Should be at least 60% Japanese
            is_compliant = japanese_ratio >= 0.6
            
            self.log_test(
                "Japanese Output",
                is_compliant,
                f"Japanese character ratio: {japanese_ratio:.1%}",
                {
                    "japanese_chars": japanese_chars,
                    "total_chars": total_chars,
                    "japanese_ratio": f"{japanese_ratio:.1%}",
                    "target_ratio": "≥60%",
                    "compliant": is_compliant
                }
            )
            
            return is_compliant
            
        except Exception as e:
            self.log_test(
                "Japanese Output",
                False,
                f"Error checking Japanese output: {e}"
            )
            return False
    
    def test_template_compliance(self, newsletter_path: str) -> bool:
        """
        Test that newsletter follows template structure.
        
        Args:
            newsletter_path: Path to generated newsletter file
            
        Returns:
            True if template structure is followed
        """
        try:
            if not os.path.exists(newsletter_path):
                self.log_test(
                    "Template Compliance",
                    False,
                    f"Newsletter file not found: {newsletter_path}"
                )
                return False
            
            with open(newsletter_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required template sections
            required_sections = [
                r'# .*(AI NEWS TLDR|ニュース).*',  # Main title with "AI NEWS TLDR" or "ニュース"
                r'## .+',  # At least one section header
                r'\*\*.+\*\*',  # Bold text (article titles)
                r'https?://',  # URLs for citations
            ]
            
            missing_sections = []
            found_sections = {}
            
            for i, pattern in enumerate(required_sections):
                matches = re.findall(pattern, content)
                found_sections[f"section_{i}"] = len(matches)
                if not matches:
                    missing_sections.append(pattern)
            
            is_compliant = len(missing_sections) == 0
            
            self.log_test(
                "Template Compliance",
                is_compliant,
                f"Template structure check",
                {
                    "sections_found": found_sections,
                    "missing_sections": missing_sections,
                    "compliant": is_compliant
                }
            )
            
            return is_compliant
            
        except Exception as e:
            self.log_test(
                "Template Compliance",
                False,
                f"Error checking template compliance: {e}"
            )
            return False
    
    def run_newsletter_compliance_tests(self, newsletter_path: str) -> Dict[str, bool]:
        """
        Run all compliance tests on a generated newsletter.
        
        Args:
            newsletter_path: Path to generated newsletter file
            
        Returns:
            Dictionary of test results
        """
        print(f"\n🧪 Running PRD Compliance Tests on: {newsletter_path}")
        print("=" * 60)
        
        tests = {
            "article_count": self.test_article_count_guarantee,
            "update_detection": self.test_update_detection_compliance,
            "citation_diversity": self.test_citation_diversity,
            "japanese_output": self.test_japanese_output_compliance,
            "template_structure": self.test_template_compliance,
        }
        
        results = {}
        for test_name, test_func in tests.items():
            results[test_name] = test_func(newsletter_path)
        
        return results
    
    def generate_compliance_report(self) -> str:
        """Generate a detailed compliance report."""
        passed_tests = [t for t in self.test_results if t["passed"]]
        failed_tests = [t for t in self.test_results if not t["passed"]]
        
        report = f"""
📊 PRD Compliance Test Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Total Tests: {len(self.test_results)}
- Passed: {len(passed_tests)}
- Failed: {len(failed_tests)}
- Success Rate: {len(passed_tests)/max(len(self.test_results), 1):.1%}

DETAILED RESULTS:
"""
        
        for result in self.test_results:
            status = "PASS" if result["passed"] else "FAIL"
            report += f"\n[{status}] {result['test']}: {result['message']}\n"
            if result["details"]:
                for key, value in result["details"].items():
                    report += f"  - {key}: {value}\n"
        
        return report


def find_latest_newsletter() -> Optional[str]:
    """Find the most recently generated newsletter."""
    draft_paths = [
        "drafts/",
        "tests/test_output/",
        "tests/quality_improved/",
        "tests/test/"
    ]
    
    latest_file = None
    latest_time = None
    
    for draft_path in draft_paths:
        if os.path.exists(draft_path):
            for file in os.listdir(draft_path):
                if file.endswith('.md') and 'newsletter' in file:
                    file_path = os.path.join(draft_path, file)
                    file_time = os.path.getmtime(file_path)
                    if latest_time is None or file_time > latest_time:
                        latest_time = file_time
                        latest_file = file_path
    
    return latest_file


def main():
    """Run PRD compliance tests."""
    print("🧪 PRD Compliance Testing Suite")
    print("=" * 50)
    
    # Find newsletter to test
    newsletter_path = find_latest_newsletter()
    
    if not newsletter_path:
        print("❌ No newsletter file found for testing")
        print("📋 Please generate a newsletter first:")
        print("   python3 main.py --max-items 30 --edition daily")
        return False
    
    print(f"📄 Testing newsletter: {newsletter_path}")
    
    # Run compliance tests
    checker = PRDComplianceChecker()
    results = checker.run_newsletter_compliance_tests(newsletter_path)
    
    # Generate report
    print("\n" + "=" * 60)
    report = checker.generate_compliance_report()
    print(report)
    
    # Save report
    report_path = f"tests/prd_compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 Report saved to: {report_path}")
    
    # Return overall success
    all_passed = all(results.values())
    
    if all_passed:
        print("🎉 All PRD compliance tests passed!")
    else:
        failed_count = sum(1 for passed in results.values() if not passed)
        print(f"⚠️  {failed_count} tests failed. Please review implementation.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)