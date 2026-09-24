"""Helpers for combining registered study tables.

Union datasets stack source frames. Stimuli tables also drop duplicate
``post_primary_key`` rows, keeping the first copy.
"""

from __future__ import annotations

import pandas as pd

STIMULI_ID_COLUMN = "post_primary_key"


def concat_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Stack ``frames`` row-wise and align columns.

    Raises
    ------
    ValueError
        If ``frames`` is empty.
    """
    if not frames:
        raise ValueError("Cannot concatenate an empty list of frames.")
    return pd.concat(frames, ignore_index=True, sort=False)


def union_stimuli_frames(
    frames: list[pd.DataFrame],
    *,
    id_column: str = STIMULI_ID_COLUMN,
) -> pd.DataFrame:
    """Stack stimulus tables and keep one row per ``id_column``.

    Duplicate keys keep the first row in source order.

    Raises
    ------
    ValueError
        If ``frames`` is empty.
    KeyError
        If ``id_column`` is missing after the frames are stacked.
    """
    combined = concat_frames(frames)
    if id_column not in combined.columns:
        raise KeyError(f"Expected {id_column!r} column in stimuli frames.")
    return combined.drop_duplicates(subset=[id_column], keep="first").reset_index(
        drop=True
    )
