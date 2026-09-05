"""Map Bluesky warehouse dump rows onto the Bluesky ingest record shape.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.data_dumps.bluesky.transform import dump_post_to_sync_row"
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

import pandas as pd

from data_platform.ingestion.generate_record_id import (
    INTEGRATION_BLUESKY,
    attach_record_id,
)

REQUIRED_DUMP_KEYS = ("uri", "did", "created_at", "text")
ENGAGEMENT_COUNT = 0
BLUESKY_PROFILE_POST_URL = "https://bsky.app/profile/{did}/post/{rkey}"


def _require_dump_text(row: Mapping[str, object], key: str) -> str:
    if key not in row:
        raise KeyError(key)
    return str(row[key]).strip()


def _rkey_from_uri(uri: str) -> str:
    if "/" not in uri:
        raise ValueError("uri must include a slash")
    return uri.rsplit("/", 1)[-1]


def _created_at_isoformat(created_at: object) -> str:
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
        return created_at.isoformat()
    parsed = pd.to_datetime(created_at, utc=True)
    return parsed.isoformat()


def dump_post_to_sync_row(
    row: Mapping[str, object],
    sync_timestamp: str,
) -> dict[str, object]:
    """Return a Bluesky ingest row for one warehouse dump post.

    Parameters
    ----------
    row
        Dump columns ``uri``, ``did``, ``created_at``, and ``text``.
    sync_timestamp
        Raw run directory name written onto ``sync_timestamp``.

    Returns
    -------
    dict[str, object]
        A dict that validates as ``SyncBlueskyPostModel``.

    Raises
    ------
    KeyError
        When a required dump key is missing.
    ValueError
        When ``uri`` or ``did`` is blank, or ``uri`` has no ``/``.
    """
    for key in REQUIRED_DUMP_KEYS:
        if key not in row:
            raise KeyError(key)
    uri = _require_dump_text(row, "uri")
    did = _require_dump_text(row, "did")
    if not uri or not did:
        raise ValueError("uri and did must be non-empty")
    rkey = _rkey_from_uri(uri)
    mapped: dict[str, object] = {
        "uri": uri,
        "url": BLUESKY_PROFILE_POST_URL.format(did=did, rkey=rkey),
        "author_handle": did,
        "text": str(row["text"]),
        "created_at": _created_at_isoformat(row["created_at"]),
        "like_count": ENGAGEMENT_COUNT,
        "repost_count": ENGAGEMENT_COUNT,
        "reply_count": ENGAGEMENT_COUNT,
        "quote_count": ENGAGEMENT_COUNT,
        "sync_timestamp": sync_timestamp,
    }
    return attach_record_id(mapped, INTEGRATION_BLUESKY)
