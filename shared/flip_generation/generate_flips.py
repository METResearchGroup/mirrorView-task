"""Generate politically mirrored posts and write immutable S3 parquet parts.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from shared.flip_generation.generate_flips import BATCH_SIZE, generate_flips; print(BATCH_SIZE)"

Smoke (manual, not pytest):

    given a two-row posts frame with required columns and a fake Converse client
    and an in-memory store
    when generate_flips is called with BATCH_SIZE, MAX_CONCURRENCY, MAX_TOKENS, and DEFAULT_BEDROCK_SONNET_MODEL
    then one part object exists
    and flips.parquet exists
    and FlipRunResult.row_count is 2
    and FlipRunResult.wrote_final is true

    given the same store and run_prefix
    when generate_flips is called again
    then the fake client is not called
    and FlipRunResult.row_count is 2
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
    """Validate required columns and stances, then sort by record id.

    Parameters
    ----------
    posts
        Input table with record id, text, stance, and toxicity tier.

    Returns
    -------
    pd.DataFrame
        Copy of ``posts`` sorted by ``RECORD_ID_COLUMN``.

    Raises
    ------
    ValueError
        When a required column is missing, ``record_id`` is duplicated, or
        ``political_stance`` is not ``left`` or ``right``.
    """
    raise NotImplementedError


def _build_label_tasks(posts: pd.DataFrame) -> list[LabelTask]:
    """Build LabelTask rows from validated posts.

    Parameters
    ----------
    posts
        Validated posts sorted by record id.

    Returns
    -------
    list[LabelTask]
        One task per row with opposite-stance target group in the user message.
    """
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
    """Label pending batches and write parquet parts plus errors.

    Parameters
    ----------
    posts
        Validated input table.
    tasks
        Label tasks in record-id order.
    store
        Campaign object store for the run prefix.
    run_prefix
        S3 key prefix ending in ``/``.
    client
        Bedrock runtime client.
    batch_size
        Rows per immutable part.
    max_concurrency
        Thread pool size for Bedrock calls.
    max_tokens
        Converse ``maxTokens`` for each flip.
    model_id
        Bedrock model id.
    """
    raise NotImplementedError


def _build_flip_run_result(
    posts: pd.DataFrame,
    store: CampaignObjectStore,
    run_prefix: str,
) -> FlipRunResult:
    """Collect part and error counts and finalize ``flips.parquet`` when complete."""
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
    """Generate mirrored posts and write resumable S3 artifacts.

    Parameters
    ----------
    posts
        Input table with ``record_id``, ``text``, ``political_stance``, and
        ``llm_toxicity_tier``.
    store
        Campaign object store for the run prefix.
    run_prefix
        S3 key prefix ending in ``/``.
    client
        Bedrock runtime client.
    batch_size
        Rows per immutable part.
    max_concurrency
        Thread pool size for Bedrock calls.
    max_tokens
        Converse ``maxTokens`` for each flip.
    model_id
        Bedrock model id.

    Returns
    -------
    FlipRunResult
        Run summary with part counts and whether ``flips.parquet`` exists.
    """
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
    return _build_flip_run_result(validated_posts, store, run_prefix)
