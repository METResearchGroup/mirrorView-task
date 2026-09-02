"""These tests check that raw ingest rows include ISO created_at and sync_timestamp.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_raw_row_timestamps.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from data_platform.ingestion.sync_bluesky import fetch_posts_for_keyword
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
        id="xyz789",
        name="t1_xyz789",
        parent_id="t3_abc123",
        author="user",
        body="comment body",
        score=2,
        created_utc=CREATED_AT_UNIX,
        permalink="/r/politics/comments/abc123/title/xyz789/",
    )


class TestFetchPostsForKeyword:
    """Tests for fetch_posts_for_keyword()."""

    def test_writes_created_at_and_sync_timestamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bluesky rows include ISO created_at and the run sync_timestamp."""
        ingestion_params = {"limit_per_task": 1, "sort": "latest"}
        response = mock_search_response([mock_post("at://did:plc:ex/app.bsky.feed.post/a1")])
        monkeypatch.setattr(
            "data_platform.ingestion.sync_bluesky._search_posts_page",
            lambda *_args, **_kwargs: response,
        )

        rows, _stats = fetch_posts_for_keyword(
            MagicMock(),
            ingestion_params,
            "alpha",
            task_id="alpha",
            sync_timestamp=SYNC_TIMESTAMP,
        )

        expected_created_at = "2026-05-30T00:00:00.000Z"
        assert rows[0]["created_at"] == expected_created_at
        assert rows[0]["sync_timestamp"] == SYNC_TIMESTAMP
        SyncBlueskyPostModel.model_validate(rows[0])


class TestSubmissionToRow:
    """Tests for submission_to_row()."""

    def test_writes_iso_created_at_and_keeps_created_utc_alias(self) -> None:
        """submission_to_row writes ISO created_at and keeps created_utc as an alias."""
        result = submission_to_row(_mock_submission(), SYNC_TIMESTAMP)

        expected = CREATED_AT_ISO
        assert result["created_at"] == expected
        assert result["created_utc"] == expected
        assert result["sync_timestamp"] == SYNC_TIMESTAMP
        SyncRedditPostModel.model_validate(result)


class TestCommentToRow:
    """Tests for comment_to_row()."""

    def test_writes_iso_created_at_and_keeps_created_utc_alias(self) -> None:
        """comment_to_row writes ISO created_at and keeps created_utc as an alias."""
        result = comment_to_row(
            _mock_comment(),
            _mock_submission(),
            SYNC_TIMESTAMP,
            depth=0,
            comment_rank=1,
        )

        expected = CREATED_AT_ISO
        assert result["created_at"] == expected
        assert result["created_utc"] == expected
        assert result["sync_timestamp"] == SYNC_TIMESTAMP
        SyncRedditCommentModel.model_validate(result)


class TestTweetToRow:
    """Tests for tweet_to_row()."""

    def test_keeps_created_at_and_sync_timestamp(self) -> None:
        """tweet_to_row still writes ISO created_at and sync_timestamp."""
        created_at = datetime(2026, 5, 30, tzinfo=timezone.utc)
        tweet = SimpleNamespace(
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

        result = tweet_to_row(
            tweet,
            username="user",
            keyword="alpha",
            sync_timestamp=SYNC_TIMESTAMP,
        )

        assert datetime.fromisoformat(str(result["created_at"])) == created_at
        assert result["sync_timestamp"] == SYNC_TIMESTAMP
        SyncTwitterPostModel.model_validate(result)
