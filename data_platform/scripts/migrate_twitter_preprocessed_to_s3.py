"""Copy the pinned Twitter preprocessed posts csv from Git LFS to S3.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from lib.aws.s3 import S3
from lib.constants import REPO_ROOT

BUCKET = "mirrorview-experimental-artifacts"
REGION = "us-east-2"
DATASET_ID = "twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547"
PREPROCESSED_RUN = "2026_09_06-19:28:47"
EXPECTED_OBJECT_COUNT = 1
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"

DATASET_ROOT = f"data_platform/data/twitter/{DATASET_ID}"
POSTS_CSV_PATH = (
    f"{DATASET_ROOT}/preprocessed/{PREPROCESSED_RUN}/posts.csv"
)
INVENTORY_PATH = REPO_ROOT / DATASET_ROOT / "s3_preprocessed_inventory.json"
LFS_INCLUDE_PATTERNS: tuple[str, ...] = (POSTS_CSV_PATH,)


def scoped_repo_relative_paths() -> list[str]:
    """Return the locked upload paths. Must have length EXPECTED_OBJECT_COUNT."""
    raise NotImplementedError


def run_git_lfs_pull(patterns: Sequence[str]) -> None:
    """Fetch and check out Git LFS blobs for each include pattern."""
    raise NotImplementedError


def read_scoped_bytes(repo_relative_path: str) -> bytes:
    """Read a scoped file and refuse Git LFS pointer text.

    Raises
    ------
    ValueError
        If the file still starts with the Git LFS pointer header.
    """
    raise NotImplementedError


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of the bytes."""
    raise NotImplementedError


def content_type_for(repo_relative_path: str) -> str:
    """Return application/json for .json and application/octet-stream otherwise."""
    raise NotImplementedError


def upload_and_verify(s3: S3, repo_relative_path: str, data: bytes) -> dict:
    """Upload bytes to the key equal to the path and confirm the remote SHA-256.

    The S3 ETag is never used as a content hash.

    Returns
    -------
    dict
        Inventory row with repo_relative_path, s3_key, bytes, and sha256.
    """
    raise NotImplementedError


def write_inventory(rows: list[dict], path: Path) -> None:
    """Write inventory JSON including bucket, region, dataset_id, and preprocessed_run."""
    raise NotImplementedError


def main() -> None:
    """Pull LFS, upload the scoped csv, write inventory, and print the object count."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
