"""Resolve feature-label file paths using StorageManager filename rules.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.utils.duckdb_features import feature_glob"
"""

from __future__ import annotations

from pathlib import Path

from data_platform.utils.dataset import ValidDataFormats
from data_platform.utils.storage import format_filename

DEFAULT_FEATURE_EXT = ".csv"


def feature_file_path(
    features_root: Path,
    feature_name: str,
    ext: str = DEFAULT_FEATURE_EXT,
) -> Path:
    """Return the feature label file path under the features root."""
    file_format = ValidDataFormats(ext.removeprefix("."))
    return features_root / format_filename(feature_name, file_format)


def feature_glob(
    features_root: Path,
    feature_name: str,
    ext: str = DEFAULT_FEATURE_EXT,
) -> str:
    """Return a POSIX path string for DuckDB on the feature file."""
    return feature_file_path(features_root, feature_name, ext).as_posix()
