"""Balance a DataFrame so each class has as many rows as the largest class.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.utils.upsample import upsample_df"
"""

from __future__ import annotations

import pandas as pd


def upsample_df(
    df: pd.DataFrame,
    class_label: str,
    *,
    random_state: int = 1,
) -> pd.DataFrame:
    """Return a copy where every class has as many rows as the largest class.

    Parameters
    ----------
    df
        Input table. The function does not modify it.
    class_label
        Column name that holds the class value.
    random_state
        Seed used when sampling smaller classes with replacement.

    Returns
    -------
    pandas.DataFrame
        Every input row, in its original order, followed by sampled rows for
        each smaller class in the order that class first appears. The result
        has a fresh ``RangeIndex``, the same columns, and the same dtypes.
        An empty table, a one-class table, or an already balanced table is
        an independent copy.

    Raises
    ------
    KeyError
        When ``class_label`` is not a column.
    ValueError
        When the class column contains a null value.
    """
    ...
