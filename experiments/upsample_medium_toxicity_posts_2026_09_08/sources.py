"""Pinned combined parquet, 10,200 sample, and upsample output constants."""

from __future__ import annotations

from dataclasses import dataclass

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)


@dataclass(frozen=True)
class UpsampleRunResult:
    """Counts and paths from one unused medium upsample run."""


def pinned_combined_source() -> CandidateSource:
    """Return the pinned combined parquet identity."""
    raise NotImplementedError


def pinned_sample_source() -> CandidateSource:
    """Return the pinned 10,200 post sample identity."""
    raise NotImplementedError
