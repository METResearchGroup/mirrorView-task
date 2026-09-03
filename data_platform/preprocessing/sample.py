"""Sample preprocessed rows before write.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.preprocessing.sample import sample_rows"
"""

from __future__ import annotations

import pandas as pd

MIN_SAMPLE_SIZE = 1


def sample_rows(
    records: pd.DataFrame,
    sample_size: int,
    sample_seed: int,
) -> pd.DataFrame:
    """Return a repeatable sample of preprocessed rows.

    Parameters
    ----------
    records
        Kept rows after preprocess filters.
    sample_size
        Maximum number of rows to keep. Must be at least 1.
    sample_seed
        Seed for Algorithm R.

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
    raise NotImplementedError
