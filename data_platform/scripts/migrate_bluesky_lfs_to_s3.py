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
from lib.constants import REPO_ROOT

BUCKET = "mirrorview-experimental-artifacts"
REGION = "us-east-2"
DATASET_ID = "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"
RAW_RUN = "2026_09_01-00:00:00"
PREPROCESSED_RUN = "2026_09_03-23:51:30"
EXPECTED_OBJECT_COUNT = 53
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"

DATASET_ROOT = f"data_platform/data/bluesky/{DATASET_ID}"
DUMP_ROOT = "data_platform/ingestion/data_dumps/bluesky/data"
INVENTORY_PATH = REPO_ROOT / DATASET_ROOT / "s3_migration_inventory.json"
LFS_INCLUDE_PATTERNS: tuple[str, ...] = (
    f"{DATASET_ROOT}/**",
    f"{DUMP_ROOT}/parquet/**",
)

# The raw run and the dump tree hold the same 24 hourly files for 2026-09-01.
HOURLY_PARQUET_SEGMENTS: tuple[str, ...] = (
    "hour=00/87e175daae2e2a8367e353ab2018088747e1f1deaa9b052889d9fd276297b2ef.parquet",
    "hour=01/07a13b46f6e914e3fbfd0c87ef4ebdcf9c2d4f634322c915ee90f6c6590cc182.parquet",
    "hour=02/9291dd02ea6779db0af5c4e7338dff05d5a1b8a757bd1887d96e7dc5fa8e8be3.parquet",
    "hour=03/f507657e54bd11a974d2d3360dfd20ea5a37720b2720060a20a62392d32fa838.parquet",
    "hour=04/8f71e793b20221a35c9c068c7e1b5a2c92d20d3b6d07d7b6f14c96fa6e7b9b8a.parquet",
    "hour=05/b75983817d2a7caa33652e907d87e0045d765613ff8912c75b6677460546c2a9.parquet",
    "hour=06/1d1efb717db79a6012e21439d1d99583a844b489bf851514d3c17f25060c245d.parquet",
    "hour=07/bdcf5c6a124a8427d6243ca1cb4dad21de091a9cc2f861bc31e68dc4ae0e8ee7.parquet",
    "hour=08/0276dae1716f95233fc8cc45af8e0fab85a9c6c30f38b7b873633d3555316cec.parquet",
    "hour=09/065a1008065c2274e24202136e72b152d6b04d780a854c04dee3765d68357508.parquet",
    "hour=10/a1f035bf84ffc505ea57fda0c373c18633dbf65c2b4686c9326d63170026f88c.parquet",
    "hour=11/819729c9892253012b62bb3a28dc5c3a05c3b66b1836533f44065a330a116e3b.parquet",
    "hour=12/c215309e4986c3414dbc5570af8e35d14d13324c8025301fbec2a5346c9b8f8b.parquet",
    "hour=13/4e8e9fa304aa7077c79f235570515987684b758e2c3faa7b70e90590c90e7c98.parquet",
    "hour=14/996a62335449379e3495e840958d5d11b7833c4c5e77490ec69f1acf1f2d393c.parquet",
    "hour=15/c17354f4d79805d27549fe6b1008cc8b1bdf70b6f801b68c9b844e27ef5a8c78.parquet",
    "hour=16/11044bc252e2f74cd4a8b1cccee37f09fa7c7f0805e9c5951e3e003cbf9b0508.parquet",
    "hour=17/7561d13554b77359f734feab412d997b54ec77b75aad0cb0c88a42d544af4412.parquet",
    "hour=18/d8a3189e9a0ccf1573d931c21a7a0406c624c795f64c0b78bddb255ddc5fbee9.parquet",
    "hour=19/ebb4b2d8fd185c4a957629af8e777ef84cf979057fdaf7be998db4eeb7afed17.parquet",
    "hour=20/1e9397d32125d44702131b572c3300c4da2dc65cde2ab324cfb13f2437d679d7.parquet",
    "hour=21/73a3a11c68afafe8cd2e210f02ba138cc46f2983c954aeaf71bfe38f7c02454f.parquet",
    "hour=22/71ec9881d8718156f855e4aeb9d23799bb8a5e92bd2c9d1b9ffe8ae00e41c4f7.parquet",
    "hour=23/7aa81f763c2c76de75602fbe77ab9483e85cb4b94c4a81b6829787a70aef0945.parquet",
)


def scoped_repo_relative_paths() -> list[str]:
    """Return the 53 repo-relative paths in the locked upload scope, sorted.

    Raises
    ------
    RuntimeError
        If the list does not have exactly ``EXPECTED_OBJECT_COUNT`` entries
        or any path is missing on disk.
    """
    raise NotImplementedError


def run_git_lfs_pull(patterns: Sequence[str]) -> None:
    """Fetch and check out LFS blobs for each include pattern.

    Raises
    ------
    subprocess.CalledProcessError
        If any ``git lfs pull`` call exits non-zero.
    """
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
    """Return ``application/json`` for ``.json`` and ``application/octet-stream`` otherwise."""
    raise NotImplementedError


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
    raise NotImplementedError


def write_inventory(rows: list[dict], path: Path) -> None:
    """Write the migration inventory JSON with rows sorted by repo-relative path."""
    raise NotImplementedError


def main() -> None:
    paths = scoped_repo_relative_paths()
    run_git_lfs_pull(LFS_INCLUDE_PATTERNS)
    s3 = S3(BUCKET, region_name=REGION)
    rows = [upload_and_verify(s3, path, read_scoped_bytes(path)) for path in paths]
    write_inventory(rows, INVENTORY_PATH)
    print(f"uploaded {len(rows)} objects to s3://{BUCKET}/")


if __name__ == "__main__":
    main()
