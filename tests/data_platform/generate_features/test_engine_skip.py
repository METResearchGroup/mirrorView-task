from __future__ import annotations

from pydantic import BaseModel

from data_platform.generate_features.engines.base import (
    filter_seen_tasks,
    load_seen_ids_from_features_dir,
)
from data_platform.generate_features.models import LabelTask
from data_platform.utils.storage import StorageManager
from tests.data_platform.conftest import write_feature_csv
from tests.data_platform.constants import (
    FEATURES_DATASET_ID,
    LABEL_TIMESTAMP,
    URI_POST_A,
    URI_POST_B,
)

ID_COLUMN_URI = "uri"


def _feature_storage(dataset_id: str = FEATURES_DATASET_ID) -> StorageManager:
    return StorageManager(
        "bluesky",
        "features",
        BaseModel,
        dataset_id,
        records_filename="is_political",
    )


class TestLoadSeenIdsFromFeaturesDir:
    """Tests for load_seen_ids_from_features_dir()."""

    def test_reads_ids_from_parameterized_column(self, data_root) -> None:
        feature_storage = _feature_storage()
        write_feature_csv(
            feature_storage.root_dir,
            "is_political",
            [
                {
                    ID_COLUMN_URI: URI_POST_A,
                    "label_timestamp": LABEL_TIMESTAMP,
                    "is_political": True,
                }
            ],
        )
        expected = {URI_POST_A}

        result = load_seen_ids_from_features_dir(feature_storage, ID_COLUMN_URI)

        assert result == expected

    def test_returns_empty_set_when_feature_file_is_missing(self, data_root) -> None:
        feature_storage = _feature_storage()
        feature_storage.root_dir.mkdir(parents=True, exist_ok=True)
        expected: set[str] = set()

        result = load_seen_ids_from_features_dir(feature_storage, ID_COLUMN_URI)

        assert result == expected


class TestFilterSeenTasks:
    """Tests for filter_seen_tasks()."""

    def test_drops_tasks_whose_id_is_already_labeled(self, data_root) -> None:
        feature_storage = _feature_storage()
        write_feature_csv(
            feature_storage.root_dir,
            "is_political",
            [
                {
                    ID_COLUMN_URI: URI_POST_A,
                    "label_timestamp": LABEL_TIMESTAMP,
                    "is_political": True,
                }
            ],
        )
        tasks = [
            LabelTask(uri=URI_POST_A, text="one"),
            LabelTask(uri=URI_POST_B, text="two"),
        ]

        result = filter_seen_tasks(tasks, feature_storage, ID_COLUMN_URI)

        assert [task.uri for task in result] == [URI_POST_B]

    def test_keeps_all_tasks_when_no_labels_exist(self, data_root) -> None:
        feature_storage = _feature_storage()
        feature_storage.root_dir.mkdir(parents=True, exist_ok=True)
        tasks = [LabelTask(uri=URI_POST_A, text="one")]

        result = filter_seen_tasks(tasks, feature_storage, ID_COLUMN_URI)

        assert result == tasks
