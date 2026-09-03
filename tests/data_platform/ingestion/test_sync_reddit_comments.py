"""Tests for Reddit comment ingest rows with fewer fields.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_reddit_comments.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from data_platform.ingestion.generate_record_id import attach_record_id
from data_platform.ingestion.sync_reddit import fetch_post_comments
from data_platform.models.sync import SyncRedditCommentModel
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row

SYNC_TIMESTAMP = "2026_05_30-10:00:00"
CREATED_AT_UNIX = datetime(2026, 5, 30, tzinfo=timezone.utc).timestamp()
ELIGIBLE_BODY = "this comment body is long enough"


class FakeCommentForest(list):
    """A list that stands in for a PRAW CommentForest."""

    def replace_more(self, limit: int = 0) -> list[object]:
        del limit
        return []


def _comment(
    name: str,
    *,
    body: str = ELIGIBLE_BODY,
    stickied: bool = False,
    distinguished: str | None = None,
    replies: list[object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        author="user",
        body=body,
        created_utc=CREATED_AT_UNIX,
        stickied=stickied,
        distinguished=distinguished,
        replies=FakeCommentForest(replies or []),
    )


class TestSyncRedditCommentModel:
    """Tests that SyncRedditCommentModel rejects unexpected columns."""

    def test_rejects_columns_that_are_no_longer_on_a_comment_row(self) -> None:
        """SyncRedditCommentModel rejects columns such as depth that are no longer on a comment row."""
        row = mock_comment_row("t1_keep")
        row["depth"] = 0

        with pytest.raises(ValidationError):
            SyncRedditCommentModel.model_validate(row)


class TestFetchPostComments:
    """Tests for fetch_post_comments()."""

    def test_keeps_eligible_comments_without_depth_or_rank(self) -> None:
        """fetch_post_comments keeps eligible comments, and the rows do not include depth or rank."""
        forest = FakeCommentForest(
            [
                _comment("t1_sticky", stickied=True),
                _comment("t1_keep"),
                _comment("t1_mod", distinguished="moderator"),
                _comment("t1_short", body="too short"),
            ]
        )
        submission = SimpleNamespace(comments=forest)

        result = fetch_post_comments(
            submission,
            max_comments=10,
            min_body_length=10,
            sync_timestamp=SYNC_TIMESTAMP,
        )

        assert [row["comment_fullname"] for row in result] == ["t1_keep"]
        assert "depth" not in result[0]
        assert "comment_rank" not in result[0]
        SyncRedditCommentModel.model_validate(attach_record_id(result[0], "reddit"))

    def test_collects_nested_replies_in_display_order(self) -> None:
        """Nested replies are still visited after depth tracking is removed."""
        child = _comment("t1_child")
        parent = _comment("t1_parent", replies=[child])
        submission = SimpleNamespace(comments=FakeCommentForest([parent]))

        result = fetch_post_comments(
            submission,
            max_comments=10,
            min_body_length=10,
            sync_timestamp=SYNC_TIMESTAMP,
        )

        assert [row["comment_fullname"] for row in result] == ["t1_parent", "t1_child"]
