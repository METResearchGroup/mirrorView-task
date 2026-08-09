"""Upload local directories to S3 for frozen experiment artifact layout.

Run from root: PYTHONPATH=. uv run python -c "from experiments.finetune_qwen_model_2026_08_08.src.s3_upload import upload_directory"
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import boto3


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Split ``s3://bucket/prefix`` into bucket and key prefix."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"Invalid S3 URI: {uri}")
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")
    return bucket, prefix.rstrip("/")


def upload_directory(local_dir: Path, s3_uri: str, region: str) -> list[str]:
    """Upload all files under ``local_dir`` to ``s3_uri``.

    Parameters
    ----------
    local_dir
        Local directory whose files are uploaded (non-recursive flat + nested).
    s3_uri
        Destination prefix ``s3://bucket/prefix``.
    region
        AWS region name.

    Returns
    -------
    list[str]
        Uploaded object URIs.
    """
    bucket, prefix = parse_s3_uri(s3_uri)
    client = boto3.client("s3", region_name=region)
    uploaded: list[str] = []
    for path in sorted(local_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(local_dir).as_posix()
        key = f"{prefix}/{relative}" if prefix else relative
        client.upload_file(str(path), bucket, key)
        uri = f"s3://{bucket}/{key}"
        uploaded.append(uri)
        print(f"Uploaded {uri}")
    return uploaded
