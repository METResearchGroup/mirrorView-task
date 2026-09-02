"""Resolve and round-trip paths relative to the data-platform package.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q
"""

from __future__ import annotations

from pathlib import Path

from data_platform.constants import PACKAGE_ROOT

_PARENT_DIR = ".."


def _validated_relative_path(relative_path: str | Path) -> Path:
    if relative_path == "":
        raise ValueError("Package-relative path must not be empty.")
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"Package-relative path must not be absolute: {relative_path}")
    if _PARENT_DIR in candidate.parts:
        raise ValueError(
            f"Package-relative path must not contain parent segments: {relative_path}"
        )
    return candidate


def _require_resolved_inside_package(resolved: Path, source: str | Path) -> Path:
    package_root = PACKAGE_ROOT.resolve()
    if not resolved.is_relative_to(package_root):
        raise ValueError(
            f"Path is outside the data-platform package: {source}"
        )
    return package_root


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
    candidate = _validated_relative_path(relative_path)
    package_root = PACKAGE_ROOT.resolve()
    resolved = (package_root / candidate).resolve()
    _require_resolved_inside_package(resolved, relative_path)
    return resolved


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
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")
    resolved = candidate.resolve()
    package_root = _require_resolved_inside_package(resolved, path)
    return resolved.relative_to(package_root).as_posix()
