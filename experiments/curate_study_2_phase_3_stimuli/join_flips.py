"""Inner-join posts to successful flips and count stance by toxicity cells."""

from __future__ import annotations

import pandas as pd

from experiments.combine_data_into_stimulus_set_2026_09_08.crosstab import (
    stance_by_toxicity,
)
from experiments.curate_study_2_phase_3_stimuli.sources import (
    CELL_TARGET,
    EMPTY_CELL,
    FLIP_KEEP_COLUMNS,
    JoinedFlipPool,
    MIRRORED_TEXT_COLUMN,
    ORIGINAL_TEXT_COLUMN,
    RECORD_ID_COLUMN,
    STANCE_VALUES,
    TEXT_COLUMN,
    TOXICITY_TIERS,
)


def join_posts_to_flips(
    sample_posts: pd.DataFrame,
    sample_flips: pd.DataFrame,
    unified_posts: pd.DataFrame,
    unified_flips: pd.DataFrame,
) -> JoinedFlipPool:
    """Inner-join each post table to its flips and concatenate the two pieces.

    Toxicity comes from the original post table. The 300 promoted posts count
    as high.

    Parameters
    ----------
    sample_posts
        The 10,200 post sample.
    sample_flips
        Successful flips for that sample.
    unified_posts
        The unified 2,300 post upsample.
    unified_flips
        Successful flips for that upsample.

    Returns
    -------
    JoinedFlipPool
        Concatenated posts that have a flip.

    Raises
    ------
    ValueError
        When a ``record_id`` is duplicated, the same ``record_id`` appears in
        both joined pieces, original text does not match post text, or
        ``mirrored_text`` is empty.
    """
    sample_joined = _inner_join(sample_posts, sample_flips)
    unified_joined = _inner_join(unified_posts, unified_flips)
    _require_no_id_overlap(sample_joined, unified_joined)
    rows = pd.concat([sample_joined, unified_joined], ignore_index=True)
    return JoinedFlipPool(
        rows=rows,
        sample_joined_rows=len(sample_joined),
        upsample_joined_rows=len(unified_joined),
    )


def available_cell_counts(pool: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Return political stance by toxicity counts for posts that have a flip."""
    return stance_by_toxicity(pool)


def cells_meet_targets(available: dict[str, dict[str, int]]) -> bool:
    """Return True when every stance by toxicity cell meets its catalog target."""
    for stance in STANCE_VALUES:
        for tier in TOXICITY_TIERS:
            if int(available.get(stance, {}).get(tier, 0)) < CELL_TARGET[stance][tier]:
                return False
    return True


def _inner_join(posts: pd.DataFrame, flips: pd.DataFrame) -> pd.DataFrame:
    flip_rows = flips.loc[:, list(FLIP_KEEP_COLUMNS)]
    _require_unique_record_ids(posts)
    _require_unique_record_ids(flip_rows)
    joined = posts.merge(flip_rows, on=RECORD_ID_COLUMN, how="inner")
    _require_text_match(joined)
    _require_mirrored_text(joined)
    return joined


def _require_unique_record_ids(frame: pd.DataFrame) -> None:
    ids = frame[RECORD_ID_COLUMN].map(str)
    if ids.nunique() != len(frame):
        raise ValueError("duplicate record_id")


def _require_text_match(joined: pd.DataFrame) -> None:
    post_text = joined[TEXT_COLUMN].astype(str)
    original = joined[ORIGINAL_TEXT_COLUMN].astype(str)
    mismatch = post_text != original
    if mismatch.any():
        record_id = joined.loc[mismatch, RECORD_ID_COLUMN].iloc[0]
        raise ValueError(f"original_text does not match post text for {record_id}")


def _require_mirrored_text(joined: pd.DataFrame) -> None:
    mirrored = joined[MIRRORED_TEXT_COLUMN].fillna(EMPTY_CELL).astype(str).str.strip()
    if (mirrored == EMPTY_CELL).any():
        raise ValueError("empty mirrored_text")


def _require_no_id_overlap(sample_joined: pd.DataFrame, unified_joined: pd.DataFrame) -> None:
    overlap = set(sample_joined[RECORD_ID_COLUMN].map(str)) & set(
        unified_joined[RECORD_ID_COLUMN].map(str)
    )
    if overlap:
        raise ValueError(f"record_id in both join pieces {sorted(overlap)[0]}")
