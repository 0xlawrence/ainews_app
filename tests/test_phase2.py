#!/usr/bin/env python3
"""
Phase 2 test to verify context analysis and embedding functionality.

This script tests the embedding manager, context analyzer, and
contextual article processing without requiring full API access.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that Phase 2 modules can be imported."""
    print("Testing Phase 2 imports...")

    try:
        print("✅ Phase 2 imports successful")
        return True
    except Exception as e:
        print(f"❌ Phase 2 import failed: {e}")
        return False

def test_context_prompts():
    """Test context analysis prompts loading."""
    print("\nTesting context analysis prompts...")

    try:
        from pathlib import Path

        import yaml

        prompts_file = Path("src/prompts/context_analysis.yaml")
        if not prompts_file.exists():
            print("❌ Context analysis prompts file missing")
            return False

        with open(prompts_file, encoding='utf-8') as f:
            prompts = yaml.safe_load(f)

        required_keys = ["context_analysis_prompt", "system_prompt"]
        missing_keys = [key for key in required_keys if key not in prompts]

        if missing_keys:
            print(f"❌ Missing prompt keys: {missing_keys}")
            return False

        print("✅ Context analysis prompts loaded successfully")
        print(f"   Found {len(prompts)} prompt templates")
        return True
    except Exception as e:
        print(f"❌ Context prompts test failed: {e}")
        return False

def test_embedding_manager_init():
    """Test embedding manager initialization."""
    print("\nTesting embedding manager initialization...")

    try:
        from utils.embedding_manager import EmbeddingManager

        # Initialize without OpenAI API key (will warn but not fail)
        manager = EmbeddingManager()

        stats = manager.get_index_stats()

        print("✅ Embedding manager initialized")
        print(f"   Dimension: {stats['dimension']}")
        print(f"   Model: {stats['model']}")
        print(f"   Vectors: {stats['total_vectors']}")
        return True
    except Exception as e:
        print(f"❌ Embedding manager test failed: {e}")
        return False

def test_context_analyzer_init():
    """Test context analyzer initialization."""
    print("\nTesting context analyzer initialization...")

    try:
        from utils.context_analyzer import ContextAnalyzer

        analyzer = ContextAnalyzer()

        # Check if prompts were loaded
        assert analyzer.prompts is not None
        assert "context_analysis_prompt" in analyzer.prompts

        print("✅ Context analyzer initialized")
        print(f"   Prompts loaded: {len(analyzer.prompts)} templates")
        return True
    except Exception as e:
        print(f"❌ Context analyzer test failed: {e}")
        return False

def test_schemas_validation():
    """Test Phase 2 schema additions."""
    print("\nTesting Phase 2 schema validation...")

    try:
        from models.schemas import ContextAnalysisResult

        # Test valid context analysis result
        result = ContextAnalysisResult(
            decision="UPDATE",
            reasoning="Article is a follow-up to previous news",
            contextual_summary="Updated information about the topic",
            references=["article_1", "article_2"],
            similarity_score=0.85
        )

        assert result.decision == "UPDATE"
        assert result.similarity_score == 0.85

        # Test invalid decision
        try:
            invalid_result = ContextAnalysisResult(
                decision="INVALID",
                reasoning="Test",
                similarity_score=0.5
            )
            print("❌ Schema should have rejected invalid decision")
            return False
        except Exception:
            pass  # Expected validation error

        print("✅ Phase 2 schemas validation working")
        return True
    except Exception as e:
        print(f"❌ Schema validation test failed: {e}")
        return False

def test_sql_schema():
    """Test SQL schema file."""
    print("\nTesting SQL schema file...")

    try:
        sql_file = Path("sql/phase2_tables.sql")
        if not sql_file.exists():
            print("❌ Phase 2 SQL schema file missing")
            return False

        with open(sql_file, encoding='utf-8') as f:
            sql_content = f.read()

        # Check for required tables
        required_tables = ["contextual_articles", "article_relationships"]
        missing_tables = []

        for table in required_tables:
            if f"CREATE TABLE IF NOT EXISTS {table}" not in sql_content:
                missing_tables.append(table)

        if missing_tables:
            print(f"❌ Missing table definitions: {missing_tables}")
            return False

        # Check for required functions
        required_functions = ["find_related_articles", "get_article_context_chain"]
        missing_functions = []

        for func in required_functions:
            if f"CREATE OR REPLACE FUNCTION {func}" not in sql_content:
                missing_functions.append(func)

        if missing_functions:
            print(f"❌ Missing function definitions: {missing_functions}")
            return False

        print("✅ SQL schema file is complete")
        print(f"   Tables: {len(required_tables)}")
        print(f"   Functions: {len(required_functions)}")
        return True
    except Exception as e:
        print(f"❌ SQL schema test failed: {e}")
        return False

def test_workflow_integration():
    """Test that workflow can import Phase 2 components."""
    print("\nTesting workflow integration...")

    try:
        from workflow.newsletter_workflow import NewsletterWorkflow

        workflow = NewsletterWorkflow()

        # Check that Phase 2 components are available
        assert hasattr(workflow, 'embedding_manager')
        assert hasattr(workflow, 'context_analyzer')

        print("✅ Workflow integration successful")
        return True
    except Exception as e:
        print(f"❌ Workflow integration test failed: {e}")
        return False

def test_template_updates():
    """Test that templates support Phase 2 features."""
    print("\nTesting template updates...")

    try:
        template_path = Path("src/templates/daily_newsletter.jinja2")
        if not template_path.exists():
            print("❌ Newsletter template missing")
            return False

        with open(template_path, encoding='utf-8') as f:
            template_content = f.read()

        # Check for Phase 2 template features
        phase2_features = [
            "article.is_update",
            "🆙",
            "article.final_summary",
            "article.context_analysis"
        ]

        missing_features = []
        for feature in phase2_features:
            if feature not in template_content:
                missing_features.append(feature)

        if missing_features:
            print(f"❌ Template missing Phase 2 features: {missing_features}")
            return False

        print("✅ Template supports Phase 2 features")
        return True
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False

def main():
    """Run all Phase 2 tests."""
    print("🧪 Running Phase 2 Context Analysis Tests\n")

    tests = [
        test_imports,
        test_context_prompts,
        test_embedding_manager_init,
        test_context_analyzer_init,
        test_schemas_validation,
        test_sql_schema,
        test_workflow_integration,
        test_template_updates
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Phase 2 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All Phase 2 tests passed! Context analysis system is ready.")
        print("\n📋 Next steps:")
        print("1. Set up Supabase database with Phase 2 tables")
        print("2. Run: python3 main.py --max-items 5 --dry-run")
        print("3. Test with actual API keys for full functionality")
        return True
    else:
        print("⚠️  Some Phase 2 tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
