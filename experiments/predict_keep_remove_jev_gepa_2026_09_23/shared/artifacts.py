"""Download and upload experiment artifacts under the experimental S3 prefix.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_artifacts.py -q
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from lib.constants import REPO_ROOT

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
EXPERIMENT_DIRNAME = "predict_keep_remove_jev_gepa_2026_09_23"
EXPERIMENT_S3_PREFIX = "experiments/predict_keep_remove_jev_gepa_2026_09_23"


def download_if_missing(path: Path, key: str) -> None:
    """Write ``key`` from S3 when the local file is absent.

    Parameters
    ----------
    path
        Local destination path.
    key
        S3 object key within the experiment bucket.

    Raises
    ------
    FileNotFoundError
        When the object is missing on S3.
    """
    raise NotImplementedError


def upload_under_prefix(path: Path, allowed_prefix: str = EXPERIMENT_S3_PREFIX) -> None:
    """Upload ``path`` with put_new when absent, else replace.

    Parameters
    ----------
    path
        Local file to upload. The S3 key is ``path.relative_to(REPO_ROOT)``.
    allowed_prefix
        Allowed key prefix. Uploads outside this prefix are refused.

    Raises
    ------
    ValueError
        When the derived S3 key is outside ``allowed_prefix``.
    """
    raise NotImplementedError
