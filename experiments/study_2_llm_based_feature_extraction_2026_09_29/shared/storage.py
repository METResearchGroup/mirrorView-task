"""Local paths and S3 upload/download for experiment artifacts."""

from pathlib import Path


def local_path(relative_key: str) -> Path:
    raise NotImplementedError


def upload_artifact(relative_key: str) -> str:
    raise NotImplementedError


def download_artifact(relative_key: str) -> Path:
    raise NotImplementedError
