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


def _assert_stable_texts(trials: pd.DataFrame) -> None:
    text_nunique = (
        trials.groupby("post_id", dropna=False)
        .agg(
            original_text_nunique=("original_text", lambda s: s.fillna("").nunique()),
            mirror_text_nunique=("mirror_text", lambda s: s.fillna("").nunique()),
        )
        .reset_index()
    )
    bad = text_nunique[
        (text_nunique["original_text_nunique"] != 1)
        | (text_nunique["mirror_text_nunique"] != 1)
    ]
    if len(bad):
        example_post = str(bad.iloc[0]["post_id"])
        raise ValueError(
            "Expected stable original/mirror text per post_id, but found conflicts. "
            f"Example problematic post_id={example_post}."
        )


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
    return load_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL, low_memory=False)


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
    frame = trials.copy()
    frame = frame[frame["prolific_id"].notna()].copy()
    frame["prolific_id"] = frame["prolific_id"].astype(str).str.strip()
    frame = frame[frame["prolific_id"] != ""].copy()
    frame = frame[frame["prolific_id"].str.lower() != "nan"].copy()
    worker_post = ["post_id", "prolific_id"]
    distinct_decisions = frame.groupby(worker_post)["decision"].transform("nunique")
    frame = frame.loc[distinct_decisions == 1].copy()
    ordered = frame.sort_values(
        ["post_id", "prolific_id", "trial_index", "time_elapsed"],
        kind="mergesort",
    )
    return ordered.drop_duplicates(worker_post, keep="first").reset_index(drop=True)


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
    _assert_stable_texts(trials)
    grouped = (
        trials.groupby("post_id", dropna=False)
        .agg(
            n_raters=("decision", "size"),
            n_unique_decisions=("decision", "nunique"),
            keep_count=("decision", lambda s: int((s == "keep").sum())),
            remove_count=("decision", lambda s: int((s == "remove").sum())),
            original_text=("original_text", "first"),
            mirror_text=("mirror_text", "first"),
        )
        .reset_index()
    )
    grouped["is_unanimous"] = grouped["n_unique_decisions"] == 1
    grouped["post_id"] = grouped["post_id"].astype(str)
    grouped["n_raters"] = grouped["n_raters"].astype(int)
    grouped["keep_count"] = grouped["keep_count"].astype(int)
    grouped["remove_count"] = grouped["remove_count"].astype(int)
    grouped["n_unique_decisions"] = grouped["n_unique_decisions"].astype(int)
    grouped["is_unanimous"] = grouped["is_unanimous"].astype(bool)
    grouped["original_text"] = grouped["original_text"].astype(str)
    grouped["mirror_text"] = grouped["mirror_text"].astype(str)
    return grouped[_OUTPUT_COLUMNS].reset_index(drop=True)


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
    raw_frame = raw if raw is not None else load_results_full()
    trials = filter_linked_fate_trials(raw_frame)
    trials = dedupe_worker_votes(trials)
    return aggregate_votes_per_post(trials)
