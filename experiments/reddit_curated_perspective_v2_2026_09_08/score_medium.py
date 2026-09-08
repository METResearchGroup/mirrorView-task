"""Score medium curated Reddit comments with the Perspective thread-pool engine.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --score
"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd

from data_platform.generate_features.engines import build_engine
from data_platform.generate_features.engines.base import (
    BatchExecutionEngine,
    batched,
)
from data_platform.generate_features.models import FeatureRunConfig, LabelTask
from data_platform.generate_features.registry import FEATURE_REGISTRY

SCORE_FEATURE_NAME = "is_toxic_tiered"
SCORE_BATCH_SIZE = 64
SCORE_MAX_CONCURRENCY = 80
SOURCE_RECORD_ID_COLUMN = "source_record_id"
TEXT_COLUMN = "text"
TOXICITY_PROB_COLUMN = "toxicity_prob"
TOXICITY_PROB_MIN = 0.0
TOXICITY_PROB_MAX = 1.0
MISSING_ID_SAMPLE_SIZE = 5


def default_score_engine() -> BatchExecutionEngine:
    """Return the product thread-pool engine for ``is_toxic_tiered``.

    Returns
    -------
    BatchExecutionEngine
        Engine built from ``FEATURE_REGISTRY["is_toxic_tiered"]``.
    """
    spec = FEATURE_REGISTRY[SCORE_FEATURE_NAME]
    run_config = FeatureRunConfig(
        max_concurrency=SCORE_MAX_CONCURRENCY,
        batch_size=SCORE_BATCH_SIZE,
    )
    return build_engine(spec, run_config)


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


def _empty_scores_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            SOURCE_RECORD_ID_COLUMN: pd.Series(dtype="string"),
            TOXICITY_PROB_COLUMN: pd.Series(dtype="float64"),
        }
    )


def _valid_probability_mask(probabilities: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(probabilities, errors="coerce")
    in_unit_interval = numeric.between(TOXICITY_PROB_MIN, TOXICITY_PROB_MAX)
    return in_unit_interval & numeric.notna()


def _load_existing_scores(scores_path: Path) -> pd.DataFrame:
    if not scores_path.is_file():
        return _empty_scores_frame()
    return pd.read_parquet(scores_path)


def _valid_existing_scores(existing: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        return _empty_scores_frame()
    valid = existing.loc[_valid_probability_mask(existing[TOXICITY_PROB_COLUMN])].copy()
    valid[SOURCE_RECORD_ID_COLUMN] = valid[SOURCE_RECORD_ID_COLUMN].astype(str)
    return valid.drop_duplicates(subset=[SOURCE_RECORD_ID_COLUMN], keep="last")


def _pending_medium_rows(medium: pd.DataFrame, scored_ids: set[str]) -> pd.DataFrame:
    record_ids = medium[SOURCE_RECORD_ID_COLUMN].astype(str)
    return medium.loc[~record_ids.isin(scored_ids)].reset_index(drop=True)


def _merge_score_frames(existing: pd.DataFrame, new_rows: pd.DataFrame) -> pd.DataFrame:
    if new_rows.empty:
        return existing
    combined = pd.concat([existing, new_rows], ignore_index=True)
    combined[SOURCE_RECORD_ID_COLUMN] = combined[SOURCE_RECORD_ID_COLUMN].astype(str)
    combined[TOXICITY_PROB_COLUMN] = pd.to_numeric(
        combined[TOXICITY_PROB_COLUMN], errors="coerce"
    )
    return combined.drop_duplicates(subset=[SOURCE_RECORD_ID_COLUMN], keep="last")


def _write_scores_parquet(scores: pd.DataFrame, scores_path: Path) -> None:
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        dir=scores_path.parent,
        suffix=".parquet",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
    try:
        scores.to_parquet(temporary_path, index=False)
        temporary_path.replace(scores_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _score_pending_batches(
    pending: pd.DataFrame,
    engine: BatchExecutionEngine,
    existing: pd.DataFrame,
    scores_path: Path,
) -> pd.DataFrame:
    scores = existing
    pending_tasks = tasks_for_medium_rows(pending)
    for chunk in batched(pending_tasks, SCORE_BATCH_SIZE):
        scored_chunk = pd.DataFrame(engine.batch_label_records(chunk))
        scores = _merge_score_frames(scores, scored_chunk)
        _write_scores_parquet(scores, scores_path)
    return scores


def _missing_medium_ids(medium: pd.DataFrame, scores: pd.DataFrame) -> list[str]:
    needed_ids = medium[SOURCE_RECORD_ID_COLUMN].astype(str).tolist()
    if scores.empty:
        return needed_ids
    valid_mask = _valid_probability_mask(scores[TOXICITY_PROB_COLUMN])
    scored_ids = set(scores.loc[valid_mask, SOURCE_RECORD_ID_COLUMN].astype(str))
    return [record_id for record_id in needed_ids if record_id not in scored_ids]


def _require_complete_scores(medium: pd.DataFrame, scores: pd.DataFrame) -> None:
    missing_ids = _missing_medium_ids(medium, scores)
    if not missing_ids:
        return
    sample = missing_ids[:MISSING_ID_SAMPLE_SIZE]
    raise ValueError(
        f"missing toxicity_prob for {len(missing_ids)} ids sample={sample}"
    )


def _ordered_scores_for_medium(medium: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    order = medium[SOURCE_RECORD_ID_COLUMN].astype(str)
    indexed = scores.set_index(SOURCE_RECORD_ID_COLUMN, drop=False)
    return indexed.loc[order].reset_index(drop=True)


def count_already_scored(medium: pd.DataFrame, scores_path: Path) -> int:
    """Count medium ids that already have a finite toxicity probability on disk.

    Parameters
    ----------
    medium
        Medium-tier curated rows.
    scores_path
        Persisted scores parquet.

    Returns
    -------
    int
        Number of medium ids with a finite ``toxicity_prob`` in ``[0, 1]``.
    """
    existing = _valid_existing_scores(_load_existing_scores(scores_path))
    scored_ids = set(existing[SOURCE_RECORD_ID_COLUMN].astype(str))
    medium_ids = medium[SOURCE_RECORD_ID_COLUMN].astype(str)
    return int(medium_ids.isin(scored_ids).sum())


def require_all_medium_scored(medium: pd.DataFrame, scores_path: Path) -> None:
    """Raise if any medium id still lacks a finite toxicity probability.

    Parameters
    ----------
    medium
        Medium-tier curated rows.
    scores_path
        Persisted scores parquet.

    Raises
    ------
    ValueError
        When the number of valid scores does not equal the medium row count.
    """
    scored = count_already_scored(medium, scores_path)
    if scored != len(medium):
        raise ValueError(f"scored={scored} medium_rows={len(medium)}")


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
    resolved_engine = engine if engine is not None else default_score_engine()
    existing = _valid_existing_scores(_load_existing_scores(scores_path))
    scored_ids = set(existing[SOURCE_RECORD_ID_COLUMN].astype(str))
    pending = _pending_medium_rows(medium, scored_ids)
    scores = _score_pending_batches(pending, resolved_engine, existing, scores_path)
    _require_complete_scores(medium, scores)
    return _ordered_scores_for_medium(medium, scores)
