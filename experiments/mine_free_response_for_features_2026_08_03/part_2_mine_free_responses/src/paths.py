"""Part 2 paths, reflection loader, and low/high Likert split helpers.

Run from repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src import paths
    df = paths.load_reflection_feedback()
    low_df, high_df = paths.split_by_likert_group(df)
    print(len(df), len(low_df), len(high_df))
    "
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK
from shared.feature_discovery.llm_based.paths import latest_timestamp_subdir

PART2_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = (
    "participant_id",
    "phase1_pair_reflection_text",
    "phase1_pair_influence_rating",
)
OPTIONAL_COLUMNS = ("prolific_id",)
LIKERT_LOW_THRESHOLD = 4
TEXT_COLUMN = "phase1_pair_reflection_text"
RATING_COLUMN = "phase1_pair_influence_rating"


class LikertGroup(str, Enum):
    """Allowed Likert-group labels for stage output paths."""

    LOW = "low"
    HIGH = "high"


def validate_likert_group(likert_group: str) -> LikertGroup:
    """Return the LikertGroup enum for a string group label.

    Parameters
    ----------
    likert_group
        Must be exactly ``low`` or ``high``.

    Returns
    -------
    LikertGroup
        Parsed enum value.

    Raises
    ------
    ValueError
        When ``likert_group`` is not low or high.
    """
    try:
        return LikertGroup(likert_group)
    except ValueError as exc:
        raise ValueError(
            f"likert_group must be 'low' or 'high', got {likert_group!r}"
        ) from exc


def stage1_root(likert_group: str) -> Path:
    """Return Stage-1 generated-features root for one Likert group."""
    group = validate_likert_group(likert_group)
    return PART2_ROOT / "outputs" / "generated_features" / group.value


def stage2_root(likert_group: str) -> Path:
    """Return Stage-2 generated-embeddings root for one Likert group."""
    group = validate_likert_group(likert_group)
    return PART2_ROOT / "outputs" / "generated_embeddings" / group.value


def stage3_root(likert_group: str) -> Path:
    """Return Stage-3 clusters root for one Likert group."""
    group = validate_likert_group(likert_group)
    return PART2_ROOT / "outputs" / "clusters" / group.value


def stage4_root(likert_group: str) -> Path:
    """Return Stage-4 generated-labels root for one Likert group."""
    group = validate_likert_group(likert_group)
    return PART2_ROOT / "outputs" / "generated_labels" / group.value


def _assert_required_columns(frame: pd.DataFrame) -> None:
    """Raise KeyError when required columns are missing."""
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise KeyError(
            f"Reflection feedback missing columns: {sorted(missing)}"
        )


def _filter_usable_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep rows with non-null numeric rating and non-empty reflection text."""
    out = frame.copy()
    out[RATING_COLUMN] = pd.to_numeric(out[RATING_COLUMN], errors="coerce")
    text = out[TEXT_COLUMN].fillna("").astype(str).str.strip()
    mask = out[RATING_COLUMN].notna() & (text != "")
    return out.loc[mask].reset_index(drop=True)


def load_reflection_feedback() -> pd.DataFrame:
    """Load usable Phase 2 Part 2 user reflection feedback rows.

    Returns
    -------
    pd.DataFrame
        Rows with required columns, non-null Likert rating, and non-empty text.
    """
    frame = load_dataset(
        STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK,
        low_memory=False,
    )
    _assert_required_columns(frame)
    keep_cols = list(REQUIRED_COLUMNS)
    for column in OPTIONAL_COLUMNS:
        if column in frame.columns:
            keep_cols.append(column)
    usable = _filter_usable_rows(frame[keep_cols])
    return usable


def split_by_likert_group(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split reflection feedback into (low_df, high_df).

    Parameters
    ----------
    df
        Frame with ``phase1_pair_influence_rating``.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Low (rating < 4) then high (rating >= 4) rows.
    """
    _assert_required_columns(df)
    ratings = pd.to_numeric(df[RATING_COLUMN], errors="coerce")
    low_df = df.loc[ratings < LIKERT_LOW_THRESHOLD].reset_index(drop=True)
    high_df = df.loc[ratings >= LIKERT_LOW_THRESHOLD].reset_index(drop=True)
    return low_df, high_df


def group_frame_for_likert(
    df: pd.DataFrame,
    likert_group: str,
) -> pd.DataFrame:
    """Return the low or high subset of a reflection feedback frame.

    Parameters
    ----------
    df
        Full usable reflection feedback frame.
    likert_group
        ``low`` or ``high``.

    Returns
    -------
    pd.DataFrame
        Subset for the requested group.
    """
    group = validate_likert_group(likert_group)
    low_df, high_df = split_by_likert_group(df)
    frames = {
        LikertGroup.LOW: low_df,
        LikertGroup.HIGH: high_df,
    }
    return frames[group]


__all__ = [
    "LikertGroup",
    "PART2_ROOT",
    "group_frame_for_likert",
    "latest_timestamp_subdir",
    "load_reflection_feedback",
    "split_by_likert_group",
    "stage1_root",
    "stage2_root",
    "stage3_root",
    "stage4_root",
    "validate_likert_group",
]
