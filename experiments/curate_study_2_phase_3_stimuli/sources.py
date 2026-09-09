"""Pinned sources and catalog constants for the 10,000 post catalog."""

from __future__ import annotations

from dataclasses import dataclass

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)


@dataclass(frozen=True)
class FlipSource:
    """One pinned flips parquet."""

    s3_uri: str
    sha256: str
    expected_row_count: int


@dataclass(frozen=True)
class JoinedFlipPool:
    """Posts that have a successful flip, from the sample and the upsample."""

    rows: object
    sample_joined_rows: int
    upsample_joined_rows: int


@dataclass(frozen=True)
class CatalogRunResult:
    """Counts and paths from one catalog run, including a pause."""

    available: dict[str, dict[str, int]]
    catalog_written: bool
    catalog_rows: int
    local_path: str
    s3_uri: str
    csv_sha256: str


def pinned_sample_source() -> CandidateSource:
    """Return the pinned 10,200 post sample identity."""
    raise NotImplementedError


def pinned_unified_source() -> CandidateSource:
    """Return the pinned unified 2,300 post parquet identity."""
    raise NotImplementedError


def pinned_sample_flips() -> FlipSource:
    """Return the pinned existing sample flips identity."""
    raise NotImplementedError


def pinned_unified_flips() -> FlipSource:
    """Return the pinned unified upsample flips identity."""
    raise NotImplementedError
