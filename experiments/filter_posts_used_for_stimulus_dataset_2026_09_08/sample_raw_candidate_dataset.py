"""Sample up to 1700 posts in each political stance by toxicity cell."""

from __future__ import annotations

import pandas as pd

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CANDIDATE_SORT_COLUMNS,
    CANDIDATE_STANCE_ROWS,
    CANDIDATE_TOXICITY_COLUMNS,
    LEFT_STANCE,
    MEDIUM_TOXICITY,
    RECORD_ID_COLUMN,
    RIGHT_STANCE,
    SAMPLE_SEED,
    STANCE_COLUMN,
    TARGET_PER_CELL,
    TOXICITY_COLUMN,
)


def sample_raw_candidate_dataset(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Return the sampled table with even left and right totals.

    Cells with fewer than ``TARGET_PER_CELL`` cleaned posts keep every row.
    Extra posts then come from unused right-medium rows until the right
    total matches the left total. Sampling uses ``SAMPLE_SEED`` without
    replacement.

    Parameters
    ----------
    cleaned
        Candidate rows after previously used and duplicate drops.

    Returns
    -------
    pd.DataFrame
        Sampled table sorted by integration, dataset id, and source record id.

    Raises
    ------
    ValueError
        When a stance by toxicity cell is empty, or right-medium cannot
        fill the left/right gap.
    """
    parts = [_sample_one_cell(cleaned, stance, tier) for stance, tier in _cells()]
    sampled = pd.concat(parts, ignore_index=True)
    extra = _extra_right_medium(cleaned, sampled)
    if extra.empty:
        return _sort_sampled(sampled)
    return _sort_sampled(pd.concat([sampled, extra], ignore_index=True))


def _cells() -> tuple[tuple[str, str], ...]:
    return tuple(
        (stance, tier)
        for stance in CANDIDATE_STANCE_ROWS
        for tier in CANDIDATE_TOXICITY_COLUMNS
    )


def _sample_one_cell(
    cleaned: pd.DataFrame,
    stance: str,
    tier: str,
) -> pd.DataFrame:
    cell = cleaned.loc[_cell_mask(cleaned, stance, tier)]
    if cell.empty:
        raise ValueError(f"empty cell stance={stance} tier={tier}")
    if len(cell) <= TARGET_PER_CELL:
        return cell.reset_index(drop=True)
    return cell.sample(n=TARGET_PER_CELL, random_state=SAMPLE_SEED, replace=False)


def _extra_right_medium(
    cleaned: pd.DataFrame,
    sampled: pd.DataFrame,
) -> pd.DataFrame:
    needed = _right_gap(sampled)
    if needed <= 0:
        return sampled.iloc[:0].copy()
    unused = _unused_right_medium(cleaned, sampled)
    if len(unused) < needed:
        raise ValueError(f"right medium unused={len(unused)} needed={needed}")
    return unused.sample(n=needed, random_state=SAMPLE_SEED, replace=False)


def _right_gap(sampled: pd.DataFrame) -> int:
    left_n = int((sampled[STANCE_COLUMN] == LEFT_STANCE).sum())
    right_n = int((sampled[STANCE_COLUMN] == RIGHT_STANCE).sum())
    return left_n - right_n


def _unused_right_medium(
    cleaned: pd.DataFrame,
    sampled: pd.DataFrame,
) -> pd.DataFrame:
    used_ids = set(sampled[RECORD_ID_COLUMN].map(str))
    pool = cleaned.loc[_cell_mask(cleaned, RIGHT_STANCE, MEDIUM_TOXICITY)]
    is_unused = ~pool[RECORD_ID_COLUMN].map(str).isin(list(used_ids))
    return pool.loc[is_unused]


def _cell_mask(cleaned: pd.DataFrame, stance: str, tier: str) -> pd.Series:
    return (cleaned[STANCE_COLUMN] == stance) & (cleaned[TOXICITY_COLUMN] == tier)


def _sort_sampled(sampled: pd.DataFrame) -> pd.DataFrame:
    return sampled.sort_values(
        list(CANDIDATE_SORT_COLUMNS),
        kind="mergesort",
    ).reset_index(drop=True)
