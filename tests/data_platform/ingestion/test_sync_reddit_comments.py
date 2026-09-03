"""Tests for slim Reddit comment ingest rows.

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
    """List-backed stand-in for a PRAW CommentForest."""

    def replace_more(self, limit: int = 0) -> list[object]:
        del limit
        return []


def _comment(
    name: str,
    *,
    body: str = ELIGIBLE_BODY,
    stickied: bool = False,
    distinguished: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=name.removeprefix("t1_"),
        name=name,
        parent_id="t3_abc123",
        author="user",
        body=body,
        score=1,
        created_utc=CREATED_AT_UNIX,
        permalink="/r/politics/comments/abc123/title/x/",
        stickied=stickied,
        distinguished=distinguished,
        replies=[],
    )


class TestSyncRedditCommentModel:
    """Tests for SyncRedditCommentModel extra-field policy."""

    def test_rejects_dropped_geometry_fields(self) -> None:
        """Old comment-tree columns are invalid on the slim sync model."""
        row = mock_comment_row("t1_keep")
        row["depth"] = 0

        with pytest.raises(ValidationError):
            SyncRedditCommentModel.model_validate(row)


class TestFetchPostComments:
    """Tests for fetch_post_comments()."""

    def test_keeps_eligible_comments_without_tree_position(self) -> None:
        """Eligible comments are kept and do not store depth or rank."""
        forest = FakeCommentForest(
            [
                _comment("t1_sticky", stickied=True),
                _comment("t1_keep"),
                _comment("t1_mod", distinguished="moderator"),
                _comment("t1_short", body="too short"),
            ]
        )
        submission = SimpleNamespace(
            id="abc123",
            name="t3_abc123",
            subreddit=SimpleNamespace(display_name="politics"),
            comments=forest,
        )

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
