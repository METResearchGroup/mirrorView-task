"""Resolve and round-trip paths relative to the data-platform package.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q
"""

from __future__ import annotations

from pathlib import Path


def resolve_package_path(relative_path: str | Path) -> Path:
    """Return the resolved path of a location under the data-platform package.

    The target file does not need to exist.

    Parameters
    ----------
    relative_path
        Path relative to ``PACKAGE_ROOT``. Must not be absolute and must not
        contain ``..`` parts.

    Returns
    -------
    Path
        The resolved location under ``PACKAGE_ROOT``.

    Raises
    ------
    ValueError
        If ``relative_path`` is empty, absolute, contains ``..``, or would
        resolve outside ``PACKAGE_ROOT``.
    """
    raise NotImplementedError


def to_package_relative(path: str | Path) -> str:
    """Return the POSIX path of an absolute location relative to the package.

    Parameters
    ----------
    path
        Absolute path that must resolve inside ``PACKAGE_ROOT``.

    Returns
    -------
    str
        Forward-slash relative path with no leading slash. The package root
        itself is ``"."``.

    Raises
    ------
    ValueError
        If ``path`` is not absolute or does not resolve inside ``PACKAGE_ROOT``.
    """
    raise NotImplementedError
