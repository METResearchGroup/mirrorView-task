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


def _require_columns(raw: pd.DataFrame, columns: frozenset[str]) -> None:
    missing = columns - set(raw.columns)
    if missing:
        raise KeyError(f"Results missing required columns: {sorted(missing)}")


def load_results_full() -> pd.DataFrame:
    """Load Phase 2 Part 3 results full from the dataset registry.

    Returns
    -------
    pandas.DataFrame
        Raw results-full frame for Phase 2 Part 3.
    """
    raise NotImplementedError


def filter_linked_fate_trials(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep linked-fate keep or remove trials with a usable post id.

    Parameters
    ----------
    raw
        Raw results frame.

    Returns
    -------
    pandas.DataFrame
        Slim trial rows after the linked-fate gate.

    Raises
    ------
    KeyError
        When a required column is missing.
    """
    _require_columns(raw, _REQUIRED_TRIAL_COLUMNS)
    trials = raw.copy()
    trials["evaluation_mode"] = (
        trials["evaluation_mode"].astype(str).str.lower().str.strip()
    )
    trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()
    trials = trials[trials["evaluation_mode"] == "linked_fate"].copy()
    trials = trials[trials["decision"].isin(_KEEP_REMOVE)].copy()
    trials = trials[trials["post_id"].notna()].copy()
    trials["post_id"] = trials["post_id"].astype(str).str.strip()
    trials = trials[trials["post_id"] != ""].copy()
    trials = trials[trials["post_id"].str.lower() != "nan"].copy()
    return trials.reset_index(drop=True)


def dedupe_worker_votes(trials: pd.DataFrame) -> pd.DataFrame:
    """Drop conflicting worker-post pairs and keep earliest votes.

    Parameters
    ----------
    trials
        Slim linked-fate trial rows.

    Returns
    -------
    pandas.DataFrame
        Rows after conflict drop and earliest-row dedupe.
    """
    raise NotImplementedError


def aggregate_votes_per_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate deduped trials to one row per post with vote counts.

    Parameters
    ----------
    trials
        Deduped trial rows with stable texts per post.

    Returns
    -------
    pandas.DataFrame
        One row per ``post_id`` with rater and decision counts.

    Raises
    ------
    ValueError
        When a post has conflicting original or mirror text.
    """
    raise NotImplementedError


def build_per_post_votes(raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Filter, dedupe, and aggregate votes to per-post counts.

    Parameters
    ----------
    raw
        Optional raw results frame. Loads from the registry when omitted.

    Returns
    -------
    pandas.DataFrame
        Per-post vote counts with stable pair text.
    """
    raise NotImplementedError
