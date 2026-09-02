"""Tests that raw ingest rows carry ISO created_at and sync_timestamp.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_raw_row_timestamps.py
"""

from __future__ import annotations

from data_platform.ingestion.sync_bluesky import fetch_posts_for_keyword
from data_platform.ingestion.sync_reddit import comment_to_row, submission_to_row
from data_platform.ingestion.twitter_client import tweet_to_row
from data_platform.models.sync import (
    SyncBlueskyPostModel,
    SyncRedditCommentModel,
    SyncRedditPostModel,
    SyncTwitterPostModel,
)

__all__ = [
    "SyncBlueskyPostModel",
    "SyncRedditCommentModel",
    "SyncRedditPostModel",
    "SyncTwitterPostModel",
    "comment_to_row",
    "fetch_posts_for_keyword",
    "submission_to_row",
    "tweet_to_row",
]
