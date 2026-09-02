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
    """Return ``features/{timestamp}/``, creating a new run when ``run_dir_name`` is omitted."""
    raise NotImplementedError
