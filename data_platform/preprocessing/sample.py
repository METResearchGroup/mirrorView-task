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
    raise NotImplementedError
