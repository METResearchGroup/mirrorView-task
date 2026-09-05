"""Sample preprocessed rows before they are written.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.preprocessing.sample import sample_records"
"""

from __future__ import annotations

import pandas as pd

MIN_SAMPLE_SIZE = 1


def sample_records(records: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    """Return a random sample of preprocessed rows.

    Parameters
    ----------
    records
        Kept rows after preprocess filters.
    sample_size
        Maximum number of rows to keep. Must be at least 1.

    Returns
    -------
    pandas.DataFrame
        At most ``sample_size`` rows. If ``records`` is shorter, every row
        is returned.

    Raises
    ------
    ValueError
        When ``sample_size`` is less than 1.
    """
    if sample_size < MIN_SAMPLE_SIZE:
        raise ValueError("sample_size must be at least 1")
    if len(records) <= sample_size:
        return records
    return records.sample(n=sample_size).reset_index(drop=True)
