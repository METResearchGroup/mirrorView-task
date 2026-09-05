"""Local disk and S3 object stores behind ``StorageManager``."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Protocol

from botocore.exceptions import ClientError

from lib.aws.s3 import NOT_FOUND_ERROR_CODES, S3

LFS_POINTER_FIRST_LINE = b"version https://git-lfs.github.com/spec/v1"
LFS_POINTER_ERROR = "refusing {action} {key}: body is a git-lfs pointer, not file content"
S3_KEY_PREFIX = "data_platform/data"
S3_KEY_PREFIX_ROOT = S3_KEY_PREFIX.split("/", 1)[0]
UNSAFE_KEY_SEGMENTS = frozenset({".", ".."})
SHA256_METADATA_KEY = "sha256"
PRECONDITION_FAILED_ERROR_CODES = frozenset({"PreconditionFailed", "412"})
DEFAULT_CONTENT_TYPE = "application/octet-stream"
CONTENT_TYPES_BY_SUFFIX = {
    ".json": "application/json",
    ".csv": "text/csv",
    ".parquet": "application/octet-stream",
}
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
    """Object store over one S3 bucket under the ``data_platform/data`` prefix.

    Every upload records the SHA-256 of the body as object metadata and
    refuses to replace an existing object unless the caller asks for it.
    Git LFS pointer text is rejected on upload and on download. The S3 ETag
    is never used as a content hash.
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = S3_KEY_PREFIX,
        *,
        region_name: str = DEFAULT_S3_REGION,
    ) -> None:
        normalized_prefix = prefix.strip("/")
        if normalized_prefix != S3_KEY_PREFIX:
            raise ValueError(
                f"S3ObjectStore prefix must be {S3_KEY_PREFIX!r}, got {prefix!r}"
            )
        self._prefix = normalized_prefix
        self._s3 = S3(bucket, region_name=region_name)

    @property
    def bucket(self) -> str:
        return self._s3.bucket

    def full_key(self, key: str) -> str:
        """Return the bucket key for a store key, e.g. ``data_platform/data/bluesky/...``."""
        return f"{self._prefix}/{validate_key(key)}"

    def exists(self, key: str) -> bool:
        return self._s3.object_exists(self.full_key(key))

    def get_bytes(self, key: str, *, expected_sha256: str | None = None) -> bytes:
        full_key = self.full_key(key)
        try:
            body = self._s3.get_bytes(full_key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in NOT_FOUND_ERROR_CODES:
                raise FileNotFoundError(
                    f"Object not found: s3://{self.bucket}/{full_key}"
                ) from e
            raise
        if is_lfs_pointer(body):
            raise ValueError(LFS_POINTER_ERROR.format(action="to read", key=full_key))
        _verify_sha256(full_key, body, expected_sha256)
        return body

    def put_bytes(self, key: str, body: bytes, *, allow_overwrite: bool = False) -> str:
        full_key = self.full_key(key)
        if is_lfs_pointer(body):
            raise ValueError(LFS_POINTER_ERROR.format(action="to upload", key=full_key))
        digest = sha256_hex(body)
        try:
            self._s3.upload_bytes(
                full_key,
                body,
                content_type=_content_type_for(full_key),
                metadata={SHA256_METADATA_KEY: digest},
                if_none_match=None if allow_overwrite else "*",
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in PRECONDITION_FAILED_ERROR_CODES:
                raise FileExistsError(
                    f"Object already exists: s3://{self.bucket}/{full_key}"
                ) from e
            raise
        return digest

    def put_file(
        self, local_path: str | Path, key: str, *, allow_overwrite: bool = False
    ) -> str:
        return self.put_bytes(key, Path(local_path).read_bytes(), allow_overwrite=allow_overwrite)


def _content_type_for(key: str) -> str:
    return CONTENT_TYPES_BY_SUFFIX.get(Path(key).suffix.lower(), DEFAULT_CONTENT_TYPE)


def resolve_object_store(*, local_root: Path) -> ObjectStore:
    """Return the store selected by ``DATA_PLATFORM_STORAGE_BACKEND``.

    Unset or ``local`` returns a ``LocalObjectStore`` over ``local_root``.
    ``s3`` returns an ``S3ObjectStore`` over ``DATA_PLATFORM_S3_BUCKET``
    (default ``mirrorview-experimental-artifacts``).

    Raises
    ------
    ValueError
        When the backend value is not ``local`` or ``s3``.
    """
    backend = os.environ.get(STORAGE_BACKEND_ENV_VAR, LOCAL_BACKEND).strip().lower()
    if backend == LOCAL_BACKEND:
        return LocalObjectStore(local_root)
    if backend == S3_BACKEND:
        bucket = os.environ.get(S3_BUCKET_ENV_VAR, DEFAULT_S3_BUCKET)
        return S3ObjectStore(bucket)
    raise ValueError(
        f"{STORAGE_BACKEND_ENV_VAR} must be {LOCAL_BACKEND!r} or {S3_BACKEND!r}, got {backend!r}"
    )
