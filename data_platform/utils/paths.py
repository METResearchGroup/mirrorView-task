"""Resolve and round-trip paths relative to the data-platform package.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q
"""

from __future__ import annotations

from pathlib import Path


def resolve_package_path(relative_path: str | Path) -> Path:
    raise NotImplementedError


def to_package_relative(path: str | Path) -> str:
    raise NotImplementedError
