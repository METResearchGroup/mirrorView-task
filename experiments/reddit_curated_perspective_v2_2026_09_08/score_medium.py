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
TOXICITY_PROB_MIN = 0.0
TOXICITY_PROB_MAX = 1.0


def default_score_engine() -> BatchExecutionEngine:
    """Return the product thread-pool engine for ``is_toxic_tiered``.

    Returns
    -------
    BatchExecutionEngine
        Engine built from ``FEATURE_REGISTRY["is_toxic_tiered"]``.
    """
    raise NotImplementedError


def tasks_for_medium_rows(medium: pd.DataFrame) -> list[LabelTask]:
    """Build one labeling task per medium curated comment.

    Parameters
    ----------
    medium
        Rows whose LLM toxicity tier is medium. Uses ``source_record_id``
        and ``text``.

    Returns
    -------
    list[LabelTask]
        One task per row. ``uri`` is the record id and ``text`` is the comment.
    """
    return [
        LabelTask(uri=str(record_id), text=str(text))
        for record_id, text in zip(
            medium[SOURCE_RECORD_ID_COLUMN],
            medium[TEXT_COLUMN],
            strict=True,
        )
    ]


def score_medium_comments(
    medium: pd.DataFrame,
    *,
    scores_path: Path,
    engine: BatchExecutionEngine | None = None,
) -> pd.DataFrame:
    """Score medium comments with Perspective and persist probabilities.

    Parameters
    ----------
    medium
        Medium-tier curated rows to score.
    scores_path
        Parquet path for ``source_record_id`` and ``toxicity_prob``. Existing
        finite probabilities in ``[0, 1]`` are skipped.
    engine
        Batch engine used to label pending rows. None builds the product
        ``is_toxic_tiered`` thread-pool engine.

    Returns
    -------
    pd.DataFrame
        Scores for every medium id, including rows loaded from disk.

    Raises
    ------
    ValueError
        When any medium id still lacks a finite toxicity probability after
        the engine returns.
    """
    raise NotImplementedError
