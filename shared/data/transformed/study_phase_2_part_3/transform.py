"""Build and materialize Part 3 keep/remove labels.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_3/transform.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

STIMULI_JOIN_KEY = "post_primary_key"
RESULTS_JOIN_KEY = "post_id"
OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_labels.csv"


def _load_slim_trial_frame(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def _aggregate_modal_labels_with_counts(trials: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def _build_unanimous_flags(trials: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def _join_stimuli_metadata(modal: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def build_keep_remove_labels(
    raw: pd.DataFrame | None = None,
    stimuli: pd.DataFrame | None = None,
) -> pd.DataFrame:
    raise NotImplementedError


def write_keep_remove_labels(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    raise NotImplementedError


if __name__ == "__main__":
    write_keep_remove_labels()
