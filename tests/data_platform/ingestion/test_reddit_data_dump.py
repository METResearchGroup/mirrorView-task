"""Tests for Reddit dump comment read, filter, and ingest-model mapping."""

from __future__ import annotations

import json
from pathlib import Path
from random import Random

import pandas as pd
import pytest
import zstandard as zstd

from data_platform.ingestion.data_dumps.reddit.filters import keep_dump_comment
from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw
from data_platform.ingestion.data_dumps.reddit.process_dump import (
    SOURCE_DUMP_DIR,
    _input_paths,
    main,
    process_dump_file,
)
from data_platform.ingestion.data_dumps.reddit.reader import iter_dump_comments
from data_platform.ingestion.data_dumps.reddit.sample import reservoir_sample
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


def _dump_record(comment_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = dict(VALID_DUMP_COMMENT)
    payload["id"] = comment_id
    payload.update(overrides)
    return payload


class TestReservoirSample:
    """Tests for reservoir_sample()."""

    def test_is_repeatable_for_the_same_seed(self) -> None:
        """The same seed returns the same sample."""
        items = ["a", "b", "c", "d", "e"]
        sample_size = 3

        first = reservoir_sample(iter(items), sample_size, Random(0))
        second = reservoir_sample(iter(items), sample_size, Random(0))

        assert len(first) == sample_size
        assert first == second

    def test_returns_all_items_when_stream_is_shorter(self) -> None:
        """A short stream is returned in order."""
        items = ["a", "b"]
        expected = ["a", "b"]

        result = reservoir_sample(iter(items), 5, Random(0))

        assert result == expected

    def test_rejects_sample_size_below_one(self) -> None:
        """sample_size must be at least 1."""
        with pytest.raises(ValueError, match="sample_size"):
            reservoir_sample(iter(["a"]), 0, Random(0))


class TestProcessDumpFile:
    """Tests for process_dump_file()."""

    def test_writes_sampled_parquet_without_deleted_comments(
        self, tmp_path: Path
    ) -> None:
        """Deleted comments are dropped and the parquet has the sampled keepers."""
        input_path = tmp_path / "RC_test.zst"
        output_path = tmp_path / "filtered" / "RC_test.parquet"
        records = [
            _dump_record("keep1"),
            _dump_record("keep2"),
            _dump_record("keep3"),
            _dump_record("keep4"),
            _dump_record("gone", author="[deleted]"),
        ]
        _write_zst(input_path, records)
        expected_rows = 2
        deleted_tokens = {"[deleted]", "[removed]"}

        result = process_dump_file(
            input_path, output_path, expected_rows, 1, SYNC_TIMESTAMP
        )
        frame = pd.read_parquet(result)

        assert result == output_path
        assert len(frame) == expected_rows
        for row in frame.to_dict(orient="records"):
            SyncRedditCommentModel.model_validate(row)
            assert row["author"] not in deleted_tokens
            assert row["body"] not in deleted_tokens
            assert row["sync_timestamp"] == SYNC_TIMESTAMP

    def test_writes_all_keepers_when_below_sample_size(self, tmp_path: Path) -> None:
        """A file with fewer keepers than the sample size writes every keeper."""
        input_path = tmp_path / "RC_test.zst"
        output_path = tmp_path / "RC_test.parquet"
        _write_zst(input_path, [_dump_record("keep1"), _dump_record("keep2")])
        expected_rows = 2

        process_dump_file(input_path, output_path, 10, 1, SYNC_TIMESTAMP)
        frame = pd.read_parquet(output_path)

        assert len(frame) == expected_rows

    def test_raises_when_output_exists(self, tmp_path: Path) -> None:
        """An existing parquet is not overwritten."""
        input_path = tmp_path / "RC_test.zst"
        output_path = tmp_path / "RC_test.parquet"
        _write_zst(input_path, [_dump_record("keep1")])
        expected = "already written"
        output_path.write_text(expected)

        with pytest.raises(FileExistsError):
            process_dump_file(input_path, output_path, 10, 1, SYNC_TIMESTAMP)

        assert output_path.read_text() == expected

    def test_raises_when_input_is_missing(self, tmp_path: Path) -> None:
        """A missing dump file raises FileNotFoundError."""
        missing = tmp_path / "missing.zst"
        output_path = tmp_path / "out.parquet"

        with pytest.raises(FileNotFoundError):
            process_dump_file(missing, output_path, 10, 1, SYNC_TIMESTAMP)


class TestMain:
    """Tests for main()."""

    def test_writes_parquet_for_each_input_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI writes one parquet per --input-file under --output-dir."""
        first_input = tmp_path / "RC_2025-05.zst"
        second_input = tmp_path / "RC_2025-06.zst"
        output_dir = tmp_path / "filtered"
        _write_zst(first_input, [_dump_record("may1")])
        _write_zst(second_input, [_dump_record("jun1")])
        monkeypatch.setattr(
            "data_platform.ingestion.data_dumps.reddit.process_dump.get_current_timestamp",
            lambda: SYNC_TIMESTAMP,
        )

        main(
            [
                "--input-file",
                str(first_input),
                "--input-file",
                str(second_input),
                "--output-dir",
                str(output_dir),
            ]
        )

        first_frame = pd.read_parquet(output_dir / "RC_2025-05.parquet")
        second_frame = pd.read_parquet(output_dir / "RC_2025-06.parquet")
        assert len(first_frame) == 1
        assert len(second_frame) == 1
        assert first_frame.iloc[0]["sync_timestamp"] == SYNC_TIMESTAMP
        assert second_frame.iloc[0]["sync_timestamp"] == SYNC_TIMESTAMP


class TestInputPaths:
    """Tests for _input_paths()."""

    def test_defaults_to_experiment_month_files(self) -> None:
        """With no --input-file, the May and June experiment dumps are used."""
        expected = [
            SOURCE_DUMP_DIR / "RC_2025-05.zst",
            SOURCE_DUMP_DIR / "RC_2025-06.zst",
        ]

        result = _input_paths(None)

        assert result == expected
