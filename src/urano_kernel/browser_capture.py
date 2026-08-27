"""User-mediated browser capture for the URANO local bridge.

The browser remains the authentication boundary. This module never receives,
stores, or requests cookies, passwords, bearer tokens, refresh tokens, or
browser profile data. It accepts only page content that the user explicitly
captures from the active Chrome tab.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
from hashlib import sha256
from threading import Lock
from time import time
from typing import Any
from uuid import uuid4

MAX_TEXT_CHARS = 200_000
MAX_CAPTURES = 20


@dataclass(frozen=True)
class BrowserCapture:
    capture_id: str
    captured_at: float
    url: str
    title: str
    doi: str | None
    selected_text: str
    text: str
    content_sha256: str
    metadata: dict[str, Any]
    source: str = "chrome_active_tab"
    auth_boundary: str = "browser_session_not_exported"

    def summary(self) -> dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "captured_at": self.captured_at,
            "url": self.url,
            "title": self.title,
            "doi": self.doi,
            "content_sha256": self.content_sha256,
            "text_chars": len(self.text),
            "selected_text_chars": len(self.selected_text),
            "source": self.source,
            "auth_boundary": self.auth_boundary,
        }


class BrowserCaptureStore:
    def __init__(self, max_captures: int = MAX_CAPTURES):
        self._captures: deque[BrowserCapture] = deque(maxlen=max_captures)
        self._lock = Lock()

    def add(self, payload: dict[str, Any]) -> BrowserCapture:
        url = _required_string(payload, "url", 4096)
        title = _optional_string(payload.get("title"), 2048)
        doi = _optional_string(payload.get("doi"), 512) or None
        selected_text = _optional_string(payload.get("selected_text"), MAX_TEXT_CHARS)
        text = _optional_string(payload.get("text"), MAX_TEXT_CHARS)
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

        digest_input = "\n".join((url, title, doi or "", selected_text, text)).encode("utf-8")
        capture = BrowserCapture(
            capture_id="bc_" + uuid4().hex,
            captured_at=time(),
            url=url,
            title=title,
            doi=doi,
            selected_text=selected_text,
            text=text,
            content_sha256=sha256(digest_input).hexdigest(),
            metadata=_sanitize_metadata(metadata),
        )
        with self._lock:
            self._captures.append(capture)
        return capture

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [item.summary() for item in reversed(self._captures)]

    def get(self, capture_id: str) -> dict[str, Any] | None:
        with self._lock:
            for item in self._captures:
                if item.capture_id == capture_id:
                    return asdict(item)
        return None


def _required_string(payload: dict[str, Any], key: str, limit: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} (string) required")
    return value.strip()[:limit]


def _optional_string(value: Any, limit: int) -> str:
    return value.strip()[:limit] if isinstance(value, str) else ""


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "authors",
        "journal",
        "publisher",
        "publication_date",
        "language",
        "description",
        "canonical_url",
        "content_type",
    }
    clean: dict[str, Any] = {}
    for key in allowed:
        value = metadata.get(key)
        if isinstance(value, str):
            clean[key] = value[:4096]
        elif key == "authors" and isinstance(value, list):
            clean[key] = [str(v)[:512] for v in value[:100]]
    return clean
