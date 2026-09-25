"""Join five-labeler remove counts to Jev probabilities.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_compare.py -q
"""

from __future__ import annotations

import pandas as pd


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
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError


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
    return scored
