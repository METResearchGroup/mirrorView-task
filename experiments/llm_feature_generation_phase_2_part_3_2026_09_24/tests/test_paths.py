"""Tests for experiment path helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths


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


class TestLatestCohortRunDir:
    """Tests for latest_cohort_run_dir."""

    def test_latest_cohort_run_dir_filters_participant_filter(self, tmp_path: Path) -> None:
        """The newest run matching participant_filter is returned."""
        cohort_root = tmp_path / "outputs" / "original_only" / "cohort"
        all_early = cohort_root / "2026-09-24T10-00-00"
        all_late = cohort_root / "2026-09-24T11-00-00"
        part3_only = cohort_root / "2026-09-24T12-00-00"
        for run_dir in (all_early, all_late, part3_only):
            run_dir.mkdir(parents=True)
            metadata = {"participant_filter": "all"}
            if run_dir == part3_only:
                metadata = {"participant_filter": constants.PARTICIPANT_FILTER_PART3_ONLY}
            (run_dir / constants.METADATA_FILENAME).write_text(
                json.dumps(metadata),
                encoding="utf-8",
            )
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(paths, "EXPERIMENT_ROOT", tmp_path)
            result = paths.latest_cohort_run_dir(
                "original_only",
                constants.PARTICIPANT_FILTER_ALL,
            )
        assert result == all_late

    def test_latest_cohort_run_dir_missing_filter_raises(self, tmp_path: Path) -> None:
        """Missing participant_filter runs raise FileNotFoundError."""
        cohort_root = tmp_path / "outputs" / "paired" / "cohort" / "2026-09-24T10-00-00"
        cohort_root.mkdir(parents=True)
        (cohort_root / constants.METADATA_FILENAME).write_text(
            json.dumps({"participant_filter": constants.PARTICIPANT_FILTER_PART3_ONLY}),
            encoding="utf-8",
        )
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(paths, "EXPERIMENT_ROOT", tmp_path)
            with pytest.raises(FileNotFoundError):
                paths.latest_cohort_run_dir("paired", constants.PARTICIPANT_FILTER_ALL)
