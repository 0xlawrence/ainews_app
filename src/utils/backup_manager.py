"""backup_manager.py
Utility helpers for creating local backups of generated newsletter files.

The Phase-4 MVP simply copies the generated Markdown (and any accompanying
files) to `backups/YYYY-MM-DD/` so that we keep an immutable snapshot regardless
of further edits or failed publish attempts.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Final

from src.utils.logger import setup_logging

logger: Final = setup_logging()


def backup_file(file_path: str | Path) -> Path:
    """Copy *file_path* into the daily backup directory.

    Returns the destination path.  Any errors are propagated to the caller.
    """

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    backup_dir = Path("backups") / datetime.now().strftime("%Y-%m-%d")
    backup_dir.mkdir(parents=True, exist_ok=True)

    dest = backup_dir / path.name
    shutil.copy2(path, dest)
    logger.info("Backup created", source=str(path), destination=str(dest))
    return dest
