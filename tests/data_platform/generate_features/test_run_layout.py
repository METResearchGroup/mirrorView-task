from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.run_layout import resolve_features_run_dir
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from tests.data_platform.constants import FEATURES_DATASET_ID, PREPROCESSED_RUN_DIR


class TestResolveFeaturesRunDir:
    """Tests for resolve_features_run_dir()."""

    def test_creates_timestamped_child_when_name_omitted(self, data_root: Path) -> None:
        """Given no run name, when resolving, then a new features/{timestamp}/ dir exists."""
        storage = BlueskyStorageManager(
            StorageStage.FEATURES,
            FEATURES_DATASET_ID,
            records_filename="features",
        )

        result = resolve_features_run_dir(storage, None)

        assert result.parent == storage.root_dir
        assert result.is_dir()
        assert result.name != "features"

    def test_resumes_named_run_dir(self, data_root: Path) -> None:
        """Given a run directory name, when resolving, then that child dir is used."""
        storage = BlueskyStorageManager(
            StorageStage.FEATURES,
            FEATURES_DATASET_ID,
            records_filename="features",
        )
        expected = storage.root_dir / PREPROCESSED_RUN_DIR
        expected.mkdir(parents=True)

        result = resolve_features_run_dir(storage, PREPROCESSED_RUN_DIR)

        assert result == expected

    def test_creates_named_run_dir_when_missing(self, data_root: Path) -> None:
        """Given a run name that does not exist, when resolving, then that directory is created."""
        storage = BlueskyStorageManager(
            StorageStage.FEATURES,
            FEATURES_DATASET_ID,
            records_filename="features",
        )

        result = resolve_features_run_dir(storage, PREPROCESSED_RUN_DIR)

        assert result == storage.root_dir / PREPROCESSED_RUN_DIR
        assert result.is_dir()
