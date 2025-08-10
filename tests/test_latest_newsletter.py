#!/usr/bin/env python3
"""Test the latest newsletter for PRD compliance."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Some test runners import without package context; support both cases
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
    newsletters = [
        "drafts/2025-06-29_0658_daily_newsletter.md",  # Pre-fix (06:58)
        "drafts/2025-06-29_1505_daily_newsletter.md",  # During fix (15:05)
        "drafts/2025-06-29_1541_daily_newsletter.md"   # Post-fix (15:41)
    ]

    print("🔍 COMPREHENSIVE PRD COMPLIANCE ANALYSIS")
    print("=" * 70)

    results = {}
    for newsletter in newsletters:
        if Path(newsletter).exists():
            success, rate = test_newsletter(newsletter)
            results[newsletter] = {"success": success, "rate": rate}
            print("\n" + "=" * 70)
        else:
            print(f"❌ File not found: {newsletter}")

    print("\n🏁 FINAL ANALYSIS:")
    print("=" * 70)

    for newsletter, result in results.items():
        timestamp = newsletter.split('/')[-1].split('_')[1]
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{timestamp}: {status} ({result['rate']:.1%})")

    # Analyze trend
    if len(results) >= 2:
        rates = [r["rate"] for r in results.values()]
        if rates[-1] > rates[0]:
            print(f"\n📈 IMPROVEMENT DETECTED: {rates[0]:.1%} → {rates[-1]:.1%}")
        else:
            print(f"\n📉 REGRESSION DETECTED: {rates[0]:.1%} → {rates[-1]:.1%}")
