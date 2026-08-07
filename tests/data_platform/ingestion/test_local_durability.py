"""Tests for local-disk sync durability helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.ingestion.sync_checkpoint import (
    SyncStatus,
    TaskStatus,
    finalize_local_disk_sync,
)
from data_platform.utils.gate_checks import require_all_runs_uploaded
from data_platform.utils.local_durability import is_bluesky_s3_upload_enabled
from data_platform.utils.storage import StorageStage, TwitterStorageManager
from lib.load_env_vars import EnvVarsContainer


class TestFinalizeLocalDiskSync:
    """Tests for finalize_local_disk_sync()."""

    def test_completed_run_sets_s3_upload_status_true(self, data_root: Path) -> None:
        """Completed local Twitter sync metadata is marked durable for preprocess."""
        dataset_id = "twitter_00000000-0000-0000-0000-000000000001"
        storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
        run_dir = storage.create_new_run_dir("2026_01_01-00:00:00")
        metadata = {
            "sync_status": SyncStatus.IN_PROGRESS.value,
            "s3_upload_status": False,
            "tasks": {"kw1": {"status": TaskStatus.COMPLETED.value}},
        }

        finalize_local_disk_sync(storage, run_dir, metadata)

        loaded = storage.load_run_metadata(run_dir)
        assert loaded["s3_upload_status"] is True
        assert loaded["sync_status"] == SyncStatus.COMPLETED.value
        require_all_runs_uploaded(storage, dataset_id)

    def test_incomplete_run_does_not_set_s3_upload_status(self, data_root: Path) -> None:
        """In-progress runs keep s3_upload_status false so the preprocess gate still fails."""
        dataset_id = "twitter_00000000-0000-0000-0000-000000000002"
        storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
        run_dir = storage.create_new_run_dir("2026_01_01-00:00:00")
        metadata = {
            "sync_status": SyncStatus.IN_PROGRESS.value,
            "s3_upload_status": False,
            "tasks": {
                "kw1": {"status": TaskStatus.COMPLETED.value},
                "kw2": {"status": TaskStatus.PENDING.value},
            },
        }

        finalize_local_disk_sync(storage, run_dir, metadata)

        loaded = storage.load_run_metadata(run_dir)
        assert loaded["s3_upload_status"] is False
        assert loaded["sync_status"] == SyncStatus.IN_PROGRESS.value
        with pytest.raises(RuntimeError):
            require_all_runs_uploaded(storage, dataset_id)


class TestIsBlueskyS3UploadEnabled:
    """Tests for is_bluesky_s3_upload_enabled()."""

    def setup_method(self) -> None:
        EnvVarsContainer._instance = None

    def teardown_method(self) -> None:
        EnvVarsContainer._instance = None

    def test_default_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unset env disables Bluesky S3 upload."""
        monkeypatch.delenv("DATA_PLATFORM_BLUESKY_S3_UPLOAD", raising=False)
        EnvVarsContainer._instance = None
        assert is_bluesky_s3_upload_enabled() is False

    @pytest.mark.parametrize("value", ["0", "false", "FALSE", ""])
    def test_falsy_values_disabled(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        """Common falsy strings keep Bluesky S3 upload disabled."""
        monkeypatch.setenv("DATA_PLATFORM_BLUESKY_S3_UPLOAD", value)
        EnvVarsContainer._instance = None
        assert is_bluesky_s3_upload_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE"])
    def test_truthy_values_enabled(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        """Opt-in values enable Bluesky S3 upload."""
        monkeypatch.setenv("DATA_PLATFORM_BLUESKY_S3_UPLOAD", value)
        EnvVarsContainer._instance = None
        assert is_bluesky_s3_upload_enabled() is True
