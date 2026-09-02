from __future__ import annotations

from typing import Any

from data_platform.models.sync import SyncTwitterPostModel
from lib.timestamp_utils import format_iso_created_at, format_run_timestamp, utc_datetime

_DEFAULT_TWEET_TEXT = "This is a valid sample tweet for unit tests with enough characters."
_CREATED_AT = format_iso_created_at(utc_datetime(2026, 5, 30, 0, 0, 0))
_SYNC_TIMESTAMP = format_run_timestamp(utc_datetime(2026, 5, 30, 10, 0, 0))


def mock_tweet_row(tweet_id: str, **overrides: Any) -> dict[str, Any]:
    """Return a dict that satisfies SyncTwitterPostModel (preprocess-ready text)."""
    row: dict[str, Any] = {
        "tweet_id": tweet_id,
        "text": _DEFAULT_TWEET_TEXT,
        "author_id": "100",
        "username": "testuser",
        "created_at": _CREATED_AT,
        "like_count": 1,
        "retweet_count": 0,
        "reply_count": 0,
        "quote_count": 0,
        "url": f"https://x.com/i/web/status/{tweet_id}",
        "keyword": "test",
        "sync_timestamp": _SYNC_TIMESTAMP,
    }
    row.update(overrides)
    SyncTwitterPostModel.model_validate(row)
    return row
