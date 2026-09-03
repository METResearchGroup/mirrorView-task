"""Sample kept preprocess rows per source raw run before writing."""

from __future__ import annotations

import pandas as pd

SOURCE_RAW_RUN_COLUMN = "source_raw_run"
MIN_SAMPLE_SIZE = 1


def sample_records_per_source_run(
    records: pd.DataFrame,
    sample_size: int,
    sample_seed: int,
    source_column: str,
) -> pd.DataFrame:
    """Return up to ``sample_size`` rows from each source-run group.

    Groups with ``sample_size`` or fewer rows are kept in the current order.
    Larger groups are sampled with ``random_state=sample_seed``. The input
    frame is not modified.

    Parameters
    ----------
    records
        Filtered preprocess rows that still include ``source_column``.
    sample_size
        Maximum rows to keep per source run. Must be at least 1.
    sample_seed
        Seed passed to pandas ``sample`` for oversized groups.
    source_column
        Column that names the raw run directory.

    Returns
    -------
    pd.DataFrame
        Concatenated per-run samples with a reset index.

    Raises
    ------
    ValueError
        When ``sample_size`` is less than 1.
    KeyError
        When ``source_column`` is missing from ``records``.
    """
    if sample_size < MIN_SAMPLE_SIZE:
        raise ValueError("sample_size must be at least 1")
    if source_column not in records.columns:
        raise KeyError(source_column)
    sampled_groups: list[pd.DataFrame] = []
    for run_name in sorted(records[source_column].astype(str).unique()):
        group = records.loc[records[source_column] == run_name]
        if len(group) <= sample_size:
            sampled_groups.append(group)
            continue
        sampled_groups.append(group.sample(n=sample_size, random_state=sample_seed))
    if not sampled_groups:
        return records.iloc[0:0].copy().reset_index(drop=True)
    return pd.concat(sampled_groups, ignore_index=True)
