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
    is_unanimous = bool(row["is_unanimous"])
    n_raters = int(row["n_raters"])
    keep_count = int(row["keep_count"])
    remove_count = int(row["remove_count"])
    if keep_count == remove_count:
        raise ValueError(
            f"Cannot assign cell for exact tie: keep={keep_count} "
            f"remove={remove_count} n_raters={n_raters}"
        )
    if is_unanimous and keep_count == n_raters:
        return "unanimous_keep"
    if is_unanimous and remove_count == n_raters:
        return "unanimous_remove"
    if (not is_unanimous) and keep_count > remove_count:
        return "majority_keep"
    if (not is_unanimous) and remove_count > keep_count:
        return "majority_remove"
    raise ValueError(
        f"Cannot assign cell: keep={keep_count} remove={remove_count} "
        f"n_raters={n_raters} is_unanimous={is_unanimous}"
    )


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
    eligible = per_post[per_post["n_raters"] >= _MIN_RATERS].copy()
    eligible = eligible[eligible["keep_count"] != eligible["remove_count"]].copy()
    if eligible.empty:
        counts = {cell: 0 for cell in _CELL_ORDER}
    else:
        labels = eligible.apply(assign_agreement_cell, axis=1)
        value_counts = labels.value_counts()
        counts = {cell: int(value_counts.get(cell, 0)) for cell in _CELL_ORDER}
    return pd.DataFrame(
        {"cell": list(_CELL_ORDER), "count": [counts[cell] for cell in _CELL_ORDER]}
    )


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
    frame = cell_counts.copy()
    total = int(frame["count"].sum())
    if total == 0:
        frame["share"] = 0.0
    else:
        frame["share"] = frame["count"] / total
    return frame


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
