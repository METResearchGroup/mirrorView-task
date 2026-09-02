"""Shared YAML config path resolution for pipeline entrypoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def resolve_config_path(config: Path, base_dir: Path) -> Path:
    """Resolve a config path relative to base_dir (typically the repo root)."""
    candidates = [config]
    if config.suffix != ".yaml":
        candidates.append(config.with_suffix(".yaml"))
    if not config.is_absolute():
        candidates.extend(base_dir / candidate for candidate in list(candidates))

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(f"Config not found: {config}")


def to_repo_relative(path: str | Path, repo_root: Path) -> str:
    """Return the POSIX path of an absolute location relative to the repo root.

    The target file does not need to exist.

    Parameters
    ----------
    path
        Absolute path that must resolve inside ``repo_root``.
    repo_root
        Repository root used as the relative base.

    Returns
    -------
    str
        Forward-slash relative path with no leading slash. The repo root
        itself is ``"."``.

    Raises
    ------
    ValueError
        If ``path`` is not absolute or does not resolve inside ``repo_root``.
    """
    raise NotImplementedError


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(
            f"YAML config root must be a mapping, got {type(raw).__name__}: {config_path}"
        )
    return raw
