"""Download the pinned combined parquet and check its hash and row count."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CANDIDATE_COLUMNS,
    CandidateSource,
)
from lib.constants import REPO_ROOT

EXPERIMENT_DIR = (
    REPO_ROOT / "experiments" / "filter_posts_used_for_stimulus_dataset_2026_09_08"
)
DEFAULT_CACHE_DIR = EXPERIMENT_DIR / "cache"
CACHE_FILENAME = "dataset.parquet"


def load_raw_candidate_dataset(
    source: CandidateSource,
    store: CampaignObjectStore | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Return the candidate table after checking SHA-256 and row count.

    A matching local cache copy is reused when its SHA-256 matches the pin.

    Parameters
    ----------
    source
        Pinned combined parquet identity.
    store
        If you omit store, the function builds a store for the source bucket.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        The combined candidate table.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or columns do not match the pin.
    """
    resolved_store = store if store is not None else _store_for_source(source)
    resolved_cache_dir = cache_dir if cache_dir is not None else DEFAULT_CACHE_DIR
    body = _bytes_matching_pinned_hash(source, resolved_store, resolved_cache_dir)
    candidate = pd.read_parquet(io.BytesIO(body))
    _require_row_count(source, candidate)
    _require_columns(candidate)
    return candidate


def _store_for_source(source: CandidateSource) -> CampaignObjectStore:
    bucket, _key = parse_s3_uri(source.s3_uri)
    return CampaignObjectStore(bucket)


def _object_key(source: CandidateSource) -> str:
    _bucket, key = parse_s3_uri(source.s3_uri)
    return key


def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / CACHE_FILENAME


def _download_source_bytes(source: CandidateSource, store: CampaignObjectStore) -> bytes:
    stored = store.get(_object_key(source))
    if stored is None:
        raise FileNotFoundError(source.s3_uri)
    return stored.body


def _bytes_matching_pinned_hash(
    source: CandidateSource,
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


def _require_row_count(source: CandidateSource, candidate: pd.DataFrame) -> None:
    if len(candidate) != source.expected_row_count:
        raise ValueError(
            f"row_count={len(candidate)} expected={source.expected_row_count} "
            f"uri={source.s3_uri}"
        )


def _require_columns(candidate: pd.DataFrame) -> None:
    actual = list(candidate.columns)
    expected = list(CANDIDATE_COLUMNS)
    if actual != expected:
        raise ValueError(f"columns={actual} expected={expected}")
