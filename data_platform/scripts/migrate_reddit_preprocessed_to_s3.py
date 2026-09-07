"""Copy the pinned Reddit preprocessed comments parquet from Git LFS to S3.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/migrate_reddit_preprocessed_to_s3.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from lib.aws.s3 import S3
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

BUCKET = "mirrorview-experimental-artifacts"
REGION = "us-east-2"
DATASET_ID = "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079"
PREPROCESSED_RUN = "2026_09_03-23:39:28"
EXPECTED_OBJECT_COUNT = 1
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
PARQUET_CONTENT_TYPE = "application/octet-stream"

DATASET_ROOT = f"data_platform/data/reddit/{DATASET_ID}"
COMMENTS_PARQUET_RELATIVE_PATH = (
    f"{DATASET_ROOT}/preprocessed/{PREPROCESSED_RUN}/comments.parquet"
)
INVENTORY_PATH = REPO_ROOT / DATASET_ROOT / "s3_preprocessed_inventory.json"
LFS_INCLUDE_PATTERN = COMMENTS_PARQUET_RELATIVE_PATH


def scoped_repo_relative_path() -> str:
    """Return the locked repo-relative comments parquet path.

    Raises
    ------
    RuntimeError
        If the path is missing on disk.
    """
    path = COMMENTS_PARQUET_RELATIVE_PATH
    if not (REPO_ROOT / path).is_file():
        raise RuntimeError(f"scoped path missing on disk: {path}")
    return path


def run_git_lfs_pull(pattern: str) -> None:
    """Fetch and check out the Git LFS blob for one include pattern.

    Raises
    ------
    subprocess.CalledProcessError
        If ``git lfs pull`` exits non-zero.
    """
    subprocess.run(
        ["git", "lfs", "pull", "--include", pattern],
        cwd=REPO_ROOT,
        check=True,
    )


def read_scoped_bytes(repo_relative_path: str) -> bytes:
    """Read a scoped file and refuse Git LFS pointer text.

    Raises
    ------
    ValueError
        If the file still starts with the Git LFS pointer header.
    """
    data = (REPO_ROOT / repo_relative_path).read_bytes()
    if data.startswith(LFS_POINTER_PREFIX):
        raise ValueError(f"Git LFS pointer was not resolved to bytes: {repo_relative_path}")
    return data


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of the bytes."""
    return hashlib.sha256(data).hexdigest()


def _require_matching_remote(key: str, data: bytes, remote: bytes) -> None:
    """Raise if re-downloaded bytes differ in length or SHA-256.

    Raises
    ------
    RuntimeError
        If length or SHA-256 does not match the local bytes.
    """
    local_sha256 = sha256_hex(data)
    remote_sha256 = sha256_hex(remote)
    if len(remote) != len(data) or remote_sha256 != local_sha256:
        raise RuntimeError(
            f"remote object differs for {key}: "
            f"{len(remote)} bytes {remote_sha256} != {len(data)} bytes {local_sha256}"
        )


def upload_and_verify(s3: S3, repo_relative_path: str, data: bytes) -> dict:
    """Upload bytes to the key equal to the path and confirm the remote SHA-256.

    The object is re-downloaded after the upload. The S3 ETag is never used as
    a content hash.

    Returns
    -------
    dict
        Inventory row with ``repo_relative_path``, ``s3_key``, ``bytes``, and
        ``sha256``.

    Raises
    ------
    RuntimeError
        If the re-downloaded object differs in length or SHA-256.
    """
    key = repo_relative_path
    s3.upload_bytes(key, data, content_type=PARQUET_CONTENT_TYPE)
    _require_matching_remote(key, data, s3.get_bytes(key))
    return {
        "repo_relative_path": repo_relative_path,
        "s3_key": key,
        "bytes": len(data),
        "sha256": sha256_hex(data),
    }


def write_inventory(rows: list[dict], path: Path) -> None:
    """Write the inventory JSON with ``preprocessed_run`` and object count 1.

    Raises
    ------
    RuntimeError
        If ``rows`` is not exactly ``EXPECTED_OBJECT_COUNT`` long.
    """
    if len(rows) != EXPECTED_OBJECT_COUNT:
        raise RuntimeError(f"expected {EXPECTED_OBJECT_COUNT} inventory rows, got {len(rows)}")
    inventory = {
        "bucket": BUCKET,
        "region": REGION,
        "dataset_id": DATASET_ID,
        "preprocessed_run": PREPROCESSED_RUN,
        "uploaded_at": get_current_timestamp(),
        "object_count": EXPECTED_OBJECT_COUNT,
        "objects": rows,
    }
    path.write_text(json.dumps(inventory, indent=2) + "\n")


def main() -> None:
    path = scoped_repo_relative_path()
    run_git_lfs_pull(LFS_INCLUDE_PATTERN)
    s3 = S3(BUCKET, region_name=REGION)
    row = upload_and_verify(s3, path, read_scoped_bytes(path))
    write_inventory([row], INVENTORY_PATH)
    print(f"uploaded {EXPECTED_OBJECT_COUNT} object to s3://{BUCKET}/")


if __name__ == "__main__":
    main()
