"""Copy the pinned Reddit preprocessed comments parquet from Git LFS to S3.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/migrate_reddit_preprocessed_to_s3.py
"""

from __future__ import annotations

from pathlib import Path

from lib.aws.s3 import S3


def scoped_repo_relative_path() -> str:
    raise NotImplementedError


def run_git_lfs_pull(pattern: str) -> None:
    raise NotImplementedError


def read_scoped_bytes(repo_relative_path: str) -> bytes:
    raise NotImplementedError


def sha256_hex(data: bytes) -> str:
    raise NotImplementedError


def upload_and_verify(s3: S3, repo_relative_path: str, data: bytes) -> dict:
    raise NotImplementedError


def write_inventory(rows: list[dict], path: Path) -> None:
    raise NotImplementedError


def main() -> None:
    path = scoped_repo_relative_path()
    run_git_lfs_pull(path)
    s3 = S3("unused")
    row = upload_and_verify(s3, path, read_scoped_bytes(path))
    write_inventory([row], Path("unused"))
    print(path)


if __name__ == "__main__":
    main()
