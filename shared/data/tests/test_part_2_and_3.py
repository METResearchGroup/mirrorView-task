"""The combined Part 2 and Part 3 study tables are registered CSVs."""

from __future__ import annotations

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_AND_3_STIMULI,
    resolve_path,
)

RESULTS_ROW_COUNT = 168871
PROLIFIC_ACCOUNT_COUNT = 5051
STIMULI_ROW_COUNT = 20000


def test_combined_results_csv() -> None:
    """The combined session export is the Part 2 file followed by Part 3."""
    frame = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False)

    assert resolve_path(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL).is_file()
    assert len(frame) == RESULTS_ROW_COUNT
    assert frame["prolific_id"].nunique() == PROLIFIC_ACCOUNT_COUNT
    assert "attention_check_passed" in frame.columns


def test_combined_stimuli_csv() -> None:
    """The combined catalog has one row per post across both collections."""
    frame = load_dataset(STUDY_PHASE_2_PART_2_AND_3_STIMULI)

    assert resolve_path(STUDY_PHASE_2_PART_2_AND_3_STIMULI).is_file()
    assert len(frame) == STIMULI_ROW_COUNT
    assert frame["post_primary_key"].is_unique
