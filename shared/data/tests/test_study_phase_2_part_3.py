"""Tests for the September 2026 study datasets in the shared registry.

given the phase 2 part 3 names
when get_dataset is called
then the results entry points at results/full.csv with kind results
and the stimuli entry points at stimuli/flips.csv with kind stimuli
and study_phase is study_phase_2_part_3

given the registered stimuli CSV
when load_dataset is called for STUDY_PHASE_2_PART_3_STIMULI
then the frame has 18899 rows and the five catalog columns

given the registered results CSV
when load_dataset is called for STUDY_PHASE_2_PART_3_RESULTS_FULL
then the frame has 131175 rows, 3875 prolific accounts, and trial columns

when get_dataset is called with an unknown name
then KeyError is raised
"""

from __future__ import annotations

import pandas as pd
import pytest

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_3,
    STUDY_PHASE_2_PART_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_3_RESULTS_RELATIVE_PATH,
    STUDY_PHASE_2_PART_3_STIMULI,
    STUDY_PHASE_2_PART_3_RESULTS_ROW_COUNT,
    STUDY_PHASE_2_PART_3_RESULTS_USER_COUNT,
    STUDY_PHASE_2_PART_3_STIMULI_COLUMNS,
    STUDY_PHASE_2_PART_3_STIMULI_RELATIVE_PATH,
    STUDY_PHASE_2_PART_3_STIMULI_ROW_COUNT,
    get_dataset,
)


class TestGetDataset:
    """Tests for get_dataset."""

    def test_results_entry_points_at_phase_3_export(self) -> None:
        """Phase 2 part 3 results resolve to the September export CSV."""
        entry = get_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL)

        assert entry.name == STUDY_PHASE_2_PART_3_RESULTS_FULL
        assert entry.relative_path == STUDY_PHASE_2_PART_3_RESULTS_RELATIVE_PATH
        assert entry.kind == "results"
        assert entry.study_phase == STUDY_PHASE_2_PART_3

    def test_stimuli_entry_points_at_phase_3_catalog(self) -> None:
        """Phase 2 part 3 stimuli resolve to the September catalog CSV."""
        entry = get_dataset(STUDY_PHASE_2_PART_3_STIMULI)

        assert entry.name == STUDY_PHASE_2_PART_3_STIMULI
        assert entry.relative_path == STUDY_PHASE_2_PART_3_STIMULI_RELATIVE_PATH
        assert entry.kind == "stimuli"
        assert entry.study_phase == STUDY_PHASE_2_PART_3

    def test_unknown_name_raises_key_error(self) -> None:
        """An unregistered dataset name raises KeyError."""
        with pytest.raises(KeyError, match="Unknown dataset"):
            get_dataset("NOT_A_STUDY_DATASET")


class TestLoadDataset:
    """Tests for load_dataset on the September 2026 tables."""

    def test_stimuli_catalog_shape(self) -> None:
        """The September catalog has the pinned columns and row count."""
        result = load_dataset(STUDY_PHASE_2_PART_3_STIMULI)

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == list(STUDY_PHASE_2_PART_3_STIMULI_COLUMNS)
        assert len(result) == STUDY_PHASE_2_PART_3_STIMULI_ROW_COUNT
        assert result["post_primary_key"].is_unique

    def test_results_export_has_trial_columns(self) -> None:
        """The September export includes the trial columns callers join on."""
        result = load_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL)

        assert isinstance(result, pd.DataFrame)
        assert {"prolific_id", "trial_type", "decision"}.issubset(result.columns)
        assert len(result) == STUDY_PHASE_2_PART_3_RESULTS_ROW_COUNT
        assert result["prolific_id"].nunique() == STUDY_PHASE_2_PART_3_RESULTS_USER_COUNT
