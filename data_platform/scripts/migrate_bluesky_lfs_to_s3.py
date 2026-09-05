"""Copy the pinned Bluesky pipeline and dump files from Git LFS to S3.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/migrate_bluesky_lfs_to_s3.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from lib.aws.s3 import S3


def scoped_repo_relative_paths() -> list[str]:
    raise NotImplementedError


def run_git_lfs_pull(patterns: Sequence[str]) -> None:
    raise NotImplementedError


def read_scoped_bytes(repo_relative_path: str) -> bytes:
    raise NotImplementedError


def sha256_hex(data: bytes) -> str:
    raise NotImplementedError


def content_type_for(repo_relative_path: str) -> str:
    raise NotImplementedError


def upload_and_verify(s3: S3, repo_relative_path: str, data: bytes) -> dict:
    raise NotImplementedError


def write_inventory(rows: list[dict], path: Path) -> None:
    raise NotImplementedError


def main() -> None:
    paths = scoped_repo_relative_paths()
    run_git_lfs_pull([])
    s3 = S3("")
    rows = [upload_and_verify(s3, path, read_scoped_bytes(path)) for path in paths]
    write_inventory(rows, Path())


if __name__ == "__main__":
    main()
