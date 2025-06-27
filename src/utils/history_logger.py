"""history_logger.py
Maintain a local JSON-Lines history of Quaily publish attempts and provide
simple statistics for success-rate monitoring (Phase-4 requirement).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Final

from src.utils.logger import setup_logging

logger: Final = setup_logging()

_HISTORY_FILE: Path = Path("logs") / "publish_history.jsonl"


def record_publish(processing_id: str, result: Dict) -> None:
    """Append a single publish result to the history file."""

    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "processing_id": processing_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **result,
    }

    with _HISTORY_FILE.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.debug("Publish history entry added", processing_id=processing_id)


def compute_success_rate(window: int = 30) -> float:
    """Return publish success-rate over the last *window* entries."""

    if not _HISTORY_FILE.exists():
        return 0.0

    lines = _HISTORY_FILE.read_text(encoding="utf-8").strip().split("\n")
    if not lines:
        return 0.0

    recent = lines[-window:]

    successes = 0
    for line in recent:
        try:
            data = json.loads(line)
            if data.get("status") == "success":
                successes += 1
        except json.JSONDecodeError:
            continue

    return successes / len(recent) * 100.0 