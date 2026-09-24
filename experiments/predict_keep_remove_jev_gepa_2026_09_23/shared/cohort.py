"""Build cohort A labels from Phase 2 Part 3 moderation trials.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py --write-counts
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    ORIGINAL_FIRST_DRAW,
    PAIR_ORDER_BIN_COUNT,
    PAIR_ORDER_HASH_BYTES,
    PAIR_ORDER_MIRROR_FIRST,
    PAIR_ORDER_ORIGINAL_FIRST,
    PAIR_ORDER_SEED,
)

MIN_RATERS = 3
DECISION_KEEP = "keep"
DECISION_REMOVE = "remove"
TRIAL_TYPE_MODERATION = "moderation-trial"
_REQUIRED_FILTER_COLUMNS = ("trial_type", "post_id", "decision")
_REQUIRED_AGG_COLUMNS = (
    "post_id",
    "original_text",
    "mirror_text",
    "decision",
    "sampled_stance",
    "sample_toxicity_type",
)


def filter_scored_trials(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep moderation-trial rows with non-empty post_id and decision keep or remove.

    Normalize decision to lowercase stripped strings. Raise KeyError on missing columns.

    Parameters
    ----------
    frame
        Raw Part 3 export frame.

    Returns
    -------
    pandas.DataFrame
        Filtered trial rows.

    Raises
    ------
    KeyError
        When required columns are missing.
    """
    missing = [name for name in _REQUIRED_FILTER_COLUMNS if name not in frame.columns]
    if missing:
        raise KeyError(f"missing columns: {sorted(missing)}")
    trials = frame.copy()
    trial_type = trials["trial_type"].fillna("").astype(str).str.lower().str.strip()
    decision = trials["decision"].fillna("").astype(str).str.lower().str.strip()
    post_id = trials["post_id"].fillna("").astype(str).str.strip()
    keep = (
        (trial_type == TRIAL_TYPE_MODERATION)
        & post_id.ne("")
        & decision.isin({DECISION_KEEP, DECISION_REMOVE})
    )
    filtered = trials.loc[keep].copy()
    filtered["decision"] = decision.loc[filtered.index]
    filtered["post_id"] = post_id.loc[filtered.index]
    return filtered


def dedupe_participant_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Sort by post_id, prolific_id, time_elapsed, trial_index (mergesort) and keep first per pair.

    Parameters
    ----------
    trials
        Scored moderation trials.

    Returns
    -------
    pandas.DataFrame
        One row per ``(prolific_id, post_id)`` pair.
    """
    ordered = trials.sort_values(
        ["post_id", "prolific_id", "time_elapsed", "trial_index"],
        kind="mergesort",
    )
    return ordered.drop_duplicates(["post_id", "prolific_id"], keep="first")


def assert_stable_pair_text(trials: pd.DataFrame) -> None:
    """Raise ValueError when a post_id has multiple original_text or mirror_text values.

    Parameters
    ----------
    trials
        Scored moderation trials.

    Raises
    ------
    ValueError
        When pair text is not stable for a post.
    """
    for _post_id, group in trials.groupby("post_id"):
        originals = group["original_text"].fillna("").astype(str).unique()
        mirrors = group["mirror_text"].fillna("").astype(str).unique()
        if len(originals) != 1 or len(mirrors) != 1:
            raise ValueError("post_id has multiple original_text or mirror_text values")


def aggregate_post_labels(trials: pd.DataFrame) -> pd.DataFrame:
    """Return one row per post_id with vote counts and majority metadata.

    Parameters
    ----------
    trials
        Deduped scored moderation trials.

    Returns
    -------
    pandas.DataFrame
        Per-post vote summary.

    Raises
    ------
    KeyError
        When required columns are missing.
    ValueError
        When pair text is unstable.
    """
    missing = [name for name in _REQUIRED_AGG_COLUMNS if name not in trials.columns]
    if missing:
        raise KeyError(f"missing columns: {sorted(missing)}")
    assert_stable_pair_text(trials)
    tagged = trials.assign(
        _keep=trials["decision"].eq(DECISION_KEEP),
        _remove=trials["decision"].eq(DECISION_REMOVE),
    )
    counts = tagged.groupby("post_id", as_index=False).agg(
        n_raters=("decision", "size"),
        n_keep=("_keep", "sum"),
        n_remove=("_remove", "sum"),
        original_text=("original_text", "first"),
        mirror_text=("mirror_text", "first"),
        sampled_stance=("sampled_stance", "first"),
        sample_toxicity_type=("sample_toxicity_type", "first"),
    )
    counts["n_keep"] = counts["n_keep"].astype(int)
    counts["n_remove"] = counts["n_remove"].astype(int)
    counts["remove_share"] = counts["n_remove"] / counts["n_raters"]
    counts["is_unanimous"] = (counts["n_keep"] == 0) | (counts["n_remove"] == 0)
    counts["majority_decision"] = np.where(
        counts["n_keep"] > counts["n_remove"],
        DECISION_KEEP,
        DECISION_REMOVE,
    )
    return counts


def build_cohort_a(agg: pd.DataFrame) -> pd.DataFrame:
    """Keep posts with n_raters >= 3 and n_keep != n_remove. Set label from majority_decision.

    Parameters
    ----------
    agg
        Per-post vote summary from :func:`aggregate_post_labels`.

    Returns
    -------
    pandas.DataFrame
        Cohort A rows with ``label`` where 1 means remove and 0 means keep.
    """
    eligible = agg[
        (agg["n_raters"] >= MIN_RATERS) & (agg["n_keep"] != agg["n_remove"])
    ].copy()
    eligible["label"] = (eligible["majority_decision"] == DECISION_REMOVE).astype(int)
    return eligible


def pair_order_for_post(post_id: str, seed: int = PAIR_ORDER_SEED) -> tuple[str, str]:
    """SHA-256 seed hash; return (original, mirror) or (mirror, original).

    Parameters
    ----------
    post_id
        Post identifier.
    seed
        Pair-order seed.

    Returns
    -------
    tuple[str, str]
        Deterministic Post 1 and Post 2 roles.
    """
    digest = hashlib.sha256(f"{seed}:{post_id}".encode()).digest()
    rng_seed = int.from_bytes(digest[:PAIR_ORDER_HASH_BYTES], "big")
    rng = np.random.Generator(np.random.PCG64(rng_seed))
    if int(rng.integers(0, PAIR_ORDER_BIN_COUNT)) == ORIGINAL_FIRST_DRAW:
        return PAIR_ORDER_ORIGINAL_FIRST
    return PAIR_ORDER_MIRROR_FIRST


def attach_pair_order(cohort: pd.DataFrame) -> pd.DataFrame:
    """Add post_1_role and post_2_role columns.

    Parameters
    ----------
    cohort
        Cohort frame with ``post_id``.

    Returns
    -------
    pandas.DataFrame
        Cohort with deterministic pair-order roles.
    """
    ordered = cohort.copy()
    roles = [pair_order_for_post(str(post_id), PAIR_ORDER_SEED) for post_id in ordered["post_id"]]
    ordered["post_1_role"] = [role[0] for role in roles]
    ordered["post_2_role"] = [role[1] for role in roles]
    return ordered
