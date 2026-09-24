"""Assign four-cell agreement labels and vote funnel metrics.

Run from repo root::

    PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_agreement.py -q
"""

from __future__ import annotations

import pandas as pd

_MIN_RATERS = 3
_CELL_ORDER = (
    "unanimous_keep",
    "majority_keep",
    "majority_remove",
    "unanimous_remove",
)
_FUNNEL_METRICS = (
    "posts_after_vote_clean",
    "posts_dropped_lt_3_raters",
    "posts_dropped_ties",
    "posts_remaining",
)


def assign_agreement_cell(row: pd.Series) -> str:
    """Assign one four-cell label to a per-post vote row.

    Parameters
    ----------
    row
        Per-post row with ``n_raters``, ``keep_count``, ``remove_count``,
        and ``is_unanimous``.

    Returns
    -------
    str
        One of the four frozen cell strings in ``_CELL_ORDER``.

    Raises
    ------
    ValueError
        When the row is an exact tie or otherwise invalid for assignment.
    """
    raise NotImplementedError


def build_four_cell_counts(per_post: pd.DataFrame) -> pd.DataFrame:
    """Count posts in each agreement cell after rater and tie filters.

    Parameters
    ----------
    per_post
        Per-post vote frame after Step 1 cleaning.

    Returns
    -------
    pandas.DataFrame
        Two columns ``cell`` and ``count`` in ``_CELL_ORDER``.
    """
    raise NotImplementedError


def build_four_cell_shares(cell_counts: pd.DataFrame) -> pd.DataFrame:
    """Add a share column as each cell count divided by the total.

    Parameters
    ----------
    cell_counts
        Frame with ``cell`` and ``count`` columns.

    Returns
    -------
    pandas.DataFrame
        Input frame with ``share`` equal to ``count / count.sum()``.
    """
    raise NotImplementedError


def build_vote_funnel(per_post: pd.DataFrame) -> pd.DataFrame:
    """Return funnel metrics from per-post vote counts.

    Parameters
    ----------
    per_post
        Per-post vote frame after Step 1 cleaning.

    Returns
    -------
    pandas.DataFrame
        Columns ``metric`` and ``count`` with rows in ``_FUNNEL_METRICS``.
    """
    raise NotImplementedError
