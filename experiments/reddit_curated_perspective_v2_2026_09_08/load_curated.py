"""Load the pinned curated Reddit parquet without writing over it.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --load-only
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
from lib.constants import REPO_ROOT

PINNED_CURATED_S3_URI = (
    "s3://mirrorview-experimental-artifacts/data_platform/data/reddit/"
    "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/"
    "mirrorview.parquet"
)
PINNED_CURATED_SHA256 = "1db34b0f6b5d4bab42e3a3a57306de0397e4478a3906f7aa75e9229bc58d804f"
EXPECTED_CURATED_ROW_COUNT = 43061
EXPECTED_MEDIUM_ROW_COUNT = 20727
LLM_TOXICITY_TIER_COLUMN = "llm_toxicity_tier"
MEDIUM_TIER = "medium"
SOURCE_RECORD_ID_COLUMN = "source_record_id"
TEXT_COLUMN = "text"
EXPERIMENT_DIR = (
    REPO_ROOT / "experiments" / "reddit_curated_perspective_v2_2026_09_08"
)
DEFAULT_CACHE_PATH = EXPERIMENT_DIR / "cache" / "mirrorview.parquet"


def _store_for_pinned_uri() -> CampaignObjectStore:
    bucket, _key = parse_s3_uri(PINNED_CURATED_S3_URI)
    return CampaignObjectStore(bucket)


def _pinned_object_key() -> str:
    _bucket, key = parse_s3_uri(PINNED_CURATED_S3_URI)
    return key


def _download_pinned_bytes(store: CampaignObjectStore) -> bytes:
    stored = store.get(_pinned_object_key())
    if stored is None:
        raise FileNotFoundError(PINNED_CURATED_S3_URI)
    return stored.body


def _bytes_matching_pinned_hash(store: CampaignObjectStore, cache_path: Path) -> bytes:
    if cache_path.is_file():
        cached = cache_path.read_bytes()
        if sha256_hex(cached) == PINNED_CURATED_SHA256:
            return cached
    body = _download_pinned_bytes(store)
    if sha256_hex(body) != PINNED_CURATED_SHA256:
        raise ValueError("pinned curated parquet SHA-256 does not match")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(body)
    return body


def _require_nonempty_medium_text(medium: pd.DataFrame) -> None:
    text = medium[TEXT_COLUMN].fillna("").astype(str).str.strip()
    if (text == "").any():
        raise ValueError("medium rows include empty text")


def _validate_curated_counts(curated: pd.DataFrame) -> None:
    if len(curated) != EXPECTED_CURATED_ROW_COUNT:
        raise ValueError(f"curated_rows={len(curated)}")
    medium = medium_rows(curated)
    distinct_ids = medium[SOURCE_RECORD_ID_COLUMN].nunique()
    if len(medium) != EXPECTED_MEDIUM_ROW_COUNT or distinct_ids != EXPECTED_MEDIUM_ROW_COUNT:
        raise ValueError(f"medium_rows={len(medium)} distinct_ids={distinct_ids}")
    _require_nonempty_medium_text(medium)


def load_pinned_curated(
    store: CampaignObjectStore | None = None,
    cache_path: Path | None = None,
) -> pd.DataFrame:
    """Return the pinned curated Reddit table after checking its hash and row counts.

    Parameters
    ----------
    store
        Object store used to download the pinned parquet. None builds a store
        for the pinned bucket.
    cache_path
        Local parquet path. Missing or stale cache is replaced from S3.

    Returns
    -------
    pd.DataFrame
        The pinned curated comments.

    Raises
    ------
    ValueError
        When the downloaded bytes do not match the pinned SHA-256, the row
        count is wrong, the medium count is wrong, or a medium row has empty
        text.
    FileNotFoundError
        When the pinned S3 object is missing.
    """
    resolved_store = store if store is not None else _store_for_pinned_uri()
    resolved_cache = cache_path if cache_path is not None else DEFAULT_CACHE_PATH
    body = _bytes_matching_pinned_hash(resolved_store, resolved_cache)
    curated = pd.read_parquet(io.BytesIO(body))
    _validate_curated_counts(curated)
    return curated


def medium_rows(curated: pd.DataFrame) -> pd.DataFrame:
    """Return curated rows whose LLM toxicity tier is medium.

    Parameters
    ----------
    curated
        Full curated table with ``llm_toxicity_tier``.

    Returns
    -------
    pd.DataFrame
        Medium-tier subset.
    """
    is_medium = curated[LLM_TOXICITY_TIER_COLUMN] == MEDIUM_TIER
    return curated.loc[is_medium].reset_index(drop=True)
