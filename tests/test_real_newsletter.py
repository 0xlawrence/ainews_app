#!/usr/bin/env python3
"""Test a real newsletter file for PRD compliance."""

import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from tests.test_prd_compliance import PRDComplianceChecker
except Exception:  # pragma: no cover - robust fallback
    import os
    import sys
    from pathlib import Path
    TESTS_DIR = Path(__file__).parent
    PROJECT_ROOT = TESTS_DIR.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from tests.test_prd_compliance import PRDComplianceChecker


def test_newsletter(newsletter_path):
    """Test a specific newsletter file."""
    print(f"🧪 Testing: {newsletter_path}")
    print("=" * 60)

    checker = PRDComplianceChecker()
    results = checker.run_newsletter_compliance_tests(newsletter_path)

    # Generate summary
    total_tests = len(results)
    passed_tests = sum(1 for passed in results.values() if passed)
    success_rate = passed_tests / total_tests if total_tests > 0 else 0

    print(f"\n📊 SUMMARY for {newsletter_path}:")
    print(f"   Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1%})")

    return all(results.values()), success_rate

if __name__ == "__main__":
    # Test the actual generated newsletter (not mock)
    newsletter_path = "drafts/2025-06-29_1505_daily_newsletter.md"  # Real newsletter
    success, rate = test_newsletter(newsletter_path)

    if success:
        print("🎉 Newsletter meets all PRD requirements!")
    else:
        print(f"⚠️  Newsletter compliance: {rate:.1%}")

    sys.exit(0 if success else 1)
