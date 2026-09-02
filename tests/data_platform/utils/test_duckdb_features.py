from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.utils.dataset import ValidDataFormats
from data_platform.utils.duckdb_features import feature_file_path, feature_glob
from data_platform.utils.storage import format_filename

FEATURE_STEM = "is_political"


class TestFormatFilename:
    """Tests for format_filename()."""

    @pytest.mark.parametrize(
        "file_format,expected",
        [
            (ValidDataFormats.CSV, "is_political.csv"),
            (ValidDataFormats.PARQUET, "is_political.parquet"),
        ],
    )
    def test_appends_dataset_format_suffix(
        self, file_format: ValidDataFormats, expected: str
    ) -> None:
        result = format_filename(FEATURE_STEM, file_format)

        assert result == expected


class TestFeatureFilePath:
    """Tests for feature_file_path()."""

    def test_joins_root_with_format_filename(self, tmp_path: Path) -> None:
        features_root = tmp_path / "features"
        expected = features_root / "is_political.csv"

        result = feature_file_path(features_root, FEATURE_STEM)

        assert result == expected


class TestFeatureGlob:
    """Tests for feature_glob()."""

    def test_returns_posix_path_for_duckdb(self, tmp_path: Path) -> None:
        features_root = tmp_path / "features"
        expected = feature_file_path(features_root, FEATURE_STEM).as_posix()

        result = feature_glob(features_root, FEATURE_STEM)

        assert result == expected
