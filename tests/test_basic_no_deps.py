#!/usr/bin/env python3
"""
Basic test without external dependencies.

This script tests the core functionality without requiring any pip packages.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_schemas():
    """Test Pydantic schemas."""
    print("Testing schemas...")

    try:
        from src.models.schemas import NewsletterConfig, RawArticle, SourceConfig

        # Test source config
        source = SourceConfig(
            id="test_source",
            name="Test Source",
            url="https://example.com/rss",
            source_type="rss",
            enabled=True
        )

        # Test article
        article = RawArticle(
            id="test_article",
            title="Test AI Article",
            url="https://example.com/article",
            published_date=datetime.now(),
            content="This is a test article about artificial intelligence and machine learning.",
            source_id="test_source",
            source_type="rss"
        )

        # Test config
        config = NewsletterConfig(
            max_items=5,
            edition="daily",
            sources=[source],
            processing_id="test_run"
        )

        print("✅ Schema validation successful")
        print(f"   Source: {source.name}")
        print(f"   Article: {article.title}")
        print(f"   Config: {config.edition} edition with {len(config.sources)} sources")
        return True
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

def test_sources_config():
    """Test sources configuration."""
    print("\nTesting sources config...")

    try:
        with open("sources.json") as f:
            sources_data = json.load(f)

        assert "sources" in sources_data, "Sources key missing"
        assert len(sources_data["sources"]) > 0, "No sources configured"

        enabled_sources = [s for s in sources_data["sources"] if s.get("enabled", False)]
        assert len(enabled_sources) > 0, "No enabled sources"

        rss_sources = [s for s in enabled_sources if s.get("source_type") == "rss"]
        youtube_sources = [s for s in enabled_sources if s.get("source_type") == "youtube"]

        print("✅ Sources config valid")
        print(f"   Total sources: {len(sources_data['sources'])}")
        print(f"   Enabled sources: {len(enabled_sources)}")
        print(f"   RSS sources: {len(rss_sources)}")
        print(f"   YouTube sources: {len(youtube_sources)}")
        return True
    except Exception as e:
        print(f"❌ Sources config test failed: {e}")
        return False

def test_file_structure():
    """Test project file structure."""
    print("\nTesting file structure...")

    required_files = [
        "main.py",
        "requirements.txt",
        "sources.json",
        "src/models/schemas.py",
        "src/utils/content_fetcher.py",
        "src/utils/ai_filter.py",
        "src/llm/llm_router.py",
        "src/deduplication/duplicate_checker.py",
        "src/utils/newsletter_generator.py",
        "src/workflow/newsletter_workflow.py",
        "src/templates/daily_newsletter.jinja2"
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        print(f"   Checked {len(required_files)} files")
        return True

def test_template():
    """Test newsletter template."""
    print("\nTesting newsletter template...")

    try:
        template_path = Path("src/templates/daily_newsletter.jinja2")
        if not template_path.exists():
            print("❌ Template file missing")
            return False

        with open(template_path, encoding="utf-8") as f:
            template_content = f.read()

        # Check for key template variables
        required_vars = ["{{ date", "articles", "{{ lead_text", "{% for"]
        missing_vars = []

        for var in required_vars:
            if var not in template_content:
                missing_vars.append(var)

        if missing_vars:
            print(f"❌ Template missing variables: {missing_vars}")
            return False

        print("✅ Newsletter template valid")
        print(f"   Template size: {len(template_content)} characters")
        return True
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False

def test_command_line_interface():
    """Test that main.py has proper CLI interface."""
    print("\nTesting CLI interface...")

    try:
        with open("main.py") as f:
            main_content = f.read()

        # Check for CLI components (argparse or click)
        cli_components = ["def main", "if __name__"]
        argparse_components = ["argparse.ArgumentParser", "parser.add_argument"]
        click_components = ["@click.command", "@click.option"]

        missing_components = []
        for component in cli_components:
            if component not in main_content:
                missing_components.append(component)

        # Check if either argparse or click is used
        has_argparse = any(comp in main_content for comp in argparse_components)
        has_click = any(comp in main_content for comp in click_components)

        if missing_components:
            print(f"❌ CLI missing components: {missing_components}")
            return False

        if not (has_argparse or has_click):
            print("❌ CLI missing argument parsing (argparse or click)")
            return False

        print("✅ CLI interface present")
        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Phase 1 Basic Tests (No External Dependencies)\n")

    tests = [
        test_schemas,
        test_sources_config,
        test_file_structure,
        test_template,
        test_command_line_interface
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All basic tests passed! Phase 1 structure is ready.")
        print("\n📋 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set up API keys in .env file")
        print("3. Run: python3 main.py --dry-run --max-items 5")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
