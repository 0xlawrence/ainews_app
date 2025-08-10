"""
Quaily Platform Client Utilities

This module provides helper functions to publish generated newsletters to the
Quaily email/newsletter delivery platform. The implementation supports two
transport mechanisms:

1. Quaily CLI (preferred)
   If the `quaily` executable is available on the system, we invoke it via
   subprocess so that we do not have to re-implement authentication logic.
   The CLI should accept an input Markdown file and return JSON describing
   the created draft.

2. Direct HTTP API (fallback)
   When the CLI is not present but the environment variables `QUAILY_API_KEY`
   (and optionally `QUAILY_API_URL`) are defined, we send the newsletter
   content directly to Quaily's REST endpoint.

Both transports honour the `dry_run` argument – when enabled the function logs
what it *would* do and immediately returns without performing network or CLI
operations.  This behaviour is important for unit tests and local debugging
where credentials may not be available.

Slack notifications
-------------------
After a successful or failed publish attempt we optionally send a Slack
message when the `SLACK_WEBHOOK_URL` environment variable is present.

The JSON returned by `publish_newsletter` always contains a top-level `status`
key so that callers can branch on the outcome.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Union

import requests

from src.utils.text_processing import (
    normalize_unicode_content,
    safe_encode_for_api,
    validate_text_for_api,
    extract_safe_text_for_api
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _normalize_unicode_content(content: str) -> str:
    """Normalize Unicode content to prevent surrogate pair issues."""
    return normalize_unicode_content(content)


def publish_newsletter(file_path: str, *, edition: str = "daily", dry_run: bool = False) -> dict:
    """
    Publish newsletter to Quaily platform.

    Args:
        file_path: Path to the markdown file
        edition: Newsletter edition (daily, weekly, etc.)
        dry_run: If True, don't actually publish

    Returns:
        Dict with status and response details
    """
    if dry_run:
        logger.info("[Quaily] Dry run mode - skipping publish")
        return {"status": "skipped", "reason": "dry_run"}

    path = Path(file_path)
    if not path.exists():
        logger.error(f"[Quaily] File not found: {path}")
        return {"status": "failed", "reason": "file_not_found"}

    # ------------------------------------------------------------------
    # Primary: CLI-based publish
    # ------------------------------------------------------------------
    cli_executable = os.getenv("QUAILY_CLI_PATH")

    if cli_executable:
        logger.info("[Quaily] Using CLI for publish", extra={"path": str(path)})
        try:
            start = time.time()
            completed = subprocess.run(
                [cli_executable, "publish", str(path), "--edition", edition, "--json"],
                check=True,
                capture_output=True,
                text=True,
            )
            duration = time.time() - start
            logger.info("[Quaily] CLI publish succeeded", extra={"duration_sec": duration})

            resp_payload: Union[dict, str]
            try:
                resp_payload = json.loads(completed.stdout)
            except json.JSONDecodeError:
                resp_payload = completed.stdout.strip()

            _notify_slack(
                f"✅ Newsletter *{path.name}* published to Quaily via CLI ({edition})."
            )
            return {
                "status": "success",
                "method": "cli",
                "duration_sec": duration,
                "response": resp_payload,
            }
        except subprocess.CalledProcessError as exc:
            logger.error(
                "[Quaily] CLI publish failed", extra={"stderr": exc.stderr, "returncode": exc.returncode}
            )
            # fallthrough to HTTP API attempt below

    # ------------------------------------------------------------------
    # Fallback: direct HTTP POST using API key
    # ------------------------------------------------------------------
    api_key = os.getenv("QUAILY_API_KEY")
    api_url = os.getenv("QUAILY_API_URL", "https://api.quaily.io/v1/newsletters")

    if api_key:
        logger.info("[Quaily] Using HTTP API for publish", extra={"endpoint": api_url})
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "text/markdown; charset=utf-8",
            "User-Agent": "ainews-app/1.0",
        }
        
        # Read and process content
        with path.open("r", encoding="utf-8") as fp:
            markdown_content = fp.read()
        
        # Validate content before processing
        is_valid, error_msg = validate_text_for_api(markdown_content)
        if not is_valid:
            logger.warning(f"[Quaily] Content validation failed: {error_msg}")
            # Try to extract safe content
            markdown_content = extract_safe_text_for_api(markdown_content)
        
        # Normalize Unicode content to prevent surrogate pair issues
        normalized_content = _normalize_unicode_content(markdown_content)

        payload: dict[str, Union[str, None]] = {
            "edition": edition,
            "filename": path.name,
        }

        start = time.time()
        try:
            # Use safe encoding function
            encoded_content = safe_encode_for_api(normalized_content)
            resp = requests.post(api_url, params=payload, data=encoded_content, headers=headers, timeout=30)
            duration = time.time() - start

            if resp.ok:
                logger.info("[Quaily] API publish succeeded", extra={"duration_sec": duration})
                _notify_slack(f"✅ Newsletter *{path.name}* published to Quaily via API ({edition}).")
                try:
                    body = resp.json()
                except ValueError:
                    body = resp.text
                return {
                    "status": "success",
                    "method": "api",
                    "duration_sec": duration,
                    "response": body,
                }
            else:
                logger.error(
                    "[Quaily] API publish failed", extra={"status_code": resp.status_code, "text": resp.text}
                )
                _notify_slack(
                    f"🚨 Newsletter *{path.name}* failed to publish – API responded with {resp.status_code}."
                )
                return {
                    "status": "failed",
                    "method": "api",
                    "status_code": resp.status_code,
                    "text": resp.text,
                }
        except UnicodeEncodeError as e:
            logger.error(f"[Quaily] Unicode encoding error: {e}")
            return {
                "status": "failed",
                "method": "api",
                "error": "unicode_encoding_error",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"[Quaily] API request error: {e}")
            return {
                "status": "failed",
                "method": "api",
                "error": "request_error",
                "details": str(e)
            }

    # ------------------------------------------------------------------
    # Neither CLI nor API credentials available – we skip the publish step.
    # ------------------------------------------------------------------
    logger.warning("[Quaily] Skipping publish – CLI and API credentials are unavailable.")
    _notify_slack(
        f"⚠️ Newsletter *{path.name}* generated but not published – missing Quaily credentials."
    )
    return {"status": "skipped", "reason": "no_credentials"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _notify_slack(message: str) -> None:
    """Post a simple text message to Slack when webhook is configured."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return  # silently ignore – Slack is optional

    try:
        # Normalize message for safe JSON encoding
        safe_message = normalize_unicode_content(message)
        
        # Create payload with safe message
        payload = {"text": safe_message}
        
        # Use safe JSON encoding
        try:
            json_payload = json.dumps(payload, ensure_ascii=False)
        except UnicodeEncodeError:
            # If Unicode encoding fails, try with error handling
            json_payload = json.dumps(payload, ensure_ascii=False, default=str)
        
        response = requests.post(webhook_url, data=json_payload, headers={"Content-Type": "application/json"}, timeout=10)
        if not response.ok:
            logger.warning(
                "[Quaily] Slack notification failed", extra={"status_code": response.status_code, "text": response.text}
            )
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("[Quaily] Slack notification error", exc_info=exc)
