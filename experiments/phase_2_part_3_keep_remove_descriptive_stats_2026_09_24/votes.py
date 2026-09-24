"""Clean linked-fate trials and aggregate keep/remove votes per post.

Run from repo root::

    PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_votes.py -q
"""

from __future__ import annotations

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_3_RESULTS_FULL

_KEEP_REMOVE = frozenset({"keep", "remove"})
_REQUIRED_TRIAL_COLUMNS = frozenset(
    {
        "evaluation_mode",
        "decision",
        "post_id",
        "prolific_id",
        "trial_index",
        "time_elapsed",
        "original_text",
        "mirror_text",
    }
)
_OUTPUT_COLUMNS = [
    "post_id",
    "n_raters",
    "keep_count",
    "remove_count",
    "n_unique_decisions",
    "is_unanimous",
    "original_text",
    "mirror_text",
]


def load_results_full() -> pd.DataFrame:
    """Load Phase 2 Part 3 results full from the dataset registry."""
    ...


def filter_linked_fate_trials(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep linked-fate keep or remove trials with a usable post id."""
    ...


def dedupe_worker_votes(trials: pd.DataFrame) -> pd.DataFrame:
    """Drop conflicting worker-post pairs and keep earliest votes."""
    ...


def aggregate_votes_per_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate deduped trials to one row per post with vote counts."""
    ...


def build_per_post_votes(raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Filter, dedupe, and aggregate votes to per-post counts."""
    ...
