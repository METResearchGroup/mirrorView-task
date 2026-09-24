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


def rebuilt_s3_prefix() -> str:
    """Return experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt."""
    return f"{shared_artifacts.EXPERIMENT_S3_PREFIX}/{REBUILT_S3_SUBPREFIX}"


def upload_rebuilt(path: Path) -> None:
    """Call shared artifacts.upload_under_prefix with allowed_prefix = rebuilt_s3_prefix()."""
    shared_artifacts.upload_under_prefix(path, allowed_prefix=rebuilt_s3_prefix())
