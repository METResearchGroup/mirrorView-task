"""Download the pinned combined parquet and check its hash and row count."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)


def load_raw_candidate_dataset(
    source: CandidateSource,
    store: CampaignObjectStore | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Return the candidate table after checking SHA-256 and row count."""
    raise NotImplementedError
