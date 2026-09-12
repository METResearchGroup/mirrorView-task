"""Build the shared September 2026 cohort from Prolific CSV exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    CohortTrial,
    CohortUser,
)


@dataclass(frozen=True)
class BuildCohortResult:
    """Users, trials, and drop counts from one cohort build."""

    users: tuple[CohortUser, ...]
    trials: tuple[CohortTrial, ...]
    dropped_incomplete: int
    dropped_missing_pair_order: int
    dropped_missing_reflection: int


def list_september_csv_keys(store_or_s3_client) -> list[str]:
    """List September study CSV keys at or after 2026-09-09."""
    raise NotImplementedError


def build_cohort(csv_paths: list[Path]) -> BuildCohortResult:
    """Confirm complete participants from downloaded CSV paths."""
    raise NotImplementedError
