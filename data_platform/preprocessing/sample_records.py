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
    raise NotImplementedError
