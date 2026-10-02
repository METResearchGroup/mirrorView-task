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
        The returned frame has every input row in its original order, and
        then the sampled rows for each smaller class in the order that class
        first appears. The result has a fresh ``RangeIndex``, the same
        columns, and the same dtypes. An empty table, a table with one class,
        or an already balanced table is an independent copy.

    Raises
    ------
    KeyError
        When ``class_label`` is not a column.
    ValueError
        When the class column contains a null value.
    """
    labels = _class_labels(df, class_label)
    sampled_rows = _rows_for_smaller_classes(df, labels, random_state)
    if not sampled_rows:
        return df.copy().reset_index(drop=True)
    return pd.concat([df, *sampled_rows], ignore_index=True)


def _class_labels(df: pd.DataFrame, class_label: str) -> pd.Series:
    """Return the class column, rejecting null class values.

    Raises
    ------
    KeyError
        When ``class_label`` is not a column.
    ValueError
        When the class column contains a null value.
    """
    labels = df[class_label]
    if bool(labels.isna().any()):
        raise ValueError(f"{class_label} contains null values")
    return labels


def _rows_for_smaller_classes(
    df: pd.DataFrame,
    labels: pd.Series,
    random_state: int,
) -> list[pd.DataFrame]:
    """Sample each class that is smaller than the largest, in the order that class first appears."""
    counts = _counts_by_first_appearance(labels)
    if not counts:
        return []
    largest_count = max(class_count for _, class_count in counts)
    return [
        _sample_class(df, labels, class_value, largest_count - class_count, random_state)
        for class_value, class_count in counts
        if class_count < largest_count
    ]


def _counts_by_first_appearance(labels: pd.Series) -> list[tuple[object, int]]:
    """Return each observed class and its row count, in first-seen order."""
    first_seen = labels.drop_duplicates(keep="first")
    if first_seen.empty:
        return []
    counts = labels.value_counts(sort=False)
    return [(value, int(counts[value])) for value in first_seen.tolist()]


def _sample_class(
    df: pd.DataFrame,
    labels: pd.Series,
    class_value: object,
    deficit: int,
    random_state: int,
) -> pd.DataFrame:
    """Sample ``deficit`` rows from one class, with replacement."""
    class_rows = df.loc[labels == class_value]
    return class_rows.sample(n=deficit, replace=True, random_state=random_state)
