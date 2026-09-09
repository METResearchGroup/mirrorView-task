"""Pinned sources and output constants for the right-high upsample."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)


@dataclass(frozen=True)
class CandidateBuildResult:
    """Right-medium leftover candidates and drop counts."""

    rows: pd.DataFrame
    leftover_right_medium_after_upsample: int
    pr260_ids_dropped: int


@dataclass(frozen=True)
class PromotionResult:
    """Promoted right-high rows and the unified upsample table."""

    promotion_ids: list[str]
    promoted: pd.DataFrame
    unified: pd.DataFrame


@dataclass(frozen=True)
class UnifiedUpsampleRunResult:
    """Counts and paths from one unified upsample run."""

    candidate_rows: int
    leftover_right_medium_after_upsample: int
    pr260_ids_dropped: int
    promotions: int
    unified_rows: int
    unified_medium: int
    unified_high: int
    unified_left: int
    unified_right: int
    promoted_local_path: str
    promoted_s3_uri: str
    promoted_sha256: str
    unified_local_path: str
    unified_s3_uri: str
    unified_sha256: str


def pinned_combined_source() -> CandidateSource:
    """Return the pinned combined parquet identity."""
    raise NotImplementedError


def pinned_sample_source() -> CandidateSource:
    """Return the pinned 10,200 post sample identity."""
    raise NotImplementedError


def pinned_medium_upsample_source() -> CandidateSource:
    """Return the pinned 2,000 unused medium parquet identity."""
    raise NotImplementedError
