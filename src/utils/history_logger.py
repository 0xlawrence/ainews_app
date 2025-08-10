"""history_logger.py
Maintain a local JSON-Lines history of Quaily publish attempts and provide
simple statistics for success-rate monitoring (Phase-4 requirement).
"""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Final

from src.utils.logger import setup_logging

logger: Final = setup_logging()

_HISTORY_FILE: Path = Path("logs") / "publish_history.jsonl"


def normalize_unicode_for_json(text: str) -> str:
    """Normalize Unicode text for safe JSON encoding."""
    if not text:
        return text
    
    try:
        # Normalize to NFC form
        normalized = unicodedata.normalize('NFC', text)
        
        # Remove surrogate pairs and invalid characters
        cleaned = ''
        i = 0
        while i < len(normalized):
            char = normalized[i]
            category = unicodedata.category(char)
            
            # Skip surrogate characters
            if category == 'Cs':
                i += 1
                continue
            
            # Replace control characters (except newlines and tabs)
            if category == 'Cc' and char not in '\n\t\r':
                cleaned += ' '
                i += 1
                continue
            
            cleaned += char
            i += 1
        
        return cleaned
    except Exception:
        # Fallback: return original text if normalization fails
        return text


def safe_json_dumps(obj, **kwargs):
    """Safely serialize object to JSON with Unicode handling."""
    try:
        return json.dumps(obj, ensure_ascii=False, **kwargs)
    except UnicodeEncodeError:
        # If Unicode encoding fails, try with error handling
        return json.dumps(obj, ensure_ascii=False, **kwargs)


def record_publish(processing_id: str, result: dict) -> None:
    """Append a single publish result to the history file."""

    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Normalize Unicode in result data
    normalized_result = {}
    for key, value in result.items():
        if isinstance(value, str):
            normalized_result[key] = normalize_unicode_for_json(value)
        elif isinstance(value, dict):
            # Recursively normalize dictionary values
            normalized_dict = {}
            for k, v in value.items():
                if isinstance(v, str):
                    normalized_dict[k] = normalize_unicode_for_json(v)
                else:
                    normalized_dict[k] = v
            normalized_result[key] = normalized_dict
        else:
            normalized_result[key] = value

    entry = {
        "processing_id": processing_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **normalized_result,
    }

    try:
        with _HISTORY_FILE.open("a", encoding="utf-8") as fp:
            fp.write(safe_json_dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write to history file: {e}")
        # Try with error handling
        try:
            with _HISTORY_FILE.open("a", encoding="utf-8", errors='replace') as fp:
                fp.write(safe_json_dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e2:
            logger.error(f"Failed to write to history file even with error handling: {e2}")

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
