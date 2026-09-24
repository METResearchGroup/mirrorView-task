"""Tests for loading registered study tables, including Part 2+3 unions."""

from __future__ import annotations

import pytest

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_AND_3_STIMULI,
    STUDY_PHASE_2_PART_2_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_STIMULI,
    STUDY_PHASE_2_PART_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_3_STIMULI,
)

COMBINED_RESULTS_ROW_COUNT = 168871
COMBINED_PROLIFIC_ACCOUNT_COUNT = 5051
COMBINED_STIMULI_ROW_COUNT = 20000
PART3_ONLY_RESULTS_COLUMNS = (
    "attention_check_passed",
    "attention_check_selected",
)


class TestLoadUnionDataset:
    """Tests for load_dataset() on the combined Part 2 and Part 3 names."""

    def test_combined_results_is_the_row_union(self) -> None:
        """The combined export has every Part 2 and Part 3 session row."""
        combined = load_dataset(
            STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False
        )
        part2 = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
        part3 = load_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL, low_memory=False)

        assert len(combined) == COMBINED_RESULTS_ROW_COUNT
        assert len(combined) == len(part2) + len(part3)
        assert combined["prolific_id"].nunique() == COMBINED_PROLIFIC_ACCOUNT_COUNT
        for column in PART3_ONLY_RESULTS_COLUMNS:
            assert column in combined.columns
            assert combined[column].head(len(part2)).isna().all()

    def test_combined_stimuli_is_the_unique_post_union(self) -> None:
        """The combined catalog has 20,000 posts and no duplicate keys."""
        combined = load_dataset(STUDY_PHASE_2_PART_2_AND_3_STIMULI)
        part2 = load_dataset(STUDY_PHASE_2_PART_2_STIMULI)
        part3 = load_dataset(STUDY_PHASE_2_PART_3_STIMULI)

        assert len(combined) == COMBINED_STIMULI_ROW_COUNT
        assert combined["post_primary_key"].is_unique
        expected_keys = set(part2["post_primary_key"]).union(part3["post_primary_key"])
        assert set(combined["post_primary_key"]) == expected_keys

    def test_unknown_name_still_raises_key_error(self) -> None:
        """Unknown names fail the same way as file-backed datasets."""
        with pytest.raises(KeyError, match="NOT_A_DATASET"):
            load_dataset("NOT_A_DATASET")
