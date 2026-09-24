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


def assign_agreement_cell(row: pd.Series) -> str:
    """Assign one four-cell label to a per-post vote row."""
    raise NotImplementedError


def build_four_cell_counts(per_post: pd.DataFrame) -> pd.DataFrame:
    """Count posts in each agreement cell after rater and tie filters."""
    raise NotImplementedError


def build_four_cell_shares(cell_counts: pd.DataFrame) -> pd.DataFrame:
    """Add a share column as each cell count divided by the total."""
    raise NotImplementedError


def build_vote_funnel(per_post: pd.DataFrame) -> pd.DataFrame:
    """Return funnel metrics from per-post vote counts."""
    raise NotImplementedError
