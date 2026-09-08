"""Promote the top Perspective-scored medium comments and write curated v2.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --write-v2
"""

from __future__ import annotations

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

PROMOTION_COUNT = 3000
V2_FILENAME = "mirrorview_v2.parquet"
HIGH_TIER = "high"
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
    raise NotImplementedError


def apply_promotions(
    curated: pd.DataFrame,
    promotion_ids: list[str],
) -> pd.DataFrame:
    raise NotImplementedError


def write_curated_v2(
    curated_v2: pd.DataFrame,
    *,
    store: CampaignObjectStore,
    key: str,
) -> str:
    raise NotImplementedError
