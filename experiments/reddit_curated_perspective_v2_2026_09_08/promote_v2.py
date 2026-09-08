"""Promote the top Perspective-scored medium comments and write curated v2.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --write-v2
"""

from __future__ import annotations

import io

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import sha256_hex

PROMOTION_COUNT = 3000
V2_FILENAME = "mirrorview_v2.parquet"
HIGH_TIER = "high"
MEDIUM_TIER = "medium"
PROMOTION_ID_SAMPLE_SIZE = 5
SOURCE_RECORD_ID_COLUMN = "source_record_id"
TOXICITY_PROB_COLUMN = "toxicity_prob"
LLM_TOXICITY_TIER_COLUMN = "llm_toxicity_tier"
V2_OBJECT_KEY = (
    "data_platform/data/reddit/"
    "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/curated/2026_09_07-21:47:32/"
    "mirrorview_v2.parquet"
)


def select_promotions(
    scores: pd.DataFrame,
    *,
    count: int = PROMOTION_COUNT,
) -> list[str]:
    """Return the highest-probability medium comment ids to promote.

    Parameters
    ----------
    scores
        Table with ``source_record_id`` and ``toxicity_prob``.
    count
        Number of ids to keep after ranking.

    Returns
    -------
    list[str]
        ``source_record_id`` values, ranked by ``toxicity_prob`` descending
        then ``source_record_id`` ascending.

    Raises
    ------
    ValueError
        When ``scores`` has fewer rows than ``count``.
    """
    _require_enough_scores(scores, count)
    ranked = scores.sort_values(
        by=[TOXICITY_PROB_COLUMN, SOURCE_RECORD_ID_COLUMN],
        ascending=[False, True],
        kind="mergesort",
    )
    record_ids = ranked[SOURCE_RECORD_ID_COLUMN].astype(str).tolist()
    return record_ids[:count]


def _require_enough_scores(scores: pd.DataFrame, count: int) -> None:
    if len(scores) < count:
        raise ValueError(f"scored_rows={len(scores)} promotion_count={count}")


def apply_promotions(
    curated: pd.DataFrame,
    promotion_ids: list[str],
) -> pd.DataFrame:
    """Copy the curated table and set promotion rows from medium to high.

    Parameters
    ----------
    curated
        Full curated comments table.
    promotion_ids
        Record ids that must currently have LLM toxicity tier medium.

    Returns
    -------
    pd.DataFrame
        A copy with the same columns, row count, and row order. Promotion
        rows have ``llm_toxicity_tier`` set to high.

    Raises
    ------
    ValueError
        When a promotion id is missing or is not medium.
    """
    _require_promotions_are_medium(curated, promotion_ids)
    promoted = curated.copy()
    is_promoted = promoted[SOURCE_RECORD_ID_COLUMN].astype(str).isin(promotion_ids)
    promoted.loc[is_promoted, LLM_TOXICITY_TIER_COLUMN] = HIGH_TIER
    return promoted


def _require_promotions_are_medium(
    curated: pd.DataFrame, promotion_ids: list[str]
) -> None:
    record_ids = curated[SOURCE_RECORD_ID_COLUMN].astype(str)
    present_ids = set(record_ids)
    missing_ids = [record_id for record_id in promotion_ids if record_id not in present_ids]
    if missing_ids:
        raise ValueError(f"missing promotion ids sample={missing_ids[:PROMOTION_ID_SAMPLE_SIZE]}")
    promoted_tiers = curated.loc[record_ids.isin(promotion_ids), LLM_TOXICITY_TIER_COLUMN]
    if not (promoted_tiers.astype(str) == MEDIUM_TIER).all():
        raise ValueError("promotion ids must currently be medium")


def write_curated_v2(
    curated_v2: pd.DataFrame,
    *,
    store: CampaignObjectStore,
    key: str,
) -> str:
    """Upload a new curated parquet that must not already exist.

    Parameters
    ----------
    curated_v2
        Curated table after promotions.
    store
        Object store used only with ``put_new``.
    key
        Destination key for ``mirrorview_v2.parquet``.

    Returns
    -------
    str
        SHA-256 of the uploaded parquet bytes.

    Raises
    ------
    FileExistsError
        When the destination key already exists.
    """
    body = _parquet_bytes(curated_v2)
    store.put_new(key, body)
    return sha256_hex(body)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()
