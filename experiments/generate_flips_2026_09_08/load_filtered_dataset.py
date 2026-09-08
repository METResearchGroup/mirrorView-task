"""Download the pinned filtered parquet and check its hash and row count."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.generate_flips_2026_09_08.sources import FilteredSource


def load_filtered_dataset(
    source: FilteredSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Return the filtered table after checking SHA-256, row count, and columns."""
    raise NotImplementedError
