"""Copy the pinned Twitter preprocessed posts csv from Git LFS to S3.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

from lib.aws.s3 import S3
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

BUCKET = "mirrorview-experimental-artifacts"
REGION = "us-east-2"
DATASET_ID = "twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547"
PREPROCESSED_RUN = "2026_09_06-19:28:47"
EXPECTED_OBJECT_COUNT = 1
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
DUPLICATE_PREFIX = "data_platform/data_platform/"

DATASET_ROOT = f"data_platform/data/twitter/{DATASET_ID}"
POSTS_CSV_PATH = f"{DATASET_ROOT}/preprocessed/{PREPROCESSED_RUN}/posts.csv"
INVENTORY_PATH = REPO_ROOT / DATASET_ROOT / "s3_preprocessed_inventory.json"
LFS_INCLUDE_PATTERNS: tuple[str, ...] = (POSTS_CSV_PATH,)


def scoped_repo_relative_paths() -> list[str]:
    """Return the locked upload paths. Must have length EXPECTED_OBJECT_COUNT.

    Raises
    ------
    RuntimeError
        If the list does not have exactly ``EXPECTED_OBJECT_COUNT`` entries
        or the path is missing on disk.
    """
    paths = [POSTS_CSV_PATH]
    if len(paths) != EXPECTED_OBJECT_COUNT:
        raise RuntimeError(f"expected {EXPECTED_OBJECT_COUNT} scoped paths, built {len(paths)}")
    missing = [path for path in paths if not (REPO_ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"scoped paths missing on disk: {missing}")
    return paths


def run_git_lfs_pull(patterns: Sequence[str]) -> None:
    """Fetch and check out Git LFS blobs for each include pattern.

    Raises
    ------
    subprocess.CalledProcessError
        If any ``git lfs pull`` call exits non-zero.
    """
    for pattern in patterns:
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


def content_type_for(repo_relative_path: str) -> str:
    """Return application/json for .json and application/octet-stream otherwise."""
    if repo_relative_path.endswith(".json"):
        return "application/json"
    return "application/octet-stream"


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
    ValueError
        If the key starts with ``data_platform/data_platform/``.
    RuntimeError
        If the re-downloaded object differs in length or SHA-256.
    """
    key = repo_relative_path
    if key.startswith(DUPLICATE_PREFIX):
        raise ValueError(f"refusing duplicated data_platform prefix: {key}")
    local_sha256 = sha256_hex(data)
    s3.upload_bytes(key, data, content_type=content_type_for(repo_relative_path))
    remote = s3.get_bytes(key)
    remote_sha256 = sha256_hex(remote)
    if len(remote) != len(data) or remote_sha256 != local_sha256:
        raise RuntimeError(
            f"remote object differs for {key}: "
            f"{len(remote)} bytes {remote_sha256} != {len(data)} bytes {local_sha256}"
        )
    return {
        "repo_relative_path": repo_relative_path,
        "s3_key": key,
        "bytes": len(data),
        "sha256": local_sha256,
    }


def write_inventory(rows: list[dict], path: Path) -> None:
    """Write inventory JSON including bucket, region, dataset_id, and preprocessed_run."""
    inventory = {
        "bucket": BUCKET,
        "region": REGION,
        "dataset_id": DATASET_ID,
        "preprocessed_run": PREPROCESSED_RUN,
        "uploaded_at": get_current_timestamp(),
        "object_count": len(rows),
        "objects": sorted(rows, key=lambda row: row["repo_relative_path"]),
    }
    path.write_text(json.dumps(inventory, indent=2) + "\n")


def main() -> None:
    """Pull LFS, upload the scoped csv, write inventory, and print the object count."""
    paths = scoped_repo_relative_paths()
    run_git_lfs_pull(LFS_INCLUDE_PATTERNS)
    s3 = S3(BUCKET, region_name=REGION)
    rows = []
    for path in paths:
        row = upload_and_verify(s3, path, read_scoped_bytes(path))
        print(f"verified s3://{BUCKET}/{row['s3_key']} ({row['bytes']} bytes)")
        rows.append(row)
    write_inventory(rows, INVENTORY_PATH)
    print(f"uploaded {len(rows)} object")


if __name__ == "__main__":
    main()
