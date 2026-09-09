"""Promote the top 300 scored right-medium posts to high and concatenate the unified table."""

from __future__ import annotations

import pandas as pd

from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.sources import (
    HIGH_TOXICITY,
    LEFT_STANCE,
    MEDIUM_TOXICITY,
    MEDIUM_UPSAMPLE_ROW_COUNT,
    PROMOTION_COUNT,
    PromotionResult,
    RECORD_ID_COLUMN,
    RIGHT_STANCE,
    SORT_COLUMNS,
    SORT_KIND,
    STANCE_COLUMN,
    TOXICITY_COLUMN,
    TOXICITY_PROB_COLUMN,
    UNIFIED_ROW_COUNT,
)

EXPECTED_UNIFIED_LEFT = 1000
EXPECTED_UNIFIED_RIGHT = 1300


def promote_top_candidates(
    candidates: pd.DataFrame,
    scores: pd.DataFrame,
    medium_upsample: pd.DataFrame,
) -> PromotionResult:
    """Reclassify the top 300 scored rows as high and concatenate the 2,000 medium posts.

    Parameters
    ----------
    candidates
        Leftover right-medium rows.
    scores
        ``record_id`` and ``toxicity_prob`` for those rows.
    medium_upsample
        The 2,000 unused medium posts. Toxicity stays medium.

    Returns
    -------
    PromotionResult
        Promoted rows and the unified 2,300 post table.

    Raises
    ------
    ValueError
        When a promotion is not right, still medium after the copy, or overlaps
        the 2,000 medium upsample.
    """
    promotion_ids = select_promotions(scores)
    promoted = _promoted_rows(candidates, promotion_ids)
    unified = _unified_table(medium_upsample, promoted)
    return PromotionResult(
        promotion_ids=promotion_ids,
        promoted=promoted,
        unified=unified,
    )


def select_promotions(
    scores: pd.DataFrame,
    *,
    count: int = PROMOTION_COUNT,
) -> list[str]:
    """Return the highest-probability candidate ids to promote.

    Parameters
    ----------
    scores
        Table with ``record_id`` and ``toxicity_prob``.
    count
        Number of ids to keep after ranking.

    Returns
    -------
    list[str]
        ``record_id`` values, ranked by ``toxicity_prob`` descending then
        ``record_id`` ascending.

    Raises
    ------
    ValueError
        When ``scores`` has fewer rows than ``count``.
    """
    if len(scores) < count:
        raise ValueError(f"scored_rows={len(scores)} promotion_count={count}")
    ranked = scores.sort_values(
        by=[TOXICITY_PROB_COLUMN, RECORD_ID_COLUMN],
        ascending=[False, True],
        kind=SORT_KIND,
    )
    return ranked[RECORD_ID_COLUMN].astype(str).tolist()[:count]


def _promoted_rows(candidates: pd.DataFrame, promotion_ids: list[str]) -> pd.DataFrame:
    indexed = candidates.set_index(candidates[RECORD_ID_COLUMN].astype(str), drop=False)
    _require_promotion_ids_present(indexed.index, promotion_ids)
    promoted = indexed.loc[list(promotion_ids)].copy()
    promoted[TOXICITY_COLUMN] = HIGH_TOXICITY
    promoted = promoted.reset_index(drop=True)
    _require_promoted_shape(promoted)
    return promoted


def _require_promotion_ids_present(
    candidate_ids: pd.Index, promotion_ids: list[str]
) -> None:
    missing = [record_id for record_id in promotion_ids if record_id not in candidate_ids]
    if missing:
        raise ValueError(f"missing promotion id {missing[0]}")


def _require_promoted_shape(promoted: pd.DataFrame) -> None:
    if len(promoted) != PROMOTION_COUNT:
        raise ValueError(f"promotions={len(promoted)} needed={PROMOTION_COUNT}")
    if not (promoted[STANCE_COLUMN] == RIGHT_STANCE).all():
        raise ValueError("promoted rows must all be right")
    if not (promoted[TOXICITY_COLUMN] == HIGH_TOXICITY).all():
        raise ValueError("promoted rows must all be high")


def _unified_table(medium_upsample: pd.DataFrame, promoted: pd.DataFrame) -> pd.DataFrame:
    _require_no_id_overlap(medium_upsample, promoted)
    _require_medium_upsample_shape(medium_upsample)
    unified = pd.concat([medium_upsample, promoted], ignore_index=True)
    unified = unified.sort_values(list(SORT_COLUMNS), kind=SORT_KIND).reset_index(
        drop=True
    )
    _require_unified_shape(unified)
    return unified


def _require_no_id_overlap(medium_upsample: pd.DataFrame, promoted: pd.DataFrame) -> None:
    overlap = set(medium_upsample[RECORD_ID_COLUMN].map(str)) & set(
        promoted[RECORD_ID_COLUMN].map(str)
    )
    if overlap:
        raise ValueError(f"promoted id overlaps medium upsample {sorted(overlap)[0]}")


def _require_medium_upsample_shape(medium_upsample: pd.DataFrame) -> None:
    if len(medium_upsample) != MEDIUM_UPSAMPLE_ROW_COUNT:
        raise ValueError(
            f"medium_upsample_rows={len(medium_upsample)} "
            f"expected={MEDIUM_UPSAMPLE_ROW_COUNT}"
        )
    if not (medium_upsample[TOXICITY_COLUMN] == MEDIUM_TOXICITY).all():
        raise ValueError("medium upsample rows must all be medium")


def _require_unified_shape(unified: pd.DataFrame) -> None:
    medium_n = int((unified[TOXICITY_COLUMN] == MEDIUM_TOXICITY).sum())
    high_n = int((unified[TOXICITY_COLUMN] == HIGH_TOXICITY).sum())
    left_n = int((unified[STANCE_COLUMN] == LEFT_STANCE).sum())
    right_n = int((unified[STANCE_COLUMN] == RIGHT_STANCE).sum())
    if len(unified) != UNIFIED_ROW_COUNT:
        raise ValueError(f"unified_rows={len(unified)} expected={UNIFIED_ROW_COUNT}")
    if medium_n != MEDIUM_UPSAMPLE_ROW_COUNT or high_n != PROMOTION_COUNT:
        raise ValueError(f"unified_medium={medium_n} unified_high={high_n}")
    if left_n != EXPECTED_UNIFIED_LEFT or right_n != EXPECTED_UNIFIED_RIGHT:
        raise ValueError(f"unified_left={left_n} unified_right={right_n}")
