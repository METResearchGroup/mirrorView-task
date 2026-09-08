"""Download the pinned filtered parquet and check its hash and row count."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.combine_data_into_stimulus_set_2026_09_08.sources import (
    COMBINED_COLUMNS,
)
from experiments.generate_flips_2026_09_08.sources import (
    CACHE_FILENAME,
    FilteredSource,
)
from lib.constants import REPO_ROOT

EXPERIMENT_DIR = REPO_ROOT / "experiments" / "generate_flips_2026_09_08"
DEFAULT_CACHE_DIR = EXPERIMENT_DIR / "cache"


def load_filtered_dataset(
    source: FilteredSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Return the filtered table after checking SHA-256, row count, and columns.

    A matching local cache copy is reused when its SHA-256 matches the pin.

    Parameters
    ----------
    source
        Pinned filtered parquet identity.
    store
        Object store for the source bucket.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        The filtered candidate table with combined stimulus columns.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or columns do not match the pin.
    """
    body = _bytes_matching_pinned_hash(source, store, cache_dir)
    filtered = pd.read_parquet(io.BytesIO(body))
    _require_row_count(source, filtered)
    _require_columns(filtered)
    return filtered


def _object_key(source: FilteredSource) -> str:
    _bucket, key = parse_s3_uri(source.uri)
    return key


def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / CACHE_FILENAME


def _download_source_bytes(source: FilteredSource, store: CampaignObjectStore) -> bytes:
    stored = store.get(_object_key(source))
    if stored is None:
        raise FileNotFoundError(source.uri)
    return stored.body


def _bytes_matching_pinned_hash(
    source: FilteredSource,
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
        raise ValueError(f"SHA-256 mismatch for {source.uri}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(body)
    return body


def _require_row_count(source: FilteredSource, filtered: pd.DataFrame) -> None:
    if len(filtered) != source.expected_row_count:
        raise ValueError(
            f"row_count={len(filtered)} expected={source.expected_row_count} "
            f"uri={source.uri}"
        )


def _require_columns(filtered: pd.DataFrame) -> None:
    actual = list(filtered.columns)
    expected = list(COMBINED_COLUMNS)
    if actual != expected:
        raise ValueError(f"columns={actual} expected={expected}")
