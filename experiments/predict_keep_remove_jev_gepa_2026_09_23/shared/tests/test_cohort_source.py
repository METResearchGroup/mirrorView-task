"""Tests for cohort source registry selection."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.cohort import (
    CohortSource,
    registry_dataset_name,
)

STUDY_PHASE_2_PART_3_RESULTS_FULL = "STUDY_PHASE_2_PART_3_RESULTS_FULL"
STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL = "STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL"


class TestRegistryDatasetName:
    """Tests for registry_dataset_name."""

    def test_part3_source_uses_part3_registry_name(self) -> None:
        """Part 3 source maps to the Part 3 registry dataset."""
        result = registry_dataset_name(CohortSource.PART3)
        assert result == STUDY_PHASE_2_PART_3_RESULTS_FULL

    def test_union_source_uses_combined_registry_name(self) -> None:
        """Union source maps to the combined Part 2 and Part 3 registry dataset."""
        result = registry_dataset_name(CohortSource.UNION)
        assert result == STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL
