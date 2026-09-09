"""Score leftover right-medium posts with the Perspective thread-pool engine."""

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
from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.sources import (
    ENGINE_SOURCE_RECORD_ID_COLUMN,
    MISSING_ID_SAMPLE_SIZE,
    RECORD_ID_COLUMN,
    SCORE_BATCH_SIZE,
    SCORE_FEATURE_NAME,
    SCORE_MAX_CONCURRENCY,
    TEXT_COLUMN,
    TOXICITY_PROB_COLUMN,
    TOXICITY_PROB_MAX,
    TOXICITY_PROB_MIN,
)


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


def score_candidates(
    candidates: pd.DataFrame,
    *,
    scores_path: Path,
    engine: BatchExecutionEngine | None = None,
) -> pd.DataFrame:
    """Score candidates with Perspective and persist ``record_id`` probabilities.

    Parameters
    ----------
    candidates
        Leftover right-medium rows.
    scores_path
        Parquet path for ``record_id`` and ``toxicity_prob``. Existing finite
        probabilities in ``[0, 1]`` are skipped.
    engine
        Batch engine used to label pending rows. None builds the product
        ``is_toxic_tiered`` thread-pool engine.

    Returns
    -------
    pd.DataFrame
        Scores for every candidate id.

    Raises
    ------
    ValueError
        When any candidate still lacks a finite toxicity probability.
    """
    resolved_engine = engine if engine is not None else default_score_engine()
    existing = _valid_existing_scores(_load_existing_scores(scores_path))
    pending = _pending_candidate_rows(candidates, set(existing[RECORD_ID_COLUMN]))
    scores = _score_pending_batches(pending, resolved_engine, existing, scores_path)
    _require_complete_scores(candidates, scores)
    return _ordered_scores(candidates, scores)


def _empty_scores_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            RECORD_ID_COLUMN: pd.Series(dtype="string"),
            TOXICITY_PROB_COLUMN: pd.Series(dtype="float64"),
        }
    )


def _valid_probability_mask(probabilities: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(probabilities, errors="coerce")
    in_unit_interval = numeric.between(TOXICITY_PROB_MIN, TOXICITY_PROB_MAX)
    return in_unit_interval & numeric.notna()


def _load_existing_scores(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return _empty_scores_frame()
    return pd.read_parquet(path)


def _valid_existing_scores(existing: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        return _empty_scores_frame()
    valid = existing.loc[_valid_probability_mask(existing[TOXICITY_PROB_COLUMN])].copy()
    valid[RECORD_ID_COLUMN] = valid[RECORD_ID_COLUMN].astype(str)
    return valid.drop_duplicates(subset=[RECORD_ID_COLUMN], keep="last")


def _pending_candidate_rows(candidates: pd.DataFrame, scored_ids: set[str]) -> pd.DataFrame:
    record_ids = candidates[RECORD_ID_COLUMN].astype(str)
    return candidates.loc[~record_ids.isin(scored_ids)].reset_index(drop=True)


def _tasks_for_candidates(candidates: pd.DataFrame) -> list[LabelTask]:
    return [
        LabelTask(uri=str(record_id), text=str(text))
        for record_id, text in zip(
            candidates[RECORD_ID_COLUMN],
            candidates[TEXT_COLUMN],
            strict=True,
        )
    ]


def _scores_from_engine_rows(labeled: list[dict]) -> pd.DataFrame:
    if not labeled:
        return _empty_scores_frame()
    frame = pd.DataFrame(labeled)
    renamed = frame.rename(columns={ENGINE_SOURCE_RECORD_ID_COLUMN: RECORD_ID_COLUMN})
    return renamed.loc[:, [RECORD_ID_COLUMN, TOXICITY_PROB_COLUMN]]


def _merge_score_frames(existing: pd.DataFrame, new_rows: pd.DataFrame) -> pd.DataFrame:
    if new_rows.empty:
        return existing
    combined = pd.concat([existing, new_rows], ignore_index=True)
    combined[RECORD_ID_COLUMN] = combined[RECORD_ID_COLUMN].astype(str)
    combined[TOXICITY_PROB_COLUMN] = pd.to_numeric(
        combined[TOXICITY_PROB_COLUMN], errors="coerce"
    )
    return combined.drop_duplicates(subset=[RECORD_ID_COLUMN], keep="last")


def _write_scores_parquet(scores: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, suffix=".parquet", delete=False) as tmp:
        temporary_path = Path(tmp.name)
    try:
        scores.to_parquet(temporary_path, index=False)
        temporary_path.replace(path)
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
    for chunk in batched(_tasks_for_candidates(pending), SCORE_BATCH_SIZE):
        scored_chunk = _scores_from_engine_rows(engine.batch_label_records(chunk))
        scores = _merge_score_frames(scores, scored_chunk)
        _write_scores_parquet(scores, scores_path)
    return scores


def _missing_candidate_ids(candidates: pd.DataFrame, scores: pd.DataFrame) -> list[str]:
    needed_ids = candidates[RECORD_ID_COLUMN].astype(str).tolist()
    if scores.empty:
        return needed_ids
    valid_mask = _valid_probability_mask(scores[TOXICITY_PROB_COLUMN])
    scored_ids = set(scores.loc[valid_mask, RECORD_ID_COLUMN].astype(str))
    return [record_id for record_id in needed_ids if record_id not in scored_ids]


def _require_complete_scores(candidates: pd.DataFrame, scores: pd.DataFrame) -> None:
    missing_ids = _missing_candidate_ids(candidates, scores)
    if not missing_ids:
        return
    sample = missing_ids[:MISSING_ID_SAMPLE_SIZE]
    raise ValueError(
        f"missing toxicity_prob for {len(missing_ids)} ids sample={sample}"
    )


def _ordered_scores(candidates: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    order = candidates[RECORD_ID_COLUMN].astype(str)
    indexed = scores.set_index(RECORD_ID_COLUMN, drop=False)
    return indexed.loc[order].reset_index(drop=True)
