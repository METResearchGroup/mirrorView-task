"""Count remove votes for posts with five labelers.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py -q
"""

from __future__ import annotations

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    REQUIRED_LABELERS,
)


def select_scored_trials(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def dedupe_labeler_post(trials: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def aggregate_remove_counts(trials: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def posts_with_labeler_count(counts: pd.DataFrame, labeler_count: int) -> pd.DataFrame:
    raise NotImplementedError


def build_five_labeler_counts(raw: pd.DataFrame) -> pd.DataFrame:
    """Return posts that have five labelers and a remove-vote count."""
    trials = select_scored_trials(raw)
    deduped = dedupe_labeler_post(trials)
    counts = aggregate_remove_counts(deduped)
    return posts_with_labeler_count(counts, REQUIRED_LABELERS)
