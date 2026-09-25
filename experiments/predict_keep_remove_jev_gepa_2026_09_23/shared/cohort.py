"""Build cohort A labels from Phase 2 Part 3 moderation trials.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py --write-counts
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

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
STUDY_PART_PART2 = "part2"
STUDY_PART_PART3 = "part3"
PART3_MARKER_COLUMN = "attention_check_passed"
_REQUIRED_STUDY_PART_COLUMN = "study_part"
_REQUIRED_FILTER_COLUMNS = ("trial_type", "post_id", "decision")
_REQUIRED_AGG_COLUMNS = (
    "post_id",
    "original_text",
    "mirror_text",
    "decision",
    "sampled_stance",
    "sample_toxicity_type",
)


class CohortSource(str, Enum):
    """Which raw results table feeds cohort construction."""

    PART3 = "part3"
    UNION = "union"


@dataclass(frozen=True)
class UnionStrataExclusionReport:
    """Summary of union-only stance and toxicity filtering."""

    n_excluded: int
    excluded_keep: int
    excluded_remove: int
    n_stance_disagreements: int
    n_toxicity_disagreements: int


def load_raw_results(source: CohortSource) -> pd.DataFrame:
    """Load the registry CSV for ``source``.

    Parameters
    ----------
    source
        Part 3-only or Part 2 plus Part 3 union table.

    Returns
    -------
    pandas.DataFrame
        Raw session export.
    """
    from shared.data.dataloader import load_dataset

    return load_dataset(registry_dataset_name(source), low_memory=False)


def registry_dataset_name(source: CohortSource) -> str:
    """Return the registry constant for ``source``."""
    if source is CohortSource.PART3:
        return "STUDY_PHASE_2_PART_3_RESULTS_FULL"
    return "STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL"


def derive_study_part(frame: pd.DataFrame) -> pd.Series:
    """Return part2 or part3 from ``attention_check_passed`` on union rows.

    Part 3 session rows populate ``attention_check_passed``; Part 2 rows leave it
    empty. When the column is absent (Part 3-only export), every row is Part 3.
    """
    if PART3_MARKER_COLUMN not in frame.columns:
        return pd.Series(STUDY_PART_PART3, index=frame.index, dtype="object")
    marker = frame[PART3_MARKER_COLUMN].fillna("").astype(str).str.strip()
    return pd.Series(
        np.where(marker.ne(""), STUDY_PART_PART3, STUDY_PART_PART2),
        index=frame.index,
        dtype="object",
    )


def attach_study_part(trials: pd.DataFrame) -> pd.DataFrame:
    """Add ``study_part`` to scored trial rows."""
    tagged = trials.copy()
    tagged[_REQUIRED_STUDY_PART_COLUMN] = derive_study_part(tagged)
    return tagged


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
    if _REQUIRED_STUDY_PART_COLUMN not in trials.columns:
        trials = attach_study_part(trials)
    tagged = trials.assign(
        _keep=trials["decision"].eq(DECISION_KEEP),
        _remove=trials["decision"].eq(DECISION_REMOVE),
        _part2=trials[_REQUIRED_STUDY_PART_COLUMN].eq(STUDY_PART_PART2),
        _part3=trials[_REQUIRED_STUDY_PART_COLUMN].eq(STUDY_PART_PART3),
    )
    counts = tagged.groupby("post_id", as_index=False).agg(
        n_raters=("decision", "size"),
        n_keep=("_keep", "sum"),
        n_remove=("_remove", "sum"),
        n_raters_part2=("_part2", "sum"),
        n_raters_part3=("_part3", "sum"),
        original_text=("original_text", "first"),
        mirror_text=("mirror_text", "first"),
        sampled_stance=("sampled_stance", "first"),
        sample_toxicity_type=("sample_toxicity_type", "first"),
    )
    counts["n_keep"] = counts["n_keep"].astype(int)
    counts["n_remove"] = counts["n_remove"].astype(int)
    counts["n_raters_part2"] = counts["n_raters_part2"].astype(int)
    counts["n_raters_part3"] = counts["n_raters_part3"].astype(int)
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


def _non_empty_values(series: pd.Series) -> list[str]:
    cleaned = series.fillna("").astype(str).str.strip()
    return sorted({value for value in cleaned if value})


def _first_non_empty_value(series: pd.Series) -> str:
    cleaned = series.fillna("").astype(str).str.strip()
    for value in cleaned:
        if value:
            return value
    return ""


def _part3_preferred_field(trials: pd.DataFrame, column: str) -> str:
    part3_rows = trials.loc[trials[_REQUIRED_STUDY_PART_COLUMN].eq(STUDY_PART_PART3)]
    part3_value = _first_non_empty_value(part3_rows[column])
    if part3_value:
        return part3_value
    return _first_non_empty_value(trials[column])


def resolve_post_strata_fields(trials: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Return per-post stance and toxicity with Part 3 tie-breaks.

    Returns
    -------
    tuple[pandas.DataFrame, int, int]
        One row per ``post_id`` plus stance and toxicity disagreement counts.
    """
    if _REQUIRED_STUDY_PART_COLUMN not in trials.columns:
        trials = attach_study_part(trials)
    rows: list[dict[str, object]] = []
    stance_disagreements = 0
    toxicity_disagreements = 0
    for post_id, group in trials.groupby("post_id"):
        stance_values = _non_empty_values(group["sampled_stance"])
        toxicity_values = _non_empty_values(group["sample_toxicity_type"])
        if len(stance_values) > 1:
            stance_disagreements += 1
        if len(toxicity_values) > 1:
            toxicity_disagreements += 1
        rows.append(
            {
                "post_id": post_id,
                "sampled_stance": _part3_preferred_field(group, "sampled_stance"),
                "sample_toxicity_type": _part3_preferred_field(
                    group,
                    "sample_toxicity_type",
                ),
            }
        )
    return pd.DataFrame(rows), stance_disagreements, toxicity_disagreements


