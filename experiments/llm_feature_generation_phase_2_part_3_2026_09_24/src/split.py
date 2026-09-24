"""Stratified discovery versus test split for the cohort.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.split \\
      --seed 42 --write
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.constants import (
    STRATIFY_COLUMNS,
)


@dataclass(frozen=True)
class SplitResult:
    """Discovery and test ID lists plus metadata path."""

    discovery_ids: list[str]
    test_ids: list[str]
    metadata_path: Path


def build_stratify_key(frame: pd.DataFrame) -> pd.Series:
    """Build the concatenated stratification key for train_test_split."""
    raise NotImplementedError


def stratified_split(
    cohort: pd.DataFrame,
    seed: int,
) -> tuple[list[str], list[str]]:
    """Return discovery and test post ID lists."""
    raise NotImplementedError


def write_split_outputs(
    cohort: pd.DataFrame,
    discovery_ids: list[str],
    test_ids: list[str],
    seed: int,
    participant_filter: str,
) -> SplitResult:
    """Write split CSVs, metadata, and update cohort parquet split column."""
    raise NotImplementedError


def main() -> None:
    """Parse CLI args and write split artifacts when ``--write`` is set."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
