"""Sample catalog cells and map columns to the old catalog schema."""

from __future__ import annotations

import pandas as pd


def sample_catalog(pool: pd.DataFrame) -> pd.DataFrame:
    """Sample each stance by toxicity cell and map rows to catalog columns.

    Raises
    ------
    ValueError
        When a cell is short, original text disagrees with post text, or
        ``mirrored_text`` is empty.
    """
    raise NotImplementedError
