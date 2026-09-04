"""Tests for experiment path helpers."""

from pathlib import Path

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    CLASSIFIER_NAMES,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.paths import (
    category_dir,
    output_parquet_path,
    training_data_root,
)


class TestOutputParquetPath:
    """Tests for output_parquet_path."""

    def test_output_parquet_path_suffix(self):
        """Verify the built parquet path matches the locked filename shape."""
        classifier_name = "is_political"
        dataset_id = "bluesky_abc"
        timestamp = "2026_09_04-12:00:00"
        expected_suffix = (
            "training_data/is_political/bluesky_abc_2026_09_04-12:00:00.parquet"
        )

        result = output_parquet_path(classifier_name, dataset_id, timestamp)

        assert str(result).endswith(expected_suffix)


class TestCategoryDir:
    """Tests for category_dir."""

    def test_category_folders_exist(self):
        """Verify every classifier folder exists under training_data."""
        training_root = training_data_root()

        for classifier_name in CLASSIFIER_NAMES:
            expected = training_root / classifier_name
            result = category_dir(classifier_name)

            assert result == expected
            assert result.is_dir()
