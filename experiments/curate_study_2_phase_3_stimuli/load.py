"""Download pinned post tables and flip parquets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.curate_study_2_phase_3_stimuli.sources import (
    FlipSource,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)


def load_posts(
    source: CandidateSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download a pinned combined-column parquet and check its identity."""
    raise NotImplementedError


def load_flips(
    source: FlipSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download a pinned flips parquet and check its identity."""
    raise NotImplementedError
