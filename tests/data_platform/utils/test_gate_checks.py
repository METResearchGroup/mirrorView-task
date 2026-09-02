from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.generate_features.models import FeatureRunMetadata
from data_platform.utils.gate_checks import require_features_complete
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from tests.data_platform.constants import VALID_DATASET_ID
from tests.data_platform.utils.conftest import write_stage_metadata


class TestStorageRequireAllRunsComplete:
    """Tests for StorageManager.require_all_runs_complete()."""

    def test_raises_when_root_missing(self, data_root: Path) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        with pytest.raises(RuntimeError, match="No raw runs found"):
            storage.require_all_runs_complete(VALID_DATASET_ID)

    def test_passes_when_sync_completed(self, data_root: Path) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        write_stage_metadata(storage.create_new_run_dir("2026_01_01-00:00:00"))
        storage.require_all_runs_complete(VALID_DATASET_ID)

    def test_raises_when_sync_incomplete(self, data_root: Path) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        write_stage_metadata(
            storage.create_new_run_dir("2026_01_01-00:00:00"),
            sync_status="in_progress",
        )
        with pytest.raises(RuntimeError, match="complete locally"):
            storage.require_all_runs_complete(VALID_DATASET_ID)

    def test_raises_when_metadata_missing(self, data_root: Path) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        storage.create_new_run_dir("2026_01_01-00:00:00")
        with pytest.raises(RuntimeError, match="complete locally"):
            storage.require_all_runs_complete(VALID_DATASET_ID)

    def test_passes_for_stage_without_sync_status(self, data_root: Path) -> None:
        storage = BlueskyStorageManager(StorageStage.PREPROCESSED, VALID_DATASET_ID)
        write_stage_metadata(storage.create_new_run_dir("2026_01_01-00:00:00"), sync_status=None)
        storage.require_all_runs_complete(VALID_DATASET_ID)


def test_require_features_complete_passes_when_sync_completed() -> None:
    meta = FeatureRunMetadata(
        dataset_id=VALID_DATASET_ID,
        source_preprocessed_runs=[],
        sync_status="completed",
    )
    require_features_complete(meta, VALID_DATASET_ID)


def test_require_features_complete_raises_when_not_completed() -> None:
    meta = FeatureRunMetadata(
        dataset_id=VALID_DATASET_ID,
        source_preprocessed_runs=[],
        sync_status="in_progress",
    )
    with pytest.raises(RuntimeError, match="not complete locally"):
        require_features_complete(meta, VALID_DATASET_ID)
