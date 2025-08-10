r"""
URL/Citation 妥当性検証ユーティリティ。

用途:
- 一般的な http/https URL 形式の検証
- YouTube 動画 URL の簡易検証（watch?v=<video_id> / youtu.be/<id> など）
- 既知ダミー URL（video_example_\d+）の排除
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


def is_http_url(url: str) -> bool:
    """http/https のみ許可する簡易チェック。"""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def extract_youtube_video_id(url: str) -> str | None:
    """各種形式の YouTube URL から video_id を抽出。該当しない場合は None。"""
    if not url or not isinstance(url, str):
        return None

    patterns = [
        r"youtube\.com/watch\?v=([^&]+)",
        r"youtu\.be/([^?&/]+)",
        r"youtube\.com/embed/([^?&/]+)",
        r"youtube\.com/v/([^?&/]+)",
    ]

    for pat in patterns:
        m = re.search(pat, url, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def is_dummy_youtube_id(video_id: str) -> bool:
    r"""既知ダミーID（video_example_\d+）の検出。"""
    return bool(re.search(r"video_example_\d+", video_id or ""))


def is_valid_youtube_video_url(url: str) -> bool:
    """YouTube の動画URLとして妥当か簡易検証。"""
    if not is_http_url(url):
        return False

    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if not ("youtube.com" in host or "youtu.be" in host):
            return False

        video_id = extract_youtube_video_id(url)
        if not video_id:
            return False

        # 既知のダミーIDは拒否
        if is_dummy_youtube_id(video_id):
            return False

        # 一般的なIDパターン（長さ 6-20 の英数字/ _ - ）を許容
        return bool(YOUTUBE_ID_PATTERN.match(video_id))
    except Exception:
        return False


def validate_citation_url(url: str) -> bool:
    r"""引用で使用するURLの妥当性検証。

    - http/https 必須
    - YouTube の場合は video_id を厳格チェック
    - 既知ダミー `video_example_\d+` は拒否
    """
    if not is_http_url(url):
        return False

    # YouTube の場合のみ厳格検証。それ以外は http/https なら許容
    try:
        host = urlparse(url).netloc.lower()
        if "youtube.com" in host or "youtu.be" in host:
            return is_valid_youtube_video_url(url)
        return True
    except Exception:
        return False


__all__ = [
    "is_http_url",
    "extract_youtube_video_id",
    "is_dummy_youtube_id",
    "is_valid_youtube_video_url",
    "validate_citation_url",
]


