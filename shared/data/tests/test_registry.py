"""Tests for the shared study dataset catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from shared.data.registry import (
    DATASETS,
    STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_AND_3_STIMULI,
    STUDY_PHASE_2_PART_2_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_STIMULI,
    STUDY_PHASE_2_PART_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_3_STIMULI,
    DatasetEntry,
    get_dataset,
    resolve_path,
)


class TestDatasetEntry:
    """Tests for DatasetEntry construction."""

    def test_rejects_missing_path_and_sources(self) -> None:
        """A catalog row must be file-backed or a union, not neither."""
        with pytest.raises(ValueError, match="exactly one"):
            DatasetEntry(
                name="EMPTY",
                relative_path=None,
                kind="results",
                study_phase="test",
            )

    def test_rejects_path_and_sources_together(self) -> None:
        """A catalog row cannot be both file-backed and a union."""
        with pytest.raises(ValueError, match="exactly one"):
            DatasetEntry(
                name="BOTH",
                relative_path=Path("shared/data/raw/example.csv"),
                kind="results",
                study_phase="test",
                source_names=("OTHER",),
            )


class TestPart2And3UnionRegistry:
    """Tests for the combined Part 2 and Part 3 catalog rows."""

    def test_results_union_sources(self) -> None:
        """The combined results table is Part 2 then Part 3 session exports."""
        entry = get_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL)

        assert entry.kind == "results"
        assert entry.is_union
        assert entry.source_names == (
            STUDY_PHASE_2_PART_2_RESULTS_FULL,
            STUDY_PHASE_2_PART_3_RESULTS_FULL,
        )
        assert DATASETS[STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL] is entry

    def test_stimuli_union_sources(self) -> None:
        """The combined catalog is Part 2 then Part 3 stimulus tables."""
        entry = get_dataset(STUDY_PHASE_2_PART_2_AND_3_STIMULI)

        assert entry.kind == "stimuli"
        assert entry.is_union
        assert entry.source_names == (
            STUDY_PHASE_2_PART_2_STIMULI,
            STUDY_PHASE_2_PART_3_STIMULI,
        )

    def test_resolve_path_rejects_union_names(self) -> None:
        """Union datasets have no single CSV, so path resolution is invalid."""
        with pytest.raises(ValueError, match="no single file"):
            resolve_path(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL)
