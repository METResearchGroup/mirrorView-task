from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.utils.gate_checks import require_all_runs_complete, require_features_complete
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from data_platform.generate_features.models import FeatureRunMetadata
from tests.data_platform.constants import VALID_DATASET_ID
from tests.data_platform.utils.conftest import write_stage_metadata


def test_require_all_runs_complete_raises_when_root_missing(data_root: Path) -> None:
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    with pytest.raises(RuntimeError, match="No raw runs found"):
        require_all_runs_complete(storage, VALID_DATASET_ID)


def test_require_all_runs_complete_passes_when_sync_completed(data_root: Path) -> None:
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    write_stage_metadata(storage.create_new_run_dir("2026_01_01-00:00:00"))
    require_all_runs_complete(storage, VALID_DATASET_ID)


def test_require_all_runs_complete_raises_when_sync_incomplete(data_root: Path) -> None:
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    write_stage_metadata(
        storage.create_new_run_dir("2026_01_01-00:00:00"),
        sync_status="in_progress",
    )
    with pytest.raises(RuntimeError, match="complete locally"):
        require_all_runs_complete(storage, VALID_DATASET_ID)


def test_require_all_runs_complete_raises_when_metadata_missing(data_root: Path) -> None:
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    storage.create_new_run_dir("2026_01_01-00:00:00")
    with pytest.raises(RuntimeError, match="complete locally"):
        require_all_runs_complete(storage, VALID_DATASET_ID)


def test_require_all_runs_complete_passes_for_stage_without_sync_status(
    data_root: Path,
) -> None:
    storage = BlueskyStorageManager(StorageStage.PREPROCESSED, VALID_DATASET_ID)
    write_stage_metadata(storage.create_new_run_dir("2026_01_01-00:00:00"), sync_status=None)
    require_all_runs_complete(storage, VALID_DATASET_ID)


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
