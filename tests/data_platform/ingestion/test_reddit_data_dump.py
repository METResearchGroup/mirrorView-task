"""Tests for Reddit dump comment read, filter, and ingest-model mapping."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import zstandard as zstd

from data_platform.ingestion.data_dumps.reddit.filters import keep_dump_comment
from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw
from data_platform.ingestion.data_dumps.reddit.reader import iter_dump_comments
from data_platform.ingestion.data_dumps.reddit.transform import dump_comment_to_sync_row
from data_platform.ingestion.generate_record_id import INTEGRATION_REDDIT
from data_platform.models.sync import SyncRedditCommentModel

VALID_DUMP_COMMENT = {
    "id": "mvbyos2",
    "author": "momamil",
    "link_id": "t3_1l09l1b",
    "parent_id": "t3_1l09l1b",
    "subreddit": "politics",
    "body": "Example comment body.",
    "score": 1,
    "created_utc": 1_748_736_018,
    "permalink": "/r/politics/comments/1l09l1b/title/mvbyos2/",
}
SYNC_TIMESTAMP = "2026_09_03-12:00:00"


def _dump_comment(**overrides: object) -> DumpCommentRaw:
    payload = dict(VALID_DUMP_COMMENT)
    payload.update(overrides)
    return DumpCommentRaw.model_validate(payload)


def _write_zst(path: Path, records: list[object]) -> None:
    lines: list[str] = []
    for record in records:
        if record is None:
            lines.append("")
        elif isinstance(record, str):
            lines.append(record)
        else:
            lines.append(json.dumps(record))
    payload = "\n".join(lines).encode("utf-8")
    path.write_bytes(zstd.ZstdCompressor().compress(payload))


class TestIterDumpComments:
    """Tests for iter_dump_comments()."""

    def test_yields_one_valid_comment(self, tmp_path: Path) -> None:
        """A compressed file with one valid comment yields that comment."""
        fixture = tmp_path / "RC_test.zst"
        _write_zst(fixture, [VALID_DUMP_COMMENT])
        expected = "mvbyos2"

        result = list(iter_dump_comments(fixture))

        assert len(result) == 1
        assert result[0].id == expected

    def test_skips_blank_and_invalid_lines(self, tmp_path: Path) -> None:
        """Blank lines and invalid JSON are skipped."""
        fixture = tmp_path / "RC_test.zst"
        _write_zst(fixture, [None, "not-json", VALID_DUMP_COMMENT])

        result = list(iter_dump_comments(fixture))

        assert len(result) == 1
        assert result[0].id == "mvbyos2"

    def test_raises_when_path_is_not_a_file(self, tmp_path: Path) -> None:
        """A missing dump file raises FileNotFoundError."""
        missing = tmp_path / "missing.zst"

        with pytest.raises(FileNotFoundError):
            list(iter_dump_comments(missing))


class TestKeepDumpComment:
    """Tests for keep_dump_comment()."""

    def test_keeps_ordinary_comment(self) -> None:
        """A normal author and body are kept."""
        comment = _dump_comment(author="user", body="hello")

        result = keep_dump_comment(comment)

        assert result is True

    def test_drops_deleted_author(self) -> None:
        """Author [deleted] is dropped."""
        comment = _dump_comment(author="[deleted]")

        result = keep_dump_comment(comment)

        assert result is False

    def test_drops_removed_body(self) -> None:
        """Body [removed] is dropped."""
        comment = _dump_comment(body="[removed]")

        result = keep_dump_comment(comment)

        assert result is False

    def test_drops_stripped_deleted_body(self) -> None:
        """Body [deleted] with surrounding spaces is dropped."""
        comment = _dump_comment(body="  [deleted]  ")

        result = keep_dump_comment(comment)

        assert result is False

    def test_keeps_short_body(self) -> None:
        """Short bodies that are not deleted tokens are kept."""
        comment = _dump_comment(body="short")

        result = keep_dump_comment(comment)

        assert result is True


class TestDumpCommentToSyncRow:
    """Tests for dump_comment_to_sync_row()."""

    def test_maps_top_level_comment_onto_ingest_model(self) -> None:
        """A top-level dump comment becomes a valid Reddit ingest row."""
        comment = _dump_comment()
        expected_record_id = f"{INTEGRATION_REDDIT}_1l09l1b_mvbyos2"
        expected_created_at = "2025-06-01T00:00:18+00:00"

        result = dump_comment_to_sync_row(comment, SYNC_TIMESTAMP)
        validated = SyncRedditCommentModel.model_validate(result)

        assert validated.post_reddit_id == "1l09l1b"
        assert validated.post_reddit_fullname == "t3_1l09l1b"
        assert validated.comment_fullname == "t1_mvbyos2"
        assert validated.record_id == expected_record_id
        assert validated.created_at == expected_created_at
        assert "created_utc" not in result
        assert validated.depth == 0
        assert validated.comment_rank == 0
        assert validated.sync_timestamp == SYNC_TIMESTAMP

    def test_nested_comment_has_depth_one(self) -> None:
        """A reply to a comment has depth 1."""
        comment = _dump_comment(parent_id="t1_mvbyhla")

        result = dump_comment_to_sync_row(comment, SYNC_TIMESTAMP)

        assert result["depth"] == 1

    def test_synthesizes_permalink_when_missing(self) -> None:
        """A missing permalink is built from subreddit, post id, and comment id."""
        comment = _dump_comment(permalink=None)
        expected = "/r/politics/comments/1l09l1b/_/mvbyos2/"

        result = dump_comment_to_sync_row(comment, SYNC_TIMESTAMP)

        assert result["permalink"] == expected
