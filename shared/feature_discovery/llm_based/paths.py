"""Timestamp helpers for LLM-based feature-discovery stage runs.

Run from repo root::

    PYTHONPATH=. uv run python -c "
    from shared.feature_discovery.llm_based.paths import make_run_timestamp, latest_timestamp_subdir
    print(make_run_timestamp())
    "
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M-%S"


def make_run_timestamp() -> str:
    """Return a local ISO-like timestamp for stage output folders.

    Returns
    -------
    str
        Timestamp formatted as ``YYYY-MM-DDTHH-MM-SS``.
    """
    return datetime.now().strftime(_TIMESTAMP_FORMAT)


def latest_timestamp_subdir(parent: Path) -> Path:
    """Return the newest child directory under ``parent``.

    Parameters
    ----------
    parent
        Directory that contains timestamped run folders.

    Returns
    -------
    Path
        Latest child directory by name sort.

    Raises
    ------
    FileNotFoundError
        When parent is missing or has no child directories.
    """
    if not parent.is_dir():
        raise FileNotFoundError(f"Directory not found: {parent}")
    children = [path for path in parent.iterdir() if path.is_dir()]
    if not children:
        raise FileNotFoundError(f"No timestamp subdirectories under {parent}")
    return sorted(children, key=lambda path: path.name)[-1]
