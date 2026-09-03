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
    """Return up to ``sample_size`` rows from each source-run group."""
    raise NotImplementedError
