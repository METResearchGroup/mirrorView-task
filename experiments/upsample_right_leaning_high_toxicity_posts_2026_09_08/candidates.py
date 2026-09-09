"""Build leftover right-medium Perspective candidates."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.sources import (
    CandidateBuildResult,
    EXPECTED_LEFTOVER_RIGHT_MEDIUM_AFTER_UPSAMPLE,
    MEDIUM_TOXICITY,
    MIN_CANDIDATES,
    PR260_PROMOTION_IDS_PATH,
    RECORD_ID_COLUMN,
    RIGHT_STANCE,
    SOURCE_RECORD_ID_COLUMN,
    STANCE_COLUMN,
    TOXICITY_COLUMN,
)


def load_pr260_source_record_ids(path: Path | None = None) -> set[str]:
    """Return pull request 260 promotion ``source_record_id`` values.

    Parameters
    ----------
    path
        JSON list of ``source_record_id`` values. Defaults to the committed
        pull request 260 file.

    Returns
    -------
    set[str]
        Promotion ids from pull request 260.
    """
    resolved = path if path is not None else PR260_PROMOTION_IDS_PATH
    payload = json.loads(resolved.read_text())
    return {str(record_id) for record_id in payload}


def build_perspective_candidates(
    cleaned: pd.DataFrame,
    sample: pd.DataFrame,
    medium_upsample: pd.DataFrame,
    pr260_source_record_ids: set[str],
) -> CandidateBuildResult:
    """Return leftover right-medium rows that may be scored and promoted.

    Parameters
    ----------
    cleaned
        Cleaned combined table.
    sample
        The 10,200 post sample.
    medium_upsample
        The 2,000 unused medium posts.
    pr260_source_record_ids
        Pull request 260 promotion ``source_record_id`` values.

    Returns
    -------
    CandidateBuildResult
        Candidate rows and drop counts.

    Raises
    ------
    ValueError
        When fewer than 300 candidates remain.
    """
    leftover_medium = _leftover_medium(cleaned, sample, medium_upsample)
    leftover_right = leftover_medium.loc[leftover_medium[STANCE_COLUMN] == RIGHT_STANCE]
    _require_leftover_right_count(leftover_right)
    candidates, dropped = _drop_pr260_ids(leftover_right, pr260_source_record_ids)
    _require_enough_candidates(candidates)
    return CandidateBuildResult(
        rows=candidates.reset_index(drop=True),
        leftover_right_medium_after_upsample=len(leftover_right),
        pr260_ids_dropped=dropped,
    )


def _require_leftover_right_count(leftover_right: pd.DataFrame) -> None:
    if len(leftover_right) != EXPECTED_LEFTOVER_RIGHT_MEDIUM_AFTER_UPSAMPLE:
        raise ValueError(
            f"leftover_right_medium_after_upsample={len(leftover_right)} "
            f"expected={EXPECTED_LEFTOVER_RIGHT_MEDIUM_AFTER_UPSAMPLE}"
        )


def _leftover_medium(
    cleaned: pd.DataFrame,
    sample: pd.DataFrame,
    medium_upsample: pd.DataFrame,
) -> pd.DataFrame:
    unused = _drop_record_ids(cleaned, sample)
    unused = _drop_record_ids(unused, medium_upsample)
    return unused.loc[unused[TOXICITY_COLUMN] == MEDIUM_TOXICITY]


def _drop_record_ids(frame: pd.DataFrame, excluded: pd.DataFrame) -> pd.DataFrame:
    excluded_ids = set(excluded[RECORD_ID_COLUMN].map(str))
    is_kept = ~frame[RECORD_ID_COLUMN].map(str).isin(list(excluded_ids))
    return frame.loc[is_kept]


def _drop_pr260_ids(
    frame: pd.DataFrame, pr260_source_record_ids: set[str]
) -> tuple[pd.DataFrame, int]:
    is_kept = ~frame[SOURCE_RECORD_ID_COLUMN].map(str).isin(list(pr260_source_record_ids))
    dropped = len(frame) - int(is_kept.sum())
    return frame.loc[is_kept], dropped


def _require_enough_candidates(candidates: pd.DataFrame) -> None:
    if len(candidates) < MIN_CANDIDATES:
        raise ValueError(
            f"candidate_rows={len(candidates)} needed={MIN_CANDIDATES}"
        )
