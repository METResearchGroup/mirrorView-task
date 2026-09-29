"""Local paths and S3 upload/download for experiment artifacts."""

from __future__ import annotations

from pathlib import Path


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
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError
