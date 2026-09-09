"""Download the pinned flips parquet and build the QA table.

given local AWS credentials from the default credential chain
and the pinned flips parquet exists at SHA-256 f3b791f226f8f69d3ddaf0737aab0a3aaf20ebb36d45a6d9b42dec8d1e148702
when load_flips_dataset is called
then the returned frame has 10182 rows
and columns match FLIP_PARQUET_COLUMNS

when qa_table is called with that frame
then the returned frame has columns ID, original text, mirror text, political lean, and toxicity tier
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.qa_latest_dataset_2026_09_09.sources import (
    CACHE_FILENAME,
    FLIP_COLUMNS,
    QA_COLUMN_RENAME,
    QA_COLUMNS,
    FlipsSource,
    pinned_flips_source,
)
from lib.constants import REPO_ROOT

EXPERIMENT_DIR = REPO_ROOT / "experiments" / "qa_latest_dataset_2026_09_09"
DEFAULT_CACHE_DIR = EXPERIMENT_DIR / "cache"


def load_flips_dataset(
    source: FlipsSource | None = None,
    store: CampaignObjectStore | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Return the pinned flips table after checking SHA-256, row count, and columns.

    A matching local cache copy is reused when its SHA-256 matches the pin.

    Parameters
    ----------
    source
        Pinned flips parquet identity. Defaults to the experiment pin.
    store
        Object store for the source bucket. If omitted, the function builds one.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        The flips table with original text, mirrored text, stance, and toxicity.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or columns do not match the pin.
    """
    resolved_source = source if source is not None else pinned_flips_source()
    resolved_store = store if store is not None else _store_for_source(resolved_source)
    resolved_cache_dir = cache_dir if cache_dir is not None else DEFAULT_CACHE_DIR
    body = _bytes_matching_pinned_hash(
        resolved_source, resolved_store, resolved_cache_dir
    )
    flips = pd.read_parquet(io.BytesIO(body))
    _require_row_count(resolved_source, flips)
    _require_columns(flips)
    return flips


def qa_table(flips: pd.DataFrame) -> pd.DataFrame:
    """Return the five-column QA view of original posts and their mirrors.

    Parameters
    ----------
    flips
        Flips table with record id, original text, mirrored text, stance, and toxicity.

    Returns
    -------
    pd.DataFrame
        Table with ID, original text, mirror text, political lean, and toxicity tier.

    Raises
    ------
    ValueError
        When a required source column is missing.
    """
    missing = [column for column in QA_COLUMN_RENAME if column not in flips.columns]
    if missing:
        raise ValueError(f"missing columns={missing}")
    view = flips.loc[:, list(QA_COLUMN_RENAME)].rename(columns=QA_COLUMN_RENAME)
    return view.loc[:, list(QA_COLUMNS)]


def _store_for_source(source: FlipsSource) -> CampaignObjectStore:
    bucket, _key = parse_s3_uri(source.uri)
    return CampaignObjectStore(bucket)


def _object_key(source: FlipsSource) -> str:
    _bucket, key = parse_s3_uri(source.uri)
    return key


def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / CACHE_FILENAME


def _download_source_bytes(source: FlipsSource, store: CampaignObjectStore) -> bytes:
    stored = store.get(_object_key(source))
    if stored is None:
        raise FileNotFoundError(source.uri)
    return stored.body


def _bytes_matching_pinned_hash(
    source: FlipsSource,
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


def _require_row_count(source: FlipsSource, flips: pd.DataFrame) -> None:
    if len(flips) != source.expected_row_count:
        raise ValueError(
            f"row_count={len(flips)} expected={source.expected_row_count} "
            f"uri={source.uri}"
        )


def _require_columns(flips: pd.DataFrame) -> None:
    actual = list(flips.columns)
    expected = list(FLIP_COLUMNS)
    if actual != expected:
        raise ValueError(f"columns={actual} expected={expected}")
