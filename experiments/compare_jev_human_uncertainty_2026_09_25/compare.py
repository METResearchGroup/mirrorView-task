"""Join five-labeler remove counts to Jev probabilities.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_compare.py -q
"""

from __future__ import annotations

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    COMPARISON_COLUMNS,
    JEV_BIN_COUNT,
    JEV_BIN_EDGES,
)


def jev_bin_for_probability(probability: float) -> int:
    """Return the 0-based bin for one remove probability.

    Parameters
    ----------
    probability
        Jev ``p_remove`` in the closed range 0 to 1.

    Returns
    -------
    int
        Bin 0 through 4.

    Raises
    ------
    ValueError
        When ``probability`` is missing or outside 0 to 1.
    """
    if pd.isna(probability):
        raise ValueError("p_remove is missing")
    value = float(probability)
    if value < JEV_BIN_EDGES[0] or value > JEV_BIN_EDGES[-1]:
        raise ValueError(f"p_remove out of range: {value}")
    last_bin = JEV_BIN_COUNT - 1
    for index in range(last_bin):
        lower = JEV_BIN_EDGES[index]
        upper = JEV_BIN_EDGES[index + 1]
        if lower <= value < upper:
            return index
    return last_bin


def attach_jev_bin(frame: pd.DataFrame) -> pd.DataFrame:
    """Add ``jev_bin`` from ``p_remove`` without changing the input frame.

    Parameters
    ----------
    frame
        Joined rows that include ``p_remove``.

    Returns
    -------
    pandas.DataFrame
        A copy with ``jev_bin``.
    """
    updated = frame.copy()
    updated["jev_bin"] = [
        jev_bin_for_probability(value) for value in updated["p_remove"]
    ]
    return updated


def attach_difference_score(frame: pd.DataFrame) -> pd.DataFrame:
    """Add human remove count minus Jev bin without changing the input frame.

    Parameters
    ----------
    frame
        Rows that include ``n_remove`` and ``jev_bin``.

    Returns
    -------
    pandas.DataFrame
        A copy with ``difference_score``.
    """
    updated = frame.copy()
    updated["difference_score"] = (
        updated["n_remove"].astype(int) - updated["jev_bin"].astype(int)
    )
    return updated


def join_on_post_id(human: pd.DataFrame, jev: pd.DataFrame) -> pd.DataFrame:
    """Inner-join human remove counts to Jev probabilities on ``post_id``.

    Parameters
    ----------
    human
        Five-labeler counts. One row per ``post_id``.
    jev
        Jev labels. One row per ``post_id``.

    Returns
    -------
    pandas.DataFrame
        Columns ``post_id``, ``n_remove``, and ``p_remove``.

    Raises
    ------
    ValueError
        When ``post_id`` is duplicated in either input.
    KeyError
        When a required column is missing.
    """
    _require_columns(human, ("post_id", "n_remove"))
    _require_columns(jev, ("post_id", "p_remove"))
    if human["post_id"].duplicated().any() or jev["post_id"].duplicated().any():
        raise ValueError("duplicate post_id")
    merged = human.merge(
        jev.loc[:, ["post_id", "p_remove"]],
        on="post_id",
        how="inner",
        validate="one_to_one",
    )
    return merged.loc[:, ["post_id", "n_remove", "p_remove"]].reset_index(drop=True)


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    """Raise KeyError when any named column is absent."""
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise KeyError(f"missing columns: {sorted(missing)}")


def build_comparison_frame(human: pd.DataFrame, jev: pd.DataFrame) -> pd.DataFrame:
    """Return the inner join with a Jev bin and a difference score.

    Parameters
    ----------
    human
        Five-labeler counts.
    jev
        Jev labels.

    Returns
    -------
    pandas.DataFrame
        Columns ``post_id``, ``n_remove``, ``p_remove``, ``jev_bin``, and
        ``difference_score``.
    """
    joined = join_on_post_id(human, jev)
    binned = attach_jev_bin(joined)
    scored = attach_difference_score(binned)
    return scored.loc[:, list(COMPARISON_COLUMNS)].reset_index(drop=True)
