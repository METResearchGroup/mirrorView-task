"""Load the old catalog, old results, and new sample parquet.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_08.constants import (
    EMPTY_CELL,
    EXPECTED_OLD_CATALOG_IDS,
    NAN_CELL,
    NewSampleSource,
    OLD_ID_COLUMN,
    OLD_RESULTS_DATASET,
    OLD_STIMULI_DATASET,
    RATER_COLUMN,
    RESULTS_ID_COLUMN,
)
from shared.data.dataloader import load_dataset


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
    catalog = load_dataset(OLD_STIMULI_DATASET)
    _require_column(catalog, OLD_ID_COLUMN)
    ids = _stripped_nonempty(catalog[OLD_ID_COLUMN])
    _require_unique_id_count(ids, EXPECTED_OLD_CATALOG_IDS, OLD_ID_COLUMN)
    return pd.DataFrame({OLD_ID_COLUMN: ids.to_numpy()})


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
    results = load_dataset(OLD_RESULTS_DATASET)
    _require_column(results, RESULTS_ID_COLUMN)
    _require_column(results, RATER_COLUMN)
    return results


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


def _require_column(frame: pd.DataFrame, column_name: str) -> None:
    if column_name not in frame.columns:
        raise ValueError(f"missing column {column_name}")


def _stripped_nonempty(values: pd.Series) -> pd.Series:
    stripped = values.fillna(EMPTY_CELL).astype(str).str.strip()
    nonempty = (stripped != EMPTY_CELL) & (stripped.str.lower() != NAN_CELL)
    return stripped.loc[nonempty]


def _require_unique_id_count(
    ids: pd.Series, expected_count: int, column_name: str
) -> None:
    unique_count = int(ids.nunique())
    if unique_count != len(ids):
        raise ValueError(f"duplicate {column_name}")
    if unique_count != expected_count:
        raise ValueError(f"{column_name} count={unique_count} expected={expected_count}")
