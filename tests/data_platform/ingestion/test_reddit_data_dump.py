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

    def test_maps_dump_comment_onto_ingest_model(self) -> None:
        """A dump comment becomes a valid Reddit ingest row."""
        comment = _dump_comment()
        expected_record_id = f"{INTEGRATION_REDDIT}_t1_mvbyos2"
        expected_created_at = "2025-06-01T00:00:18+00:00"

        result = dump_comment_to_sync_row(comment, SYNC_TIMESTAMP)
        validated = SyncRedditCommentModel.model_validate(result)

        assert validated.comment_fullname == "t1_mvbyos2"
        assert validated.record_id == expected_record_id
        assert validated.author == "momamil"
        assert validated.body == "Example comment body."
        assert validated.created_at == expected_created_at
        assert validated.sync_timestamp == SYNC_TIMESTAMP
        assert "created_utc" not in result

    def test_nested_comment_uses_comment_fullname(self) -> None:
        """A reply still maps onto comment_fullname and record_id."""
        comment = _dump_comment(id="mvbyn04", parent_id="t1_mvbyhla")
        expected_record_id = f"{INTEGRATION_REDDIT}_t1_mvbyn04"

        result = dump_comment_to_sync_row(comment, SYNC_TIMESTAMP)

        assert result["comment_fullname"] == "t1_mvbyn04"
        assert result["record_id"] == expected_record_id

    def test_omits_dump_only_fields(self) -> None:
        """Dump-only keys such as subreddit are not copied onto the ingest row."""
        comment = _dump_comment()

        result = dump_comment_to_sync_row(comment, SYNC_TIMESTAMP)

        assert "subreddit" not in result
        assert "permalink" not in result
        assert "score" not in result
        assert "parent_id" not in result
