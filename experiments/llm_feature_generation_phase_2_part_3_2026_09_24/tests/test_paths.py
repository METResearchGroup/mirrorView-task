"""Tests for experiment path helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import paths


class TestExperimentRoot:
    """Tests for EXPERIMENT_ROOT."""

    def test_experiment_root_is_package_parent(self) -> None:
        """EXPERIMENT_ROOT names the experiment folder."""
        assert paths.EXPERIMENT_ROOT.name == "llm_feature_generation_phase_2_part_3_2026_09_24"


class TestCohortDir:
    """Tests for cohort_dir."""

    def test_cohort_dir_for_each_arm(self) -> None:
        """cohort_dir returns outputs/<arm>/cohort under the experiment root."""
        result = paths.cohort_dir("original_only")
        assert str(result).endswith("outputs/original_only/cohort")


class TestLatestTimestampSubdir:
    """Tests for latest_timestamp_subdir."""

    def test_latest_timestamp_subdir_picks_max_name(
        self, tmp_path: Path
    ) -> None:
        """The lexicographically latest timestamp directory is returned."""
        early = tmp_path / "2026-09-24T10-00-00"
        late = tmp_path / "2026-09-24T11-00-00"
        early.mkdir()
        late.mkdir()
        result = paths.latest_timestamp_subdir(tmp_path)
        assert result == late

    def test_latest_timestamp_subdir_empty_raises(self, tmp_path: Path) -> None:
        """An empty parent directory raises FileNotFoundError."""
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(FileNotFoundError):
            paths.latest_timestamp_subdir(empty)