def apply_union_strata_exclusion(
    cohort: pd.DataFrame,
    trials: pd.DataFrame,
) -> tuple[pd.DataFrame, UnionStrataExclusionReport]:
    """Drop union cohort posts missing stance or toxicity after Part 3 resolution."""
    strata, stance_disagreements, toxicity_disagreements = resolve_post_strata_fields(
        trials
    )
    merged = cohort.merge(strata, on="post_id", suffixes=("", "_resolved"))
    merged["sampled_stance"] = merged["sampled_stance_resolved"]
    merged["sample_toxicity_type"] = merged["sample_toxicity_type_resolved"]
    merged = merged.drop(
        columns=["sampled_stance_resolved", "sample_toxicity_type_resolved"]
    )
    missing = merged["sampled_stance"].eq("") | merged["sample_toxicity_type"].eq("")
    excluded = merged.loc[missing]
    kept = merged.loc[~missing].copy()
    report = UnionStrataExclusionReport(
        n_excluded=len(excluded),
        excluded_keep=int((excluded["label"] == 0).sum()),
        excluded_remove=int((excluded["label"] == 1).sum()),
        n_stance_disagreements=stance_disagreements,
        n_toxicity_disagreements=toxicity_disagreements,
    )
    return kept, report


def attach_part3_overlap_flags(
    cohort: pd.DataFrame,
    frozen_part3: pd.DataFrame,
) -> pd.DataFrame:
    """Add ``in_part3_cohort_a`` and ``label_changed_vs_part3`` columns."""
    tagged = cohort.copy()
    frozen = frozen_part3[["post_id", "label"]].copy()
    frozen["post_id"] = frozen["post_id"].astype(str)
    frozen = frozen.rename(columns={"label": "_frozen_label"})
    tagged["post_id"] = tagged["post_id"].astype(str)
    merged = tagged.merge(frozen, on="post_id", how="left")
    merged["in_part3_cohort_a"] = merged["_frozen_label"].notna()
    merged["label_changed_vs_part3"] = merged["in_part3_cohort_a"] & (
        merged["label"] != merged["_frozen_label"]
    )
    return merged.drop(columns=["_frozen_label"])


def build_scored_trials(source: CohortSource) -> pd.DataFrame:
    """Filter, dedupe, and tag trials for ``source``."""
    raw = load_raw_results(source)
    trials = filter_scored_trials(raw)
    trials = dedupe_participant_post(trials)
    return attach_study_part(trials)


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
