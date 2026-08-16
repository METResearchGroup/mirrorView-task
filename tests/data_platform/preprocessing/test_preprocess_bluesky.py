from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from data_platform.preprocessing.preprocess_bluesky import preprocess_records
from tests.data_platform.constants import VALID_DATASET_ID


def _write_raw_run(
    data_root: Path,
    dataset_id: str,
    run_name: str,
    *,
    sync_status: str,
) -> Path:
    run_dir = data_root / "bluesky" / dataset_id / "raw" / run_name
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps({"sync_status": sync_status}), encoding="utf-8"
    )
    return run_dir


class TestPreprocessGates:
    def test_gate_fails_if_no_raw_runs(self, data_root: Path) -> None:
        with pytest.raises(FileNotFoundError):
            preprocess_records(VALID_DATASET_ID)

    def test_gate_fails_if_raw_not_complete(self, data_root: Path) -> None:
        _write_raw_run(
            data_root, VALID_DATASET_ID, "2026_01_01-00:00:00", sync_status="in_progress"
        )
        with pytest.raises(RuntimeError):
            preprocess_records(VALID_DATASET_ID)


class TestPreprocessRun:
    def test_preprocess_delegates_to_runner(
        self, data_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_raw_run(
            data_root, VALID_DATASET_ID, "2026_01_01-00:00:00", sync_status="completed"
        )
        expected = data_root / "bluesky" / VALID_DATASET_ID / "preprocessed" / "2026_01_01-00:05:00"
        mock_run = MagicMock(return_value=expected)
        monkeypatch.setattr(
            "data_platform.preprocessing.preprocess_bluesky.run_preprocess_records",
            mock_run,
        )

        result = preprocess_records(VALID_DATASET_ID)

        mock_run.assert_called_once()
        assert result == expected
