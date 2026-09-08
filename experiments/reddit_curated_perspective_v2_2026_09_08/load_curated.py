"""Load the pinned curated Reddit parquet without writing over it.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --load-only
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

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
    raise NotImplementedError


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
    raise NotImplementedError
