from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.utils.dataset import dataset_root
from data_platform.utils.disk_cleanup import delete_dataset_local_files
from tests.data_platform.constants import VALID_DATASET_ID
from tests.data_platform.utils.conftest import seed_complete_dataset


def test_delete_dataset_local_files_removes_directory_when_root_exists(data_root: Path) -> None:
    root = seed_complete_dataset()
    assert root.exists()

    delete_dataset_local_files("bluesky", VALID_DATASET_ID)

    assert not root.exists()


def test_delete_dataset_local_files_raises_file_not_found_when_dataset_root_missing(
    data_root: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        delete_dataset_local_files("bluesky", VALID_DATASET_ID)
