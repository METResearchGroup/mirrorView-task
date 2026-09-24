"""Build the post-level cohort for Phase 2 Part 3.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort \\
      --participant-filter all --write
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

ParticipantFilter = Literal["all", "attention_pass"]


@dataclass(frozen=True)
class CohortBuildStats:
    """Summary counts printed after a cohort build."""

    n_posts: int
    n_labeled: int
    n_part2_overlap: int
    label_count_one: int
    label_count_two: int
    label_count_three_plus: int


@dataclass(frozen=True)
class CohortWriteResult:
    """Paths written for one cohort build across text arms."""

    run_timestamp: str
    stats: CohortBuildStats
    cohort_paths: tuple[Path, ...]


def slim_trials(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep phase-one linked-fate keep or remove moderation trials."""
    raise NotImplementedError


def filter_by_participant(
    trials: pd.DataFrame,
    participant_filter: ParticipantFilter,
) -> pd.DataFrame:
    """Apply the all or attention_pass participant filter."""
    raise NotImplementedError


def drop_conflicting_worker_posts(trials: pd.DataFrame) -> pd.DataFrame:
    """Drop worker-post pairs that contain both keep and remove."""
    raise NotImplementedError


def dedupe_worker_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Keep the earliest row per worker and post."""
    raise NotImplementedError


def assign_group(keep_count: int, remove_count: int) -> str | None:
    """Return split, unanimous_keep, unanimous_remove, or None."""
    raise NotImplementedError


def modal_decision(keep_count: int, remove_count: int) -> str | None:
    """Return keep, remove, or None when there are zero raters."""
    raise NotImplementedError


def three_group_label(keep_count: int, remove_count: int) -> str | None:
    """Return the three-group label when n_raters meets MIN_RATERS."""
    raise NotImplementedError


def map_toxicity_type(raw_value: str) -> str:
    """Map sample_*_toxicity strings to low, middle, or high."""
    raise NotImplementedError


def build_cohort_frame(participant_filter: ParticipantFilter) -> pd.DataFrame:
    """Build the full post-level cohort table."""
    raise NotImplementedError


def write_cohort_outputs(
    cohort: pd.DataFrame,
    stats: CohortBuildStats,
    participant_filter: ParticipantFilter,
    run_timestamp: str,
) -> CohortWriteResult:
    """Write cohort parquet and metadata for each text arm."""
    raise NotImplementedError


def main() -> None:
    """Parse CLI args and build cohort outputs when ``--write`` is set."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
