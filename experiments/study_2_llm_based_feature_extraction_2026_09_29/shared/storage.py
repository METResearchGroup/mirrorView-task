"""Local paths and S3 upload/download for experiment artifacts."""

from __future__ import annotations

from pathlib import Path

from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    use_lab_credentials,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    LOCAL_OUTPUT_DIR,
    S3_BUCKET,
    S3_PREFIX,
)
from lib.aws.s3 import DEFAULT_REGION_NAME, S3


def local_path(relative_key: str) -> Path:
    """Return the local output path for a relative artifact key.

    Parameters
    ----------
    relative_key
        Path under the experiment ``outputs/`` directory.

    Returns
    -------
    pathlib.Path
        Absolute local path for the artifact.
    """
    return LOCAL_OUTPUT_DIR / relative_key


def upload_artifact(relative_key: str) -> str:
    """Upload a local artifact to the experiment S3 prefix.

    Parameters
    ----------
    relative_key
        Path under ``outputs/`` to upload.

    Returns
    -------
    str
        ``s3://`` URI of the uploaded object.

    Raises
    ------
    FileNotFoundError
        When the local file does not exist.
    """
    path = local_path(relative_key)
    if not path.is_file():
        raise FileNotFoundError(path)
    use_lab_credentials()
    object_key = f"{S3_PREFIX}{relative_key}"
    store = S3(S3_BUCKET, region_name=DEFAULT_REGION_NAME)
    store.upload_file(path, object_key)
    return f"s3://{S3_BUCKET}/{object_key}"


def download_artifact(relative_key: str) -> Path:
    """Return a local artifact path, downloading from S3 when missing locally.

    Parameters
    ----------
    relative_key
        Path under ``outputs/``.

    Returns
    -------
    pathlib.Path
        Local path to the artifact bytes.

    Raises
    ------
    FileNotFoundError
        When the object is missing locally and on S3.
    """
    path = local_path(relative_key)
    if path.is_file():
        return path
    use_lab_credentials()
    object_key = f"{S3_PREFIX}{relative_key}"
    store = S3(S3_BUCKET, region_name=DEFAULT_REGION_NAME)
    body = store.get_bytes(object_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path
