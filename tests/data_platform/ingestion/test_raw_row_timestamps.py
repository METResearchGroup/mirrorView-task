"""These tests check that raw ingest rows include ISO created_at and sync_timestamp.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_raw_row_timestamps.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from data_platform.ingestion.generate_record_id import attach_record_id
from data_platform.ingestion.integrations.bluesky import BlueskyClient
from data_platform.ingestion.sync_reddit import comment_to_row, submission_to_row
from data_platform.ingestion.twitter_client import tweet_to_row
from data_platform.models.sync import (
    SyncBlueskyPostModel,
    SyncRedditCommentModel,
    SyncRedditPostModel,
    SyncTwitterPostModel,
)
from tests.data_platform.ingestion.conftest import mock_post, mock_search_response

SYNC_TIMESTAMP = "2026_05_30-10:00:00"
CREATED_AT_ISO = "2026-05-30T00:00:00+00:00"
CREATED_AT_UNIX = datetime(2026, 5, 30, tzinfo=timezone.utc).timestamp()


def _mock_submission() -> SimpleNamespace:
    return SimpleNamespace(
        id="abc123",
        name="t3_abc123",
        subreddit=SimpleNamespace(display_name="politics"),
        title="title",
        selftext="body",
        author="user",
        score=1,
        upvote_ratio=0.5,
        num_comments=1,
        created_utc=CREATED_AT_UNIX,
        permalink="/r/politics/comments/abc123/title/",
        url="https://reddit.com/r/politics/comments/abc123/title/",
        is_self=True,
    )


def _mock_comment() -> SimpleNamespace:
    return SimpleNamespace(
        name="t1_xyz789",
        author="user",
        body="comment body",
        created_utc=CREATED_AT_UNIX,
    )


def _tweet(*, created_at: datetime | None) -> SimpleNamespace:
    return SimpleNamespace(
        id="123",
        text="hello",
        author_id="99",
        created_at=created_at,
        public_metrics={
            "like_count": 0,
            "retweet_count": 0,
            "reply_count": 0,
            "quote_count": 0,
        },
    )


class TestFetchPostsForKeyword:
    """Tests for BlueskyClient.fetch_posts_for_keyword()."""

    def test_writes_created_at_and_sync_timestamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bluesky rows include ISO created_at and the run sync_timestamp."""
        ingestion_params = {"limit_per_task": 1, "sort": "latest"}
        response = mock_search_response([mock_post("at://did:plc:ex/app.bsky.feed.post/a1")])
        monkeypatch.setattr(
            BlueskyClient,
            "_search_posts_page",
            lambda *_args, **_kwargs: response,
        )

        client = BlueskyClient(client=MagicMock())
        result = client.fetch_posts_for_keyword(
            ingestion_params,
            "alpha",
            task_id="alpha",
            sync_timestamp=SYNC_TIMESTAMP,
        )

        expected_created_at = "2026-05-30T00:00:00.000Z"
        assert result.rows[0]["created_at"] == expected_created_at
        assert result.rows[0]["sync_timestamp"] == SYNC_TIMESTAMP
        SyncBlueskyPostModel.model_validate(attach_record_id(result.rows[0], "bluesky"))


class TestSubmissionToRow:
    """Tests for submission_to_row()."""

    def test_writes_iso_created_at_without_created_utc(self) -> None:
        """submission_to_row writes ISO created_at and omits created_utc."""
        result = submission_to_row(_mock_submission(), SYNC_TIMESTAMP)

        assert result["created_at"] == CREATED_AT_ISO
        assert "created_utc" not in result
        assert result["sync_timestamp"] == SYNC_TIMESTAMP
        SyncRedditPostModel.model_validate(attach_record_id(result, "reddit"))


class TestCommentToRow:
    """Tests for comment_to_row()."""

    def test_writes_iso_created_at_without_created_utc(self) -> None:
        """comment_to_row writes ISO created_at and omits created_utc."""
        result = comment_to_row(_mock_comment(), SYNC_TIMESTAMP)

        assert result["created_at"] == CREATED_AT_ISO
        assert "created_utc" not in result
        assert result["sync_timestamp"] == SYNC_TIMESTAMP
        assert set(result) == {
            "comment_fullname",
            "author",
            "body",
            "created_at",
            "sync_timestamp",
        }
        SyncRedditCommentModel.model_validate(attach_record_id(result, "reddit"))


class TestTweetToRow:
    """Tests for tweet_to_row()."""

    def test_writes_iso_created_at_and_sync_timestamp(self) -> None:
        """tweet_to_row writes ISO created_at and sync_timestamp."""
        created_at = datetime(2026, 5, 30, tzinfo=timezone.utc)
        result = tweet_to_row(
            _tweet(created_at=created_at),
            username="user",
            keyword="alpha",
            sync_timestamp=SYNC_TIMESTAMP,
        )

        assert result["created_at"] == CREATED_AT_ISO
        assert result["sync_timestamp"] == SYNC_TIMESTAMP
        SyncTwitterPostModel.model_validate(attach_record_id(result, "twitter"))

    def test_writes_empty_created_at_when_payload_time_is_missing(self) -> None:
        """tweet_to_row writes an empty created_at when the payload time is missing."""
        result = tweet_to_row(
            _tweet(created_at=None),
            username="user",
            keyword="alpha",
            sync_timestamp=SYNC_TIMESTAMP,
        )

        assert result["created_at"] == ""
        assert result["sync_timestamp"] == SYNC_TIMESTAMP
