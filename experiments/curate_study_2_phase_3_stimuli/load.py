"""Download pinned post tables and flip parquets."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.curate_study_2_phase_3_stimuli.sources import (
    FLIP_KEEP_COLUMNS,
    FLIPS_CACHE_FILENAME,
    FlipSource,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.load_raw_candidate_dataset import (
    load_raw_candidate_dataset,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)


def load_posts(
    source: CandidateSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download a pinned combined-column parquet and check its identity.

    Parameters
    ----------
    source
        Pinned post parquet identity.
    store
        Object store for the source bucket.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        Combined-column post table.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or columns do not match the pin.
    """
    return load_raw_candidate_dataset(source, store, cache_dir)


def load_flips(
    source: FlipSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download a pinned flips parquet and check its identity.

    Parameters
    ----------
    source
        Pinned flips parquet identity.
    store
        Object store for the source bucket.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        Flip rows with at least record id, original text, and mirrored text.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or required columns do not match.
    """
    body = _bytes_matching_pinned_hash(source, store, cache_dir)
    frame = pd.read_parquet(io.BytesIO(body))
    _require_row_count(source, frame)
    _require_flip_columns(frame)
    return frame


def _object_key(source: FlipSource) -> str:
    _bucket, key = parse_s3_uri(source.s3_uri)
    return key


def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / FLIPS_CACHE_FILENAME


def _download_source_bytes(source: FlipSource, store: CampaignObjectStore) -> bytes:
    stored = store.get(_object_key(source))
    if stored is None:
        raise FileNotFoundError(source.s3_uri)
    return stored.body


def _bytes_matching_pinned_hash(
    source: FlipSource,
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


def _require_row_count(source: FlipSource, frame: pd.DataFrame) -> None:
    if len(frame) != source.expected_row_count:
        raise ValueError(
            f"row_count={len(frame)} expected={source.expected_row_count} "
            f"uri={source.s3_uri}"
        )


def _require_flip_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in FLIP_KEEP_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"missing flip columns {missing}")
