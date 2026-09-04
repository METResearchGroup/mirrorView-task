from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from data_platform.preprocessing.preprocess_bluesky import preprocess_records
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from tests.data_platform.conftest import make_post_row
from tests.data_platform.constants import VALID_DATASET_ID
from tests.data_platform.preprocessing.conftest import (
    EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT,
    LONG_ENGLISH_TEXT,
)


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


VALID_BLUESKY_POST_TEXT = (
    "This is a valid English bluesky post for preprocessing tests without any "
    "links and with enough words that length and language checks both pass here."
)


class TestPreprocessRecordsStandardizedText:
    """Tests that Bluesky preprocess output includes standardized text."""

    def test_preprocessed_rows_include_text(self, data_root: Path) -> None:
        """Kept Bluesky posts still have their original platform text column."""
        dataset_id = VALID_DATASET_ID
        raw_storage = BlueskyStorageManager(StorageStage.RAW, dataset_id)
        run_dir = raw_storage.create_new_run_dir("2026_05_31-10:00:00")
        raw_storage.write_records(
            [make_post_row(text=VALID_BLUESKY_POST_TEXT)],
            run_dir,
        )
        raw_storage.write_run_metadata(
            run_dir,
            {"sync_status": "completed", "row_count": 1},
        )

        output_dir = preprocess_records(dataset_id)
        output = BlueskyStorageManager(StorageStage.PREPROCESSED, dataset_id).load_records(
            output_dir
        )

        assert len(output) == 1
        assert output.iloc[0]["text"] == VALID_BLUESKY_POST_TEXT
        assert output.iloc[0]["author_handle"] == "a.bsky.social"
        assert output.iloc[0]["source_record_id"] == output.iloc[0]["uri"]
        assert "author_id" not in output.columns


    def test_preprocessed_rows_truncate_long_text(self, data_root: Path) -> None:
        """Long Bluesky posts are kept after truncation to a complete-sentence window."""
        dataset_id = VALID_DATASET_ID
        raw_storage = BlueskyStorageManager(StorageStage.RAW, dataset_id)
        run_dir = raw_storage.create_new_run_dir("2026_05_31-15:00:00")
        raw_storage.write_records(
            [make_post_row(text=LONG_ENGLISH_TEXT)],
            run_dir,
        )
        raw_storage.write_run_metadata(
            run_dir,
            {"sync_status": "completed", "row_count": 1},
        )
        expected = EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT

        output_dir = preprocess_records(dataset_id)
        output = BlueskyStorageManager(StorageStage.PREPROCESSED, dataset_id).load_records(
            output_dir
        )

        assert len(output) == 1
        assert output.iloc[0]["text"] == expected
