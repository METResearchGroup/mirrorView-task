"""Load the old catalog, old results, and new sample parquet.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_08.constants import (
    NewSampleSource,
)


def load_old_catalog() -> pd.DataFrame:
    """Load unique ids from the old stimulus catalog.

    Returns
    -------
    pd.DataFrame
        Catalog rows with a unique ``post_primary_key`` per row.

    Raises
    ------
    ValueError
        When the id column is missing or catalog ids are not unique.
    """
    raise NotImplementedError


def load_old_results() -> pd.DataFrame:
    """Load the old study results used to count unique raters.

    Returns
    -------
    pd.DataFrame
        Results rows that include ``post_id`` and ``prolific_id``.

    Raises
    ------
    ValueError
        When ``post_id`` or ``prolific_id`` is missing.
    """
    raise NotImplementedError


def load_new_sample(
    source: NewSampleSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download the pinned new sample parquet and check its identity.

    Parameters
    ----------
    source
        Pinned parquet URI, SHA-256, and row count.
    store
        Object store used only to download the pinned parquet.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        New sample rows with unique ``record_id`` values.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or ``record_id`` uniqueness does not match.
    """
    raise NotImplementedError
