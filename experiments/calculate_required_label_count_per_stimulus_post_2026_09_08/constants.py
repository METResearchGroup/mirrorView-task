"""Pinned constants for remaining labels per stimulus post.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Batch(str, Enum):
    """Which stimulus batch a remaining-label row belongs to."""

    OLD = "old"
    NEW = "new"


@dataclass(frozen=True)
class NewSampleSource:
    """Pinned new sample parquet identity."""

    s3_uri: str
    sha256: str
    expected_row_count: int


@dataclass(frozen=True)
class LabelCountRunResult:
    """Counts and paths from one remaining-label run."""

    old_catalog_ids: int
    old_posts: int
    old_labels: int
    new_posts: int
    new_labels: int
    total_posts: int
    total_labels: int
    local_path: str
    s3_uri: str
    csv_sha256: str
    new_sample_uri: str
    new_sample_sha256: str
    new_sample_rows: int


@dataclass(frozen=True)
class LocalCsvWrite:
    """Local CSV path and file bytes."""

    path: Path
    body: bytes


def pinned_new_sample() -> NewSampleSource:
    """Return the pinned new sample identity."""
    raise NotImplementedError
