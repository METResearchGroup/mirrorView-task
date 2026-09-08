"""Score medium curated Reddit comments with the Perspective thread-pool engine.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --score
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.engines.base import BatchExecutionEngine
from data_platform.generate_features.models import LabelTask

SCORE_FEATURE_NAME = "is_toxic_tiered"
SCORE_BATCH_SIZE = 64
SCORE_MAX_CONCURRENCY = 80
SOURCE_RECORD_ID_COLUMN = "source_record_id"
TEXT_COLUMN = "text"
TOXICITY_PROB_COLUMN = "toxicity_prob"


def tasks_for_medium_rows(medium: pd.DataFrame) -> list[LabelTask]:
    raise NotImplementedError


def score_medium_comments(
    medium: pd.DataFrame,
    scores_path: Path,
    engine: BatchExecutionEngine | None = None,
) -> pd.DataFrame:
    raise NotImplementedError
