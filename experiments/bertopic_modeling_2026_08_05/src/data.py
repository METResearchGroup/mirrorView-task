"""Load modal keep/remove posts and join unanimous flags from results-full.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python -c \\
      \"from experiments.bertopic_modeling_2026_08_05.src import data; print(len(data.load_posts_with_unanimous()))\"
"""

from __future__ import annotations

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS,
    STUDY_PHASE_2_PART_2_RESULTS_FULL,
)

UNANIMOUS_RULE_ID = "all_linked_fate_raters_same_decision"
UNANIMOUS_RULE_TEXT = (
    "Among STUDY_PHASE_2_PART_2_RESULTS_FULL rows with evaluation_mode == "
    '"linked_fate" and decision ∈ {keep, remove} and non-empty post_id, group by '
    "post_id. is_unanimous = True iff all decisions in the group are identical "
    "(nunique(decision) == 1). Else False. Join to modal labels on "
    "message_id == post_id."
)

_REQUIRED_LABEL_COLUMNS = (
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
)
_KEEP_REMOVE = frozenset({"keep", "remove"})


def load_keep_remove_posts() -> pd.DataFrame:
    """Load modal keep/remove labels from the shared registry.

    Returns
    -------
    pandas.DataFrame
        One row per post with required label columns. ``decision`` is
        lowercased and stripped.

    Raises
    ------
    KeyError
        If required columns are missing.
    ValueError
        If ``decision`` contains values outside ``{keep, remove}``.
    """
    frame = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)
    missing = [c for c in _REQUIRED_LABEL_COLUMNS if c not in frame.columns]
    if missing:
        raise KeyError(f"KEEP_REMOVE_LABELS missing columns: {missing}")

    out = frame.copy()
    out["decision"] = out["decision"].astype(str).str.lower().str.strip()
    out["message_id"] = out["message_id"].astype(str).str.strip()
    unexpected = set(out["decision"].unique()) - _KEEP_REMOVE
    if unexpected:
        raise ValueError(f"Unexpected decision values: {sorted(unexpected)}")
    return out.reset_index(drop=True)


def _build_unanimous_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Aggregate linked-fate keep/remove trials into per-post unanimous flags."""
    trials = raw.copy()
    if "evaluation_mode" not in trials.columns:
        raise KeyError("Expected `evaluation_mode` column in Part 2 results.")
    if "post_id" not in trials.columns:
        raise KeyError("Expected `post_id` column in Part 2 results.")
    if "decision" not in trials.columns:
        raise KeyError("Expected `decision` column in Part 2 results.")

    trials["evaluation_mode"] = (
        trials["evaluation_mode"].astype(str).str.lower().str.strip()
    )
    trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()
    trials = trials[trials["evaluation_mode"] == "linked_fate"].copy()
    trials = trials[trials["decision"].isin(_KEEP_REMOVE)].copy()

    post_id = trials["post_id"]
    trials = trials[post_id.notna()].copy()
    trials["post_id"] = trials["post_id"].astype(str).str.strip()
    trials = trials[trials["post_id"] != ""].copy()
    trials = trials[trials["post_id"].str.lower() != "nan"].copy()

    grouped = (
        trials.groupby("post_id", dropna=False)
        .agg(
            n_raters=("decision", "size"),
            n_unique_decisions=("decision", "nunique"),
            keep_count=("decision", lambda s: int((s == "keep").sum())),
            remove_count=("decision", lambda s: int((s == "remove").sum())),
        )
        .reset_index()
    )
    grouped["is_unanimous"] = grouped["n_unique_decisions"] == 1
    grouped = grouped.rename(columns={"post_id": "message_id"})
    return grouped[
        ["message_id", "is_unanimous", "n_raters", "keep_count", "remove_count"]
    ]


def load_posts_with_unanimous() -> pd.DataFrame:
    """Load modal posts and join ``is_unanimous`` from results-full.

    Every modal ``message_id`` must match a linked-fate keep/remove group.
    Rule id: ``UNANIMOUS_RULE_ID``.

    Returns
    -------
    pandas.DataFrame
        Modal label columns plus ``is_unanimous``, ``n_raters``,
        ``keep_count``, ``remove_count``.

    Raises
    ------
    ValueError
        If any modal row lacks a matching results-full group.
    """
    posts = load_keep_remove_posts()
    raw = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
    unanimous = _build_unanimous_frame(raw)
    merged = posts.merge(unanimous, on="message_id", how="left")
    missing_mask = merged["is_unanimous"].isna()
    if bool(missing_mask.any()):
        missing_ids = merged.loc[missing_mask, "message_id"].head(5).tolist()
        raise ValueError(
            "Modal rows missing unanimous join from RESULTS_FULL. "
            f"n_missing={int(missing_mask.sum())} examples={missing_ids}"
        )
    merged["is_unanimous"] = merged["is_unanimous"].astype(bool)
    return merged.reset_index(drop=True)
