"""Load remaining labels and join them to catalog cell membership.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.constants import (
    NewCatalogSource,
)


def load_remaining_labels(
    path: str, store: CampaignObjectStore, cache_dir: Path
) -> pd.DataFrame:
    """Load remaining labels from a local CSV or an S3 URI.

    Parameters
    ----------
    path
        Local path or S3 URI. The pinned remaining-labels URI is hash-checked.
    store
        Object store used only for S3 remaining-label files.
    cache_dir
        Directory for a local copy of downloaded bytes.

    Returns
    -------
    pd.DataFrame
        Remaining-label rows with unique ids and remaining counts greater than 0.

    Raises
    ------
    FileNotFoundError
        When the source object or local file is missing.
    ValueError
        When columns, uniqueness, remaining counts, or the pinned hash do not match.
    """
    raise NotImplementedError


def load_old_catalog_with_cells() -> pd.DataFrame:
    """Load old catalog rows with stance and toxicity columns.

    Returns
    -------
    pd.DataFrame
        Catalog rows with ``post_primary_key``, ``sampled_stance``, and
        ``sample_toxicity_type``.

    Raises
    ------
    ValueError
        When a required column is missing.
    """
    raise NotImplementedError


def load_new_catalog_with_cells(
    source: NewCatalogSource, store: CampaignObjectStore, cache_dir: Path
) -> pd.DataFrame:
    """Download the pinned new catalog and keep cell columns.

    Parameters
    ----------
    source
        Pinned catalog URI, SHA-256, and row count.
    store
        Object store used only to download the pinned catalog.
    cache_dir
        Directory for a local copy of the catalog bytes.

    Returns
    -------
    pd.DataFrame
        Catalog rows with ``post_primary_key``, ``sampled_stance``, and
        ``sample_toxicity_type``.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or required columns do not match.
    """
    raise NotImplementedError


def join_remaining_to_catalogs(
    remaining: pd.DataFrame, old_catalog: pd.DataFrame, new_catalog: pd.DataFrame
) -> pd.DataFrame:
    """Join remaining label ids to exactly one catalog cell.

    Parameters
    ----------
    remaining
        Remaining-label table.
    old_catalog
        Old catalog with cell columns.
    new_catalog
        New catalog with cell columns.

    Returns
    -------
    pd.DataFrame
        One row per remaining id with cell membership.

    Raises
    ------
    ValueError
        When an id is in neither catalog or in both catalogs.
    """
    raise NotImplementedError


def write_shuffled_stimuli(joined: pd.DataFrame, experiment_dir: Path) -> Path:
    """Write the seed-0 shuffled joined table locally.

    Parameters
    ----------
    joined
        Joined remaining-label rows already shuffled.
    experiment_dir
        Folder that receives ``shuffled_stimuli.csv``.

    Returns
    -------
    Path
        Path of the written file.
    """
    raise NotImplementedError
