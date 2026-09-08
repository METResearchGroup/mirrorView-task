"""S3 key helpers for flip-generation artifacts."""

from __future__ import annotations

BATCHES_DIRNAME = "batches"
PART_FILENAME_TEMPLATE = "part-{part_index:05d}.parquet"
ERRORS_FILENAME = "errors.jsonl"
FINAL_FILENAME = "flips.parquet"


def part_key(run_prefix: str, part_index: int) -> str:
    """Return the S3 key for one batch part."""
    raise NotImplementedError


def errors_key(run_prefix: str) -> str:
    """Return the S3 key for the append-only errors log."""
    raise NotImplementedError


def final_key(run_prefix: str) -> str:
    """Return the S3 key for the concatenated flips parquet."""
    raise NotImplementedError
