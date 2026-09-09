"""Pinned sources and output constants for the right-high upsample."""

from __future__ import annotations

from dataclasses import dataclass

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)


@dataclass(frozen=True)
class CandidateBuildResult:
    """Right-medium leftover candidates and drop counts."""


@dataclass(frozen=True)
class PromotionResult:
    """Promoted right-high rows and the unified upsample table."""


@dataclass(frozen=True)
class UnifiedUpsampleRunResult:
    """Counts and paths from one unified upsample run."""


def pinned_combined_source() -> CandidateSource:
    """Return the pinned combined parquet identity."""
    raise NotImplementedError


def pinned_sample_source() -> CandidateSource:
    """Return the pinned 10,200 post sample identity."""
    raise NotImplementedError


def pinned_medium_upsample_source() -> CandidateSource:
    """Return the pinned 2,000 unused medium parquet identity."""
    raise NotImplementedError
