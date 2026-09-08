"""Drop previously used posts, duplicate ids, and duplicate text."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from data_platform.preprocessing.previously_used_stimuli import (
    STIMULI_DATASET_KIND,
    load_previously_used_stimuli_ids,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CANDIDATE_COLUMNS,
    CANDIDATE_SORT_COLUMNS,
    RECORD_ID_COLUMN,
    TEXT_COLUMN,
    CleanupSummary,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import DATASETS, DatasetEntry

ORIGINAL_TEXT_COLUMN = "original_text"


def cleanup_raw_candidate_dataset(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, CleanupSummary]:
    """Return the cleaned table and drop-count summary.

    Parameters
    ----------
    frame
        Combined candidate table.

    Returns
    -------
    tuple[pd.DataFrame, CleanupSummary]
        Cleaned rows with a reset index, then the drop counts.

    Raises
    ------
    ValueError
        When a required column is missing.
    """
    _require_columns(frame)
    sorted_frame = _sort_candidates(frame)
    without_ids, dropped_ids = _drop_previously_used_ids(sorted_frame)
    without_text, dropped_text = _drop_previously_used_text(without_ids)
    without_dup_ids, dropped_dup_ids = _drop_duplicate_record_ids(without_text)
    cleaned, dropped_dup_text = _drop_duplicate_text(without_dup_ids)
    summary = _cleanup_summary(
        len(frame),
        dropped_ids,
        dropped_text,
        dropped_dup_ids,
        dropped_dup_text,
        len(cleaned),
    )
    return cleaned, summary


def _require_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in CANDIDATE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"missing columns {missing}")


def _sort_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        list(CANDIDATE_SORT_COLUMNS),
        kind="mergesort",
    ).reset_index(drop=True)


def _drop_previously_used_ids(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    previous_ids = load_previously_used_stimuli_ids(DATASETS)
    return _drop_matching(frame, RECORD_ID_COLUMN, previous_ids)


def _drop_previously_used_text(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    previous_text = _previously_used_original_text(DATASETS)
    return _drop_matching(frame, TEXT_COLUMN, previous_text)


def _previously_used_original_text(
    datasets: Mapping[str, DatasetEntry],
) -> set[str]:
    texts: set[str] = set()
    for entry in datasets.values():
        if entry.kind != STIMULI_DATASET_KIND:
            continue
        frame = load_dataset(entry.name)
        texts |= set(frame[ORIGINAL_TEXT_COLUMN].dropna().map(str))
    return texts


def _drop_matching(
    frame: pd.DataFrame,
    column: str,
    values: set[str],
) -> tuple[pd.DataFrame, int]:
    is_kept = ~frame[column].map(str).isin(list(values))
    dropped = len(frame) - int(is_kept.sum())
    return frame.loc[is_kept].reset_index(drop=True), dropped


def _drop_duplicate_record_ids(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    raise NotImplementedError


def _drop_duplicate_text(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    raise NotImplementedError


def _cleanup_summary(
    candidate_rows: int,
    dropped_previous_ids: int,
    dropped_previous_text: int,
    dropped_duplicate_ids: int,
    dropped_duplicate_text: int,
    cleaned_rows: int,
) -> CleanupSummary:
    return CleanupSummary(
        candidate_rows=candidate_rows,
        dropped_previous_ids=dropped_previous_ids,
        dropped_previous_text=dropped_previous_text,
        dropped_duplicate_ids=dropped_duplicate_ids,
        dropped_duplicate_text=dropped_duplicate_text,
        cleaned_rows=cleaned_rows,
    )
