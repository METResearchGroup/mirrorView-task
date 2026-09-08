"""Download a pinned curated parquet and check its hash and row count."""

from __future__ import annotations

import pandas as pd


def load_curated_source(source) -> pd.DataFrame:
    """Return one curated table after checking SHA-256 and row count."""
    raise NotImplementedError
