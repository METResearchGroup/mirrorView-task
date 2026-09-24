"""Upload rebuilt GEPA artifacts under the experiment S3 subprefix.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_artifacts.py -q
"""

from __future__ import annotations

from pathlib import Path

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    REBUILT_S3_SUBPREFIX,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import artifacts as shared_artifacts

_REBUILT_PACKAGE_ROOT = Path(__file__).resolve().parent
_EXPERIMENT_PARTS = ("experiments", shared_artifacts.EXPERIMENT_DIRNAME)
_REBUILT_PREFIX_PARTS = (*_EXPERIMENT_PARTS, REBUILT_S3_SUBPREFIX)


def rebuilt_s3_prefix() -> str:
    """Return experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt."""
    return f"{shared_artifacts.EXPERIMENT_S3_PREFIX}/{REBUILT_S3_SUBPREFIX}"


def rebuilt_s3_key(path: Path) -> str:
    """Map a local path to an object key under ``rebuilt_s3_prefix()`` without ``REPO_ROOT``."""
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(_REBUILT_PACKAGE_ROOT)
        suffix = relative.as_posix()
        return f"{rebuilt_s3_prefix()}/{suffix}" if suffix else rebuilt_s3_prefix()

    except ValueError:
        parts = resolved.parts
        for index in range(len(parts) - len(_REBUILT_PREFIX_PARTS) + 1):
            if tuple(parts[index : index + len(_REBUILT_PREFIX_PARTS)]) == _REBUILT_PREFIX_PARTS:
                return "/".join(parts[index:])
        for index in range(len(parts) - len(_EXPERIMENT_PARTS) + 1):
            if tuple(parts[index : index + len(_EXPERIMENT_PARTS)]) == _EXPERIMENT_PARTS:
                rest = parts[index + len(_EXPERIMENT_PARTS) :]
                if not rest:
                    raise ValueError(f"cannot derive rebuilt S3 key from {path}")
                return f"{rebuilt_s3_prefix()}/{'/'.join(rest)}"
        raise ValueError(f"cannot derive rebuilt S3 key from {path}")


def upload_rebuilt(path: Path) -> None:
    """Upload ``path`` under ``rebuilt_s3_prefix()`` using a package-relative S3 key."""
    shared_artifacts.upload_under_prefix(
        path,
        allowed_prefix=rebuilt_s3_prefix(),
        s3_key=rebuilt_s3_key(path),
    )
