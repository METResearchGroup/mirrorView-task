"""Download the pinned unified upsample parquet and check its hash and row count."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.load_raw_candidate_dataset import (
    load_raw_candidate_dataset,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)
from experiments.generate_flips_for_upsampled_posts_2026_09_08.sources import (
    UnifiedSource,
)


def load_unified_dataset(
    source: UnifiedSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Return the unified table after checking SHA-256, row count, and columns.

    Parameters
    ----------
    source
        Pinned unified parquet identity.
    store
        Object store for the source bucket.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        The unified upsample table.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or columns do not match the pin.
    """
    return load_raw_candidate_dataset(_as_candidate_source(source), store, cache_dir)


def _as_candidate_source(source: UnifiedSource) -> CandidateSource:
    return CandidateSource(
        s3_uri=source.s3_uri,
        sha256=source.sha256,
        expected_row_count=source.expected_row_count,
    )
