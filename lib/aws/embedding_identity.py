"""Stable versioned hashing for embedding cache keys."""

from __future__ import annotations

import hashlib
import json


def embedding_identity_sha256(
    text: str,
    *,
    model_id: str,
    dimensions: int,
    normalize: bool,
) -> str:
    """SHA-256 hex (64 chars) over a composite identity blob.

    Text is canonicalized with :meth:`str.strip` only (no NFC/NFKC).

    Payload is prefixed with ``b\"v1\\n\"`` so future hashing schemes can coexist.
    """
    canonical = text.strip()
    payload = {
        "dimensions": dimensions,
        "model_id": model_id,
        "normalize": normalize,
        "text": canonical,
    }
    blob = b"v1\n" + json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
