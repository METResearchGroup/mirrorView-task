"""Download the pinned catalog and build the shuffled presentation table.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    CatalogSource,
)


def load_catalog(
    source: CatalogSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download the pinned catalog CSV and validate its identity."""
    raise NotImplementedError


def build_presentation_table(catalog: pd.DataFrame) -> pd.DataFrame:
    """Shuffle each original and mirror pair once and build presentation rows."""
    raise NotImplementedError


def load_presentations(store: CampaignObjectStore) -> pd.DataFrame:
    """Load the shared presentation parquet from S3."""
    raise NotImplementedError


def smoke_presentations(presentations: pd.DataFrame) -> pd.DataFrame:
    """Return the first smoke rows after sorting by post_primary_key."""
    raise NotImplementedError
