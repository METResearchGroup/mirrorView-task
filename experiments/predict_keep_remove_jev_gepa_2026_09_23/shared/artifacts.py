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
    if path.is_file():
        return
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stored.body)


def upload_under_prefix(
    path: Path,
    allowed_prefix: str = EXPERIMENT_S3_PREFIX,
    *,
    s3_key: str | None = None,
) -> None:
    """Upload ``path`` with put_new when absent, else replace.

    Parameters
    ----------
    path
        Local file to upload. The S3 key is ``path.relative_to(REPO_ROOT)`` unless
        ``s3_key`` is provided.
    allowed_prefix
        Allowed key prefix. Uploads outside this prefix are refused.
    s3_key
        Explicit object key. When set, ``REPO_ROOT`` is not used to derive the key.

    Raises
    ------
    ValueError
        When the derived S3 key is outside ``allowed_prefix``.
    """
    key = s3_key if s3_key is not None else str(path.relative_to(REPO_ROOT))
    if not key.startswith(allowed_prefix):
        raise ValueError(f"refusing S3 key outside {allowed_prefix}: {key}")
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    body = path.read_bytes()
    existing = store.get(key)
    if existing is None:
        store.put_new(key, body)
        return
    store.replace(key, body, etag=existing.etag)
