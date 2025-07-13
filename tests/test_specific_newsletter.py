#!/usr/bin/env python3
"""
Test specific newsletter for PRD compliance.
"""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_prd_compliance import PRDComplianceChecker


def test_newsletter(newsletter_path):
    """Test a specific newsletter file."""
    print(f"🧪 Testing PRD Compliance for: {newsletter_path}")
    print("=" * 60)

    checker = PRDComplianceChecker()
    results = checker.run_newsletter_compliance_tests(newsletter_path)

    # Generate report
    report = checker.generate_compliance_report()
    print(report)

    return all(results.values())

if __name__ == "__main__":
    # Test the actual generated newsletter
    newsletter_path = "drafts/2025-06-29_0658_daily_newsletter.md"
    success = test_newsletter(newsletter_path)

    if success:
        print("🎉 Newsletter meets all PRD requirements!")
    else:
        print("⚠️  Newsletter needs improvements to meet PRD requirements")

    sys.exit(0 if success else 1)
