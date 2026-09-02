"""Resolve timestamped feature-generation run directories.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from data_platform.generate_features.run_layout import resolve_features_run_dir"
"""

from __future__ import annotations

from pathlib import Path

from data_platform.utils.storage import StorageManager


def resolve_features_run_dir(
    feature_storage: StorageManager,
    run_dir_name: str | None,
) -> Path:
    """Return ``features/{timestamp}/``, creating the directory if needed.

    Parameters
    ----------
    feature_storage
        Storage manager whose ``root_dir`` is the features stage root.
    run_dir_name
        Existing or new timestamp folder name. When omitted, a new run is created.

    Returns
    -------
    Path
        Absolute path to the timestamped feature run directory.
    """
    if run_dir_name is None:
        return feature_storage.create_new_run_dir()
    return feature_storage.create_new_run_dir(run_dir_name)
