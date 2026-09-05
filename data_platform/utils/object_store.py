"""Local disk and S3 object stores behind ``StorageManager``."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

LFS_POINTER_FIRST_LINE = b"version https://git-lfs.github.com/spec/v1"
S3_KEY_PREFIX = "data_platform/data"
DEFAULT_S3_BUCKET = "mirrorview-experimental-artifacts"
DEFAULT_S3_REGION = "us-east-2"
STORAGE_BACKEND_ENV_VAR = "DATA_PLATFORM_STORAGE_BACKEND"
S3_BUCKET_ENV_VAR = "DATA_PLATFORM_S3_BUCKET"
LOCAL_BACKEND = "local"
S3_BACKEND = "s3"


def validate_key(key: str) -> str:
    raise NotImplementedError


def is_lfs_pointer(body: bytes) -> bool:
    raise NotImplementedError


def sha256_hex(body: bytes) -> str:
    raise NotImplementedError


class ObjectStore(Protocol):
    def exists(self, key: str) -> bool: ...

    def get_bytes(self, key: str, *, expected_sha256: str | None = None) -> bytes: ...

    def put_bytes(self, key: str, body: bytes, *, allow_overwrite: bool = False) -> str: ...

    def put_file(
        self, local_path: str | Path, key: str, *, allow_overwrite: bool = False
    ) -> str: ...


class LocalObjectStore:
    def __init__(self, root: Path) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def get_bytes(self, key: str, *, expected_sha256: str | None = None) -> bytes:
        raise NotImplementedError

    def put_bytes(self, key: str, body: bytes, *, allow_overwrite: bool = False) -> str:
        raise NotImplementedError

    def put_file(
        self, local_path: str | Path, key: str, *, allow_overwrite: bool = False
    ) -> str:
        raise NotImplementedError


class S3ObjectStore:
    def __init__(
        self,
        bucket: str,
        prefix: str = S3_KEY_PREFIX,
        *,
        region_name: str = DEFAULT_S3_REGION,
    ) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def get_bytes(self, key: str, *, expected_sha256: str | None = None) -> bytes:
        raise NotImplementedError

    def put_bytes(self, key: str, body: bytes, *, allow_overwrite: bool = False) -> str:
        raise NotImplementedError

    def put_file(
        self, local_path: str | Path, key: str, *, allow_overwrite: bool = False
    ) -> str:
        raise NotImplementedError


def resolve_object_store(*, local_root: Path) -> ObjectStore:
    raise NotImplementedError
