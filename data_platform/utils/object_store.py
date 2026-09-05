"""Local disk and S3 object stores behind ``StorageManager``."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Protocol

LFS_POINTER_FIRST_LINE = b"version https://git-lfs.github.com/spec/v1"
LFS_POINTER_ERROR = "refusing {action} {key}: body is a git-lfs pointer, not file content"
S3_KEY_PREFIX = "data_platform/data"
S3_KEY_PREFIX_ROOT = S3_KEY_PREFIX.split("/", 1)[0]
UNSAFE_KEY_SEGMENTS = frozenset({".", ".."})
DEFAULT_S3_BUCKET = "mirrorview-experimental-artifacts"
DEFAULT_S3_REGION = "us-east-2"
STORAGE_BACKEND_ENV_VAR = "DATA_PLATFORM_STORAGE_BACKEND"
S3_BUCKET_ENV_VAR = "DATA_PLATFORM_S3_BUCKET"
LOCAL_BACKEND = "local"
S3_BACKEND = "s3"


def validate_key(key: str) -> str:
    """Return ``key`` unchanged when it is a safe path relative to the store prefix.

    Raises
    ------
    ValueError
        When the key is empty, absolute, contains a backslash, contains a ``.``
        or ``..`` segment, or starts with ``data_platform/`` (the prefix already
        holds that segment, so such a key would duplicate it).
    """
    if not key:
        raise ValueError("object store key must not be empty")
    if key.startswith("/"):
        raise ValueError(f"object store key must be relative, got {key!r}")
    if "\\" in key:
        raise ValueError(f"object store key must not contain backslashes, got {key!r}")
    if any(segment in UNSAFE_KEY_SEGMENTS for segment in key.split("/")):
        raise ValueError(f"object store key must not contain '.' or '..' segments, got {key!r}")
    if key.startswith(f"{S3_KEY_PREFIX_ROOT}/"):
        raise ValueError(
            f"object store key must be relative to {S3_KEY_PREFIX!r}, got {key!r}"
        )
    return key


def is_lfs_pointer(body: bytes) -> bool:
    """Return True when the first line of ``body`` is exactly the Git LFS pointer header."""
    first_line = body.split(b"\n", 1)[0]
    return first_line == LFS_POINTER_FIRST_LINE


def sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _verify_sha256(key: str, body: bytes, expected_sha256: str | None) -> None:
    if expected_sha256 is None:
        return
    actual = sha256_hex(body)
    if actual != expected_sha256.lower():
        raise ValueError(
            f"SHA-256 mismatch for {key}: expected {expected_sha256}, got {actual}"
        )


class ObjectStore(Protocol):
    def exists(self, key: str) -> bool: ...

    def get_bytes(self, key: str, *, expected_sha256: str | None = None) -> bytes: ...

    def put_bytes(self, key: str, body: bytes, *, allow_overwrite: bool = False) -> str: ...

    def put_file(
        self, local_path: str | Path, key: str, *, allow_overwrite: bool = False
    ) -> str: ...


class LocalObjectStore:
    """Object store over files under one local root directory.

    Writes go to a temporary file in the target directory and are then moved
    into place, so a crash mid-write never leaves a partial object behind.
    Local reads do not check for LFS pointer text.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def _path_for(self, key: str) -> Path:
        return self._root / validate_key(key)

    def exists(self, key: str) -> bool:
        return self._path_for(key).is_file()

    def get_bytes(self, key: str, *, expected_sha256: str | None = None) -> bytes:
        path = self._path_for(key)
        if not path.is_file():
            raise FileNotFoundError(f"Object not found: {path}")
        body = path.read_bytes()
        _verify_sha256(key, body, expected_sha256)
        return body

    def put_bytes(self, key: str, body: bytes, *, allow_overwrite: bool = False) -> str:
        path = self._path_for(key)
        if path.exists() and not allow_overwrite:
            raise FileExistsError(f"Object already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.tmp")
        tmp_path.write_bytes(body)
        os.replace(tmp_path, path)
        return sha256_hex(body)

    def put_file(
        self, local_path: str | Path, key: str, *, allow_overwrite: bool = False
    ) -> str:
        return self.put_bytes(key, Path(local_path).read_bytes(), allow_overwrite=allow_overwrite)


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
