from __future__ import annotations

from pathlib import Path

from data_platform.utils.duckdb_features import feature_glob
from tests.data_platform.constants import LABEL_TIMESTAMP


class TestFeatureGlob:
    """Tests for feature_glob()."""

    def test_matches_timestamped_feature_csv(self, tmp_path: Path) -> None:
        """Given a features root, when building a glob, then it matches features/{timestamp}/{name}.csv."""
        features_root = tmp_path / "features"
        pattern = feature_glob(features_root, "is_political")

        assert f"/{LABEL_TIMESTAMP}/" not in pattern
        assert pattern.endswith("*/is_political.csv")
        assert features_root.as_posix() in pattern
