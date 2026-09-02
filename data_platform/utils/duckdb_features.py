from __future__ import annotations

from pathlib import Path


def feature_file_path(features_root: Path, feature_name: str, ext: str = ".csv") -> Path:
    """Return a timestamped glob path for a feature file under the features root."""
    return features_root / "*" / f"{feature_name}{ext}"


def feature_glob(features_root: Path, feature_name: str, ext: str = ".csv") -> str:
    """Return a POSIX glob that matches ``features/{timestamp}/{feature}{ext}``."""
    return feature_file_path(features_root, feature_name, ext).as_posix()
