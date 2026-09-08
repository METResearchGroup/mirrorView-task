"""Download a pinned curated parquet and check its hash and row count."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.combine_data_into_stimulus_set_2026_09_08.sources import CuratedSource


def load_curated_source(
    source: CuratedSource,
    store: CampaignObjectStore | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Return one curated table after checking SHA-256 and row count.

    Parameters
    ----------
    source
        Pinned curated parquet identity.
    store
        Object store used to download the source. None builds a store for the
        source bucket.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        The curated table.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256 or row count does not match the pin.
    """
    raise NotImplementedError
