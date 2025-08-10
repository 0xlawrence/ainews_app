import os
import sys
from pathlib import Path
import tempfile

import pytest

# Ensure project root is on sys.path so that `import src` works in tests
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def newsletter_path(tmp_path: Path) -> str:
    """Provide a dummy newsletter markdown path for tests expecting this fixture.
    Creates a minimal valid markdown file to satisfy PRD checker structure.
    """
    content = (
        "# AI NEWS TLDR\n\n"
        "### 見出し\n\n"
        "- 要点その1。\n"
        "- 要点その2。\n"
        "- 要点その3。\n\n"
    )
    path = tmp_path / "dummy_newsletter.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_image_path(tmp_path: Path) -> Path:
    """Create a small temporary image-like file for upload tests.
    Uses simple bytes; tests patch uploader internals and don't decode content.
    """
    p = tmp_path / "sample.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n\x00dummy")
    return p


@pytest.fixture
def mock_settings():
    """Provide a simple mock settings object shared across tests.
    Ensures availability for tests that patch get_settings and expect this fixture.
    """
    from types import SimpleNamespace

    db = SimpleNamespace(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        supabase_image_bucket="test-bucket",
    )
    settings = SimpleNamespace(database=db)
    return settings

