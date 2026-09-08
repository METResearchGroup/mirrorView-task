"""Pinned candidate parquet and sample constants for the filter run."""

from __future__ import annotations

from dataclasses import dataclass

from experiments.combine_data_into_stimulus_set_2026_09_08.sources import (
    COMBINED_COLUMNS,
    SORT_COLUMNS,
    STANCE_CROSSTAB_ROWS,
    TOXICITY_CROSSTAB_COLUMNS,
)


@dataclass(frozen=True)
class CandidateSource:
    """One pinned combined parquet used as the filter input."""


@dataclass(frozen=True)
class CleanupSummary:
    """Row counts after each cleanup step."""


@dataclass(frozen=True)
class FilterRunResult:
    """Local path, S3 URI, hash, and counts from one filter run."""


def pinned_candidate_source() -> CandidateSource:
    """Return the pinned combined parquet identity."""
    raise NotImplementedError
