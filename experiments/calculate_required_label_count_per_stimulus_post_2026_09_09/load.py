"""Load the old catalog, old results, and new 10,000 row catalog."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.constants import (
    CACHE_FILENAME,
    EMPTY_CELL,
    EXPECTED_OLD_CATALOG_IDS,
    NAN_CELL,
    NEW_ID_COLUMN,
    NewCatalogSource,
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


def load_new_catalog(
    source: NewCatalogSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download the pinned new catalog CSV and check its identity.

    Parameters
    ----------
    source
        Pinned CSV URI, SHA-256, and row count.
    store
        Object store used only to download the pinned CSV.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        New catalog rows with unique ``post_primary_key`` values.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or id uniqueness does not match.
    """
    body = _bytes_matching_pinned_hash(source, store, cache_dir)
    frame = pd.read_csv(io.BytesIO(body))
    _require_column(frame, NEW_ID_COLUMN)
    if len(frame) != source.expected_row_count:
        raise ValueError(
            f"row_count={len(frame)} expected={source.expected_row_count}"
        )
    ids = _stripped_nonempty(frame[NEW_ID_COLUMN])
    _require_unique_id_count(ids, source.expected_row_count, NEW_ID_COLUMN)
    return frame


def _object_key(source: NewCatalogSource) -> str:
    _bucket, key = parse_s3_uri(source.s3_uri)
    return key


def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / CACHE_FILENAME


def _download_source_bytes(source: NewCatalogSource, store: CampaignObjectStore) -> bytes:
    stored = store.get(_object_key(source))
    if stored is None:
        raise FileNotFoundError(source.s3_uri)
    return stored.body


def _bytes_matching_pinned_hash(
    source: NewCatalogSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> bytes:
    cache_path = _cache_path(cache_dir)
    if cache_path.is_file():
        cached = cache_path.read_bytes()
        if sha256_hex(cached) == source.sha256:
            return cached
    body = _download_source_bytes(source, store)
    if sha256_hex(body) != source.sha256:
        raise ValueError(f"SHA-256 mismatch for {source.s3_uri}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(body)
    return body


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
