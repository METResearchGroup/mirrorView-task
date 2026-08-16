"""Build shared trial and post analysis frames for ambiguity experiments.

Run from repo root::

    PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/build_analysis_frame.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_STIMULI,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
TRIAL_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "trial_frame.csv"
POST_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "post_frame.csv"

_MIN_RATERS = 3
_KEEP_REMOVE = frozenset({"keep", "remove"})
_TRIAL_COLUMNS = [
    "participant_id",
    "post_id",
    "decision",
    "is_remove",
    "response_time_ms",
    "trial_index",
    "party_group",
    "original_text",
    "mirror_text",
    "char_count",
]
_POST_COLUMNS = [
    "post_id",
    "n_raters",
    "keep_count",
    "remove_count",
    "remove_share",
    "is_unanimous",
    "is_tie",
    "minority_share",
    "vote_entropy",
    "sample_toxicity_type",
    "sampled_stance",
    "original_text",
    "mirror_text",
]
_REQUIRED_STIMULI_COLUMNS = (
    "post_primary_key",
    "sample_toxicity_type",
    "sampled_stance",
)


def _binary_entropy(share: float) -> float:
    """Return binary entropy of a remove share in bits."""
    if share <= 0.0 or share >= 1.0:
        return 0.0
    return float(
        -share * np.log2(share) - (1.0 - share) * np.log2(1.0 - share)
    )


def build_trial_frame(raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build the linked-fate trial analysis frame.

    Parameters
    ----------
    raw
        Optional results-full frame. Loads from the registry when omitted.

    Returns
    -------
    pandas.DataFrame
        One row per linked-fate keep or remove trial.
    """
    raw_frame = (
        raw
        if raw is not None
        else load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
    )
    required = {
        "evaluation_mode",
        "decision",
        "post_id",
        "participant_id",
        "original_text",
        "mirror_text",
        "response_time_ms",
        "trial_index",
    }
    missing = required - set(raw_frame.columns)
    if missing:
        raise KeyError(f"Results missing required columns: {sorted(missing)}")

    trials = raw_frame.copy()
    trials["evaluation_mode"] = (
        trials["evaluation_mode"].astype(str).str.lower().str.strip()
    )
    trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()
    trials = trials[trials["evaluation_mode"] == "linked_fate"].copy()
    trials = trials[trials["decision"].isin(_KEEP_REMOVE)].copy()

    trials = trials[trials["post_id"].notna()].copy()
    trials["post_id"] = trials["post_id"].astype(str).str.strip()
    trials = trials[
        (trials["post_id"] != "") & (trials["post_id"].str.lower() != "nan")
    ].copy()

    trials = trials[trials["participant_id"].notna()].copy()
    trials["participant_id"] = trials["participant_id"].astype(str).str.strip()
    trials = trials[trials["participant_id"] != ""].copy()

    if "party_group" not in trials.columns:
        trials["party_group"] = pd.NA
    trials["party_group"] = trials["party_group"].astype("string")

    trials["is_remove"] = (trials["decision"] == "remove").astype(int)
    trials["response_time_ms"] = pd.to_numeric(
        trials["response_time_ms"], errors="coerce"
    )
    trials["trial_index"] = pd.to_numeric(trials["trial_index"], errors="coerce")
    trials["original_text"] = trials["original_text"].astype(str)
    trials["mirror_text"] = trials["mirror_text"].astype(str)
    trials["char_count"] = trials["original_text"].str.len().astype(int)
    return trials[_TRIAL_COLUMNS].reset_index(drop=True)


def build_post_frame(
    trial_frame: pd.DataFrame,
    stimuli: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate trials into the post frame with ties retained.

    Parameters
    ----------
    trial_frame
        Output of ``build_trial_frame``.
    stimuli
        Optional stimuli frame. Loads from the registry when omitted.

    Returns
    -------
    pandas.DataFrame
        One row per post with at least three raters, including ties.
    """
    stimuli_frame = (
        stimuli
        if stimuli is not None
        else load_dataset(STUDY_PHASE_2_PART_2_STIMULI, low_memory=False)
    )
    missing = [c for c in _REQUIRED_STIMULI_COLUMNS if c not in stimuli_frame.columns]
    if missing:
        raise KeyError(f"Stimuli missing required columns: {missing}")

    grouped = (
        trial_frame.groupby("post_id", dropna=False)
        .agg(
            n_raters=("decision", "size"),
            keep_count=("decision", lambda s: int((s == "keep").sum())),
            remove_count=("decision", lambda s: int((s == "remove").sum())),
            original_text=("original_text", "first"),
            mirror_text=("mirror_text", "first"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["n_raters"] >= _MIN_RATERS].copy()
    grouped["remove_share"] = grouped["remove_count"] / grouped["n_raters"]
    grouped["is_unanimous"] = (
        (grouped["keep_count"] == 0) | (grouped["remove_count"] == 0)
    )
    grouped["is_tie"] = grouped["keep_count"] == grouped["remove_count"]
    grouped["minority_share"] = grouped[["keep_count", "remove_count"]].min(axis=1) / (
        grouped["n_raters"]
    )
    grouped["vote_entropy"] = grouped["remove_share"].map(_binary_entropy)

    stim = stimuli_frame[list(_REQUIRED_STIMULI_COLUMNS)].copy()
    stim["post_primary_key"] = stim["post_primary_key"].astype(str).str.strip()
    merged = grouped.merge(
        stim,
        left_on="post_id",
        right_on="post_primary_key",
        how="left",
        validate="one_to_one",
    )
    missing_mask = merged["post_primary_key"].isna()
    if bool(missing_mask.any()):
        examples = merged.loc[missing_mask, "post_id"].head(5).tolist()
        raise ValueError(
            "Post frame posts missing from stimuli. "
            f"n_missing={int(missing_mask.sum())} examples={examples}"
        )
    return merged[_POST_COLUMNS].reset_index(drop=True)


def write_analysis_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build and write the trial and post frames.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Written trial frame and post frame.
    """
    trials = build_trial_frame()
    posts = build_post_frame(trials)
    TRIAL_FRAME_CSV.parent.mkdir(parents=True, exist_ok=True)
    trials.to_csv(TRIAL_FRAME_CSV, index=False)
    posts.to_csv(POST_FRAME_CSV, index=False)
    return trials, posts


def main() -> None:
    """CLI entry: write frames and print counts."""
    trials, posts = write_analysis_frames()
    print(f"Wrote {TRIAL_FRAME_CSV}")
    print(f"Wrote {POST_FRAME_CSV}")
    print(f"trial_rows {len(trials)}")
    print(f"post_rows_ge3 {len(posts)}")
    print(f"tie_rows {int(posts['is_tie'].sum())}")


if __name__ == "__main__":
    main()
