"""Stable text hashing for embedding cache keys."""

from __future__ import annotations

import hashlib


def normalize_text(text: str) -> str:
    """Normalize whitespace for stable hashing across exports."""
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip()


def text_hash(text: str) -> str:
    """SHA-256 hex digest of UTF-8 normalized text."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()
