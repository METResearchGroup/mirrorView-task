from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_platform.utils.dataset import dataset_root
from data_platform.utils.storage import METADATA_FILENAME, BlueskyStorageManager, StorageStage
from tests.data_platform.constants import VALID_DATASET_ID


@pytest.fixture
def bluesky_storage(data_root) -> BlueskyStorageManager:
    return BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)


def write_stage_metadata(
    run_dir: Path,
    *,
    sync_status: str | None = "completed",
) -> Path:
    """Write a metadata.json under run_dir for local completeness checks."""
    run_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {}
    if sync_status is not None:
        payload["sync_status"] = sync_status
    path = run_dir / METADATA_FILENAME
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def seed_complete_dataset() -> Path:
    """Write metadata.json files for every stage so disk-cleanup tests have real files."""
    for stage in (StorageStage.RAW, StorageStage.PREPROCESSED, StorageStage.CURATED):
        storage = BlueskyStorageManager(stage, VALID_DATASET_ID)
        write_stage_metadata(storage.create_new_run_dir("2026_01_01-00:00:00"))
    write_stage_metadata(
        dataset_root("bluesky", VALID_DATASET_ID) / StorageStage.FEATURES,
        sync_status=None,
    )
    return dataset_root("bluesky", VALID_DATASET_ID)
