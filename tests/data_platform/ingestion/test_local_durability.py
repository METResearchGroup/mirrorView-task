"""Tests for local-disk sync durability helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.ingestion.sync_checkpoint import (
    SyncStatus,
    TaskStatus,
    finalize_local_disk_sync,
)
from data_platform.utils.storage import StorageStage, TwitterStorageManager


class TestFinalizeLocalDiskSync:
    """Tests for finalize_local_disk_sync()."""

    def test_completed_run_sets_sync_status_completed(self, data_root: Path) -> None:
        dataset_id = "twitter_00000000-0000-0000-0000-000000000001"
        storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
        run_dir = storage.create_new_run_dir("2026_01_01-00:00:00")
        metadata = {
            "sync_status": SyncStatus.IN_PROGRESS.value,
            "tasks": {"kw1": {"status": TaskStatus.COMPLETED.value}},
        }

        finalize_local_disk_sync(storage, run_dir, metadata)

        loaded = storage.load_run_metadata(run_dir)
        assert loaded["sync_status"] == SyncStatus.COMPLETED.value
        storage.require_all_runs_complete()

    def test_incomplete_run_keeps_sync_status_in_progress(self, data_root: Path) -> None:
        dataset_id = "twitter_00000000-0000-0000-0000-000000000002"
        storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
        run_dir = storage.create_new_run_dir("2026_01_01-00:00:00")
        metadata = {
            "sync_status": SyncStatus.IN_PROGRESS.value,
            "tasks": {
                "kw1": {"status": TaskStatus.COMPLETED.value},
                "kw2": {"status": TaskStatus.PENDING.value},
            },
        }

        finalize_local_disk_sync(storage, run_dir, metadata)

        loaded = storage.load_run_metadata(run_dir)
        assert loaded["sync_status"] == SyncStatus.IN_PROGRESS.value
        with pytest.raises(RuntimeError):
            storage.require_all_runs_complete()
