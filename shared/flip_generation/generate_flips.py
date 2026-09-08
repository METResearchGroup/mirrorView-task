"""Generate politically mirrored posts and write immutable S3 parquet parts.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from shared.flip_generation.generate_flips import BATCH_SIZE, generate_flips; print(BATCH_SIZE)"
"""

from __future__ import annotations

import pandas as pd

from data_platform.generate_features.engines.bedrock_engine import BedrockRuntimeClient
from data_platform.generate_features.models import LabelTask
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

from shared.flip_generation.models import FlipRunResult

BATCH_SIZE = 25
MAX_CONCURRENCY = 10
MAX_TOKENS = 2048
FEATURE_NAME = "flip"
RECORD_ID_COLUMN = "record_id"
TEXT_COLUMN = "text"
STANCE_COLUMN = "political_stance"
TOXICITY_COLUMN = "llm_toxicity_tier"
SORT_KIND = "mergesort"
LEFT_STANCE = "left"
RIGHT_STANCE = "right"
REQUIRED_COLUMNS = (
    RECORD_ID_COLUMN,
    TEXT_COLUMN,
    STANCE_COLUMN,
    TOXICITY_COLUMN,
)
TARGET_GROUP_BY_STANCE = {
    LEFT_STANCE: RIGHT_STANCE,
    RIGHT_STANCE: LEFT_STANCE,
}


def _validate_posts(posts: pd.DataFrame) -> pd.DataFrame:
    """Validate required columns and stances, then sort by record id."""
    raise NotImplementedError


def _build_label_tasks(posts: pd.DataFrame) -> list[LabelTask]:
    """Build LabelTask rows from validated posts."""
    raise NotImplementedError


def _label_and_write_parts(
    posts: pd.DataFrame,
    tasks: list[LabelTask],
    store: CampaignObjectStore,
    run_prefix: str,
    client: BedrockRuntimeClient,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
    model_id: str,
) -> None:
    """Label pending batches and write parquet parts plus errors."""
    raise NotImplementedError


def generate_flips(
    posts: pd.DataFrame,
    store: CampaignObjectStore,
    run_prefix: str,
    client: BedrockRuntimeClient,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
    model_id: str,
) -> FlipRunResult:
    """Generate mirrored posts and write resumable S3 artifacts."""
    validated_posts = _validate_posts(posts)
    tasks = _build_label_tasks(validated_posts)
    _label_and_write_parts(
        validated_posts,
        tasks,
        store,
        run_prefix,
        client,
        batch_size,
        max_concurrency,
        max_tokens,
        model_id,
    )
    raise NotImplementedError
