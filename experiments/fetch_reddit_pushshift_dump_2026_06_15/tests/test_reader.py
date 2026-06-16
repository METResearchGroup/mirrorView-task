"""Unit tests for zstd JSONL reader."""

import json
from pathlib import Path

import zstandard as zstd

from experiments.fetch_reddit_pushshift_dump_2026_06_15.reader import iter_pushshift_comments


def _write_fixture(path: Path, records: list[dict]) -> None:
    payload = "\n".join(json.dumps(record) for record in records).encode("utf-8")
    compressed = zstd.ZstdCompressor().compress(payload)
    path.write_bytes(compressed)


def test_iter_pushshift_comments_reads_fixture(tmp_path: Path):
    fixture = tmp_path / "RC_test.zst"
    records = [
        {
            "id": "abc",
            "author": "user",
            "link_id": "t3_post",
            "parent_id": "t3_post",
            "subreddit": "politics",
            "body": "Example comment body long enough.",
            "score": 2,
            "created_utc": 1_700_000_000,
        }
    ]
    _write_fixture(fixture, records)
    parsed = list(iter_pushshift_comments(fixture))
    assert len(parsed) == 1
    assert parsed[0].id == "abc"
