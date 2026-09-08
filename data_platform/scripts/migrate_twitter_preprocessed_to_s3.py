"""Copy a Twitter preprocessed posts csv from Git LFS to S3.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py \\
        --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \\
        --preprocessed-run 2026_09_08-01:48:08
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from lib.aws.s3 import S3
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

BUCKET = "mirrorview-experimental-artifacts"
REGION = "us-east-2"
EXPECTED_OBJECT_COUNT = 1
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
DUPLICATE_PREFIX = "data_platform/data_platform/"
TWITTER_DATA_PREFIX = "data_platform/data/twitter"
PREPROCESSED_DIRNAME = "preprocessed"
POSTS_CSV_NAME = "posts.csv"
INVENTORY_FILENAME = "s3_preprocessed_inventory.json"


@dataclass(frozen=True)
class TwitterPreprocessedS3Args:
    """Required dataset id and preprocessed run for migrate and verify."""

    dataset_id: str
    preprocessed_run: str


def parse_args(argv: Sequence[str]) -> TwitterPreprocessedS3Args:
    """Parse required ``--dataset-id`` and ``--preprocessed-run``.

    Raises
    ------
    SystemExit
        If either flag is missing. Exit code is non-zero.
    """
    parser = argparse.ArgumentParser(
        description="Copy one Twitter preprocessed posts.csv from Git LFS to S3."
    )
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--preprocessed-run", required=True)
    parsed = parser.parse_args(argv)
    return TwitterPreprocessedS3Args(
        dataset_id=parsed.dataset_id,
        preprocessed_run=parsed.preprocessed_run,
    )


def dataset_root_relative(dataset_id: str) -> str:
    """Return the repo-relative Twitter dataset root for ``dataset_id``."""
    return f"{TWITTER_DATA_PREFIX}/{dataset_id}"


def posts_csv_relative_path(dataset_id: str, preprocessed_run: str) -> str:
    """Return the repo-relative preprocessed ``posts.csv`` path."""
    return (
        f"{dataset_root_relative(dataset_id)}/"
        f"{PREPROCESSED_DIRNAME}/{preprocessed_run}/{POSTS_CSV_NAME}"
    )


def inventory_path_for(dataset_id: str) -> Path:
    """Return the inventory JSON path under the Twitter dataset root."""
    return REPO_ROOT / dataset_root_relative(dataset_id) / INVENTORY_FILENAME


def scoped_repo_relative_paths(dataset_id: str, preprocessed_run: str) -> list[str]:
    """Return the locked upload paths. Must have length EXPECTED_OBJECT_COUNT.

    Raises
    ------
    RuntimeError
        If the list does not have exactly ``EXPECTED_OBJECT_COUNT`` entries
        or the path is missing on disk.
    """
    paths = [posts_csv_relative_path(dataset_id, preprocessed_run)]
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


def write_inventory(
    rows: list[dict],
    path: Path,
    dataset_id: str,
    preprocessed_run: str,
) -> None:
    """Write inventory JSON including bucket, region, dataset_id, and preprocessed_run."""
    inventory = {
        "bucket": BUCKET,
        "region": REGION,
        "dataset_id": dataset_id,
        "preprocessed_run": preprocessed_run,
        "uploaded_at": get_current_timestamp(),
        "object_count": len(rows),
        "objects": sorted(rows, key=lambda row: row["repo_relative_path"]),
    }
    path.write_text(json.dumps(inventory, indent=2) + "\n")


def upload_scoped_paths(s3: S3, paths: Sequence[str]) -> list[dict]:
    """Upload each scoped path and print the verified S3 URI."""
    rows = []
    for path in paths:
        row = upload_and_verify(s3, path, read_scoped_bytes(path))
        print(f"verified s3://{BUCKET}/{row['s3_key']} ({row['bytes']} bytes)")
        rows.append(row)
    return rows


def main(argv: Sequence[str]) -> None:
    """Pull LFS, upload the scoped csv, write inventory, and print the object count."""
    args = parse_args(argv)
    paths = scoped_repo_relative_paths(args.dataset_id, args.preprocessed_run)
    run_git_lfs_pull(paths)
    rows = upload_scoped_paths(S3(BUCKET, region_name=REGION), paths)
    write_inventory(
        rows,
        inventory_path_for(args.dataset_id),
        args.dataset_id,
        args.preprocessed_run,
    )
    print(f"uploaded {len(rows)} object")


if __name__ == "__main__":
    main(sys.argv[1:])
