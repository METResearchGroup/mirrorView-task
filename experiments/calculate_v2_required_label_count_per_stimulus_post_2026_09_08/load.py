"""Load the old catalog, old results, and new 10,000 row catalog."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.calculate_v2_required_label_count_per_stimulus_post_2026_09_08.constants import (
    NewCatalogSource,
)


def load_old_catalog() -> pd.DataFrame:
    """Load unique ids from the old stimulus catalog."""
    raise NotImplementedError


def load_old_results() -> pd.DataFrame:
    """Load the old study results used to count unique raters."""
    raise NotImplementedError


def load_new_catalog(
    source: NewCatalogSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download the pinned new catalog CSV and check its identity."""
    raise NotImplementedError
