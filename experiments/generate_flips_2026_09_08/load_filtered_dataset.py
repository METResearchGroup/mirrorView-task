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
    """Return the filtered table after checking SHA-256, row count, and columns.

    A matching local cache copy is reused when its SHA-256 matches the pin.

    Parameters
    ----------
    source
        Pinned filtered parquet identity.
    store
        Object store for the source bucket.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        The filtered candidate table with combined stimulus columns.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or columns do not match the pin.
    """
    raise NotImplementedError
