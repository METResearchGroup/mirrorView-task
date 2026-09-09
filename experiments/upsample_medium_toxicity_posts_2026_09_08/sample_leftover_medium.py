"""Sample leftover left-medium and right-medium posts after dropping the 10,200 sample."""

from __future__ import annotations

import pandas as pd

from experiments.upsample_medium_toxicity_posts_2026_09_08.sources import (
    EXPECTED_LEFTOVER_LEFT_MEDIUM,
    EXPECTED_LEFTOVER_RIGHT_MEDIUM,
    LEFT_STANCE,
    LeftoverMediumSample,
    MEDIUM_TOXICITY,
    OUTPUT_COLUMNS,
    RECORD_ID_COLUMN,
    RIGHT_STANCE,
    SAMPLE_SEED,
    SORT_COLUMNS,
    SORT_KIND,
    STANCE_COLUMN,
    TARGET_PER_STANCE,
    TOXICITY_COLUMN,
)


def sample_leftover_medium(
    cleaned: pd.DataFrame,
    sample: pd.DataFrame,
) -> LeftoverMediumSample:
    """Return 1,000 leftover left-medium and 1,000 leftover right-medium posts.

    Parameters
    ----------
    cleaned
        Cleaned combined table.
    sample
        The 10,200 post sample whose ids must be dropped.

    Returns
    -------
    LeftoverMediumSample
        Sampled rows plus leftover medium counts before sampling.

    Raises
    ------
    ValueError
        When leftover medium counts do not match the pinned leftovers, or
        either cell has fewer than 1,000 rows.
    """
    leftover_medium = _leftover_medium_rows(cleaned, sample)
    leftover_left = _stance_rows(leftover_medium, LEFT_STANCE)
    leftover_right = _stance_rows(leftover_medium, RIGHT_STANCE)
    _require_leftover_counts(leftover_left, leftover_right)
    sampled = _concat_sorted(
        [
            _sample_cell(leftover_left, LEFT_STANCE),
            _sample_cell(leftover_right, RIGHT_STANCE),
        ]
    )
    _require_sampled_shape(sampled, sample)
    return LeftoverMediumSample(
        sampled=sampled,
        leftover_left_medium=len(leftover_left),
        leftover_right_medium=len(leftover_right),
    )


def _leftover_medium_rows(cleaned: pd.DataFrame, sample: pd.DataFrame) -> pd.DataFrame:
    sample_ids = set(sample[RECORD_ID_COLUMN].map(str))
    is_unused = ~cleaned[RECORD_ID_COLUMN].map(str).isin(list(sample_ids))
    leftover = cleaned.loc[is_unused]
    return leftover.loc[leftover[TOXICITY_COLUMN] == MEDIUM_TOXICITY]


def _stance_rows(frame: pd.DataFrame, stance: str) -> pd.DataFrame:
    return frame.loc[frame[STANCE_COLUMN] == stance]


def _require_leftover_counts(leftover_left: pd.DataFrame, leftover_right: pd.DataFrame) -> None:
    if len(leftover_left) != EXPECTED_LEFTOVER_LEFT_MEDIUM:
        raise ValueError(
            f"leftover_left_medium={len(leftover_left)} "
            f"expected={EXPECTED_LEFTOVER_LEFT_MEDIUM}"
        )
    if len(leftover_right) != EXPECTED_LEFTOVER_RIGHT_MEDIUM:
        raise ValueError(
            f"leftover_right_medium={len(leftover_right)} "
            f"expected={EXPECTED_LEFTOVER_RIGHT_MEDIUM}"
        )


def _sample_cell(cell: pd.DataFrame, stance: str) -> pd.DataFrame:
    if len(cell) < TARGET_PER_STANCE:
        raise ValueError(
            f"leftover {stance} medium={len(cell)} needed={TARGET_PER_STANCE}"
        )
    return cell.sample(n=TARGET_PER_STANCE, random_state=SAMPLE_SEED, replace=False)


def _concat_sorted(parts: list[pd.DataFrame]) -> pd.DataFrame:
    sampled = pd.concat(parts, ignore_index=True)
    return sampled.sort_values(list(SORT_COLUMNS), kind=SORT_KIND).reset_index(
        drop=True
    )


def _require_sampled_shape(sampled: pd.DataFrame, sample: pd.DataFrame) -> None:
    _require_columns(sampled)
    _require_unique_ids(sampled)
    _require_no_sample_overlap(sampled, sample)
    _require_all_medium(sampled)
    _require_stance_counts(sampled)


def _require_columns(sampled: pd.DataFrame) -> None:
    actual = list(sampled.columns)
    expected = list(OUTPUT_COLUMNS)
    if actual != expected:
        raise ValueError(f"columns={actual} expected={expected}")


def _require_unique_ids(sampled: pd.DataFrame) -> None:
    ids = sampled[RECORD_ID_COLUMN].map(str)
    if ids.nunique() != len(sampled):
        raise ValueError("duplicate record_id in upsample")


def _require_no_sample_overlap(sampled: pd.DataFrame, sample: pd.DataFrame) -> None:
    overlap = set(sampled[RECORD_ID_COLUMN].map(str)) & set(
        sample[RECORD_ID_COLUMN].map(str)
    )
    if overlap:
        raise ValueError(f"upsample overlaps 10200 sample id {sorted(overlap)[0]}")


def _require_all_medium(sampled: pd.DataFrame) -> None:
    if not (sampled[TOXICITY_COLUMN] == MEDIUM_TOXICITY).all():
        raise ValueError("upsample rows must all be medium")


def _require_stance_counts(sampled: pd.DataFrame) -> None:
    left_n = int((sampled[STANCE_COLUMN] == LEFT_STANCE).sum())
    right_n = int((sampled[STANCE_COLUMN] == RIGHT_STANCE).sum())
    if left_n != TARGET_PER_STANCE or right_n != TARGET_PER_STANCE:
        raise ValueError(f"left_medium={left_n} right_medium={right_n}")
