"""S3 layout and small mutable files of one feature in an LLM labeling campaign.

Owns the per-feature prefix, the boto3 calls the campaign needs (conditional
put, conditional replace, get with ETag, delete, list, tags), and the read,
append, and conditional replace pattern behind ``manifest.json``,
``progress.jsonl``, ``errors.jsonl``, and ``active_openai_batch.json``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import boto3
from botocore.exceptions import ClientError

from data_platform.generate_features.models import CampaignRunConfig, FeatureSpec
from data_platform.utils.object_store import (
    DEFAULT_S3_BUCKET,
    DEFAULT_S3_REGION,
    PRECONDITION_FAILED_ERROR_CODES,
    S3_BUCKET_ENV_VAR,
    S3_KEY_PREFIX,
    sha256_hex,
)
from lib.aws.s3 import NOT_FOUND_ERROR_CODES

DEFAULT_CAMPAIGN_PLATFORM = "bluesky"
DEFAULT_CAMPAIGN_DATASET_ID = "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"
INTERMEDIATE_ARTIFACT_TAG = {"intermediate-artifact": "true"}
ACTIVE_STATE_FILENAME = "active_openai_batch.json"
MANIFEST_FILENAME = "manifest.json"
PROGRESS_FILENAME = "progress.jsonl"
ERRORS_FILENAME = "errors.jsonl"
FINAL_FILENAME = "final.parquet"
BATCHES_DIRNAME = "batches"
SMOKE_OUTPUT_KEY_SUFFIX = "smoke/output.parquet"
FEATURES_STAGE_DIRNAME = "features"
MAX_CONDITIONAL_WRITE_ATTEMPTS = 5
S3_URI_SCHEME = "s3://"
# S3 answers a conditional write that lost a race with 412 or, mid-upload, 409.
CONDITIONAL_CONFLICT_ERROR_CODES = frozenset(
    {*PRECONDITION_FAILED_ERROR_CODES, "ConditionalRequestConflict", "409"}
)
CONTENT_TYPES_BY_SUFFIX = {
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".parquet": "application/octet-stream",
}
DEFAULT_CONTENT_TYPE = "application/octet-stream"


def run_id_for_feature(campaign_id: str, feature: str) -> str:
    """Return ``{campaign_id}:{feature}``, the ``run_id`` stored on every row."""
    return f"{campaign_id}:{feature}"


def feature_prefix(
    campaign_id: str,
    feature: str,
    *,
    platform: str = DEFAULT_CAMPAIGN_PLATFORM,
    dataset_id: str = DEFAULT_CAMPAIGN_DATASET_ID,
) -> str:
    """Return the bucket key prefix of one campaign feature, ending in ``/``."""
    return (
        f"{S3_KEY_PREFIX}/{platform}/{dataset_id}/{FEATURES_STAGE_DIRNAME}/"
        f"{campaign_id}/{feature}/"
    )


def s3_uri(bucket: str, key: str) -> str:
    return f"{S3_URI_SCHEME}{bucket}/{key}"


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Split ``s3://bucket/key`` into ``(bucket, key)``.

    Raises
    ------
    ValueError
        When ``uri`` does not start with ``s3://`` or has no bucket.
    """
    if not uri.startswith(S3_URI_SCHEME):
        raise ValueError(f"expected an s3:// URI, got {uri!r}")
    bucket, _, key = uri[len(S3_URI_SCHEME) :].partition("/")
    if not bucket:
        raise ValueError(f"s3 URI has no bucket: {uri!r}")
    return bucket, key


def _campaign_bucket() -> str:
    return os.environ.get(S3_BUCKET_ENV_VAR, DEFAULT_S3_BUCKET)


@dataclass(frozen=True)
class FeaturePaths:
    """Bucket and per-feature prefix of one campaign feature, plus its object keys."""

    bucket: str
    prefix: str

    def __post_init__(self) -> None:
        if not self.prefix.endswith("/"):
            raise ValueError(f"feature prefix must end with '/', got {self.prefix!r}")

    @classmethod
    def canonical(
        cls,
        campaign_id: str,
        feature: str,
        *,
        bucket: str | None = None,
        platform: str = DEFAULT_CAMPAIGN_PLATFORM,
        dataset_id: str = DEFAULT_CAMPAIGN_DATASET_ID,
    ) -> FeaturePaths:
        return cls(
            bucket=bucket or _campaign_bucket(),
            prefix=feature_prefix(campaign_id, feature, platform=platform, dataset_id=dataset_id),
        )

    @classmethod
    def from_root_uri(cls, root_uri: str, feature: str) -> FeaturePaths:
        """Paths under an arbitrary ``s3://bucket/prefix/`` root, used by the smoke helper."""
        bucket, root_key = parse_s3_uri(root_uri)
        root_key = root_key.rstrip("/")
        prefix = f"{root_key}/{feature}/" if root_key else f"{feature}/"
        return cls(bucket=bucket, prefix=prefix)

    @property
    def active_state_key(self) -> str:
        return f"{self.prefix}{ACTIVE_STATE_FILENAME}"

    @property
    def manifest_key(self) -> str:
        return f"{self.prefix}{MANIFEST_FILENAME}"

    @property
    def progress_key(self) -> str:
        return f"{self.prefix}{PROGRESS_FILENAME}"

    @property
    def errors_key(self) -> str:
        return f"{self.prefix}{ERRORS_FILENAME}"

    @property
    def final_key(self) -> str:
        return f"{self.prefix}{FINAL_FILENAME}"

    @property
    def smoke_output_key(self) -> str:
        return f"{self.prefix}{SMOKE_OUTPUT_KEY_SUFFIX}"

    @property
    def batches_prefix(self) -> str:
        return f"{self.prefix}{BATCHES_DIRNAME}/"

    def batch_key(self, part_index: int) -> str:
        if part_index < 0:
            raise ValueError(f"part_index must be zero or positive, got {part_index}")
        return f"{self.batches_prefix}part-{part_index:05d}.parquet"

    def uri(self, key: str) -> str:
        return s3_uri(self.bucket, key)


@dataclass(frozen=True)
class StoredObject:
    body: bytes
    etag: str


@dataclass(frozen=True)
class WriteResult:
    sha256: str
    etag: str


class ConditionalWriteConflict(RuntimeError):
    """A conditional replace lost to a concurrent write; reload and retry."""


def _error_code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def _content_type_for(key: str) -> str:
    return CONTENT_TYPES_BY_SUFFIX.get(Path(key).suffix.lower(), DEFAULT_CONTENT_TYPE)


class CampaignObjectStore:
    """The few S3 operations a campaign feature writer needs, on one bucket.

    Every write records the SHA-256 of the body as object metadata. The ETag
    returned from writes and reads is used only for ``If-Match`` concurrency
    control and never as a content hash.
    """

    def __init__(self, bucket: str, *, region_name: str = DEFAULT_S3_REGION) -> None:
        self._bucket = bucket
        self._client: Any = boto3.client("s3", region_name=region_name)

    @property
    def bucket(self) -> str:
        return self._bucket

    def get(self, key: str) -> StoredObject | None:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as error:
            if _error_code(error) in NOT_FOUND_ERROR_CODES:
                return None
            raise
        return StoredObject(body=response["Body"].read(), etag=response["ETag"])

    def _put(
        self,
        key: str,
        body: bytes,
        *,
        condition: dict[str, str],
        tags: dict[str, str] | None,
    ) -> WriteResult:
        digest = sha256_hex(body)
        extra: dict[str, Any] = {
            "ContentType": _content_type_for(key),
            "Metadata": {"sha256": digest},
            **condition,
        }
        if tags:
            extra["Tagging"] = urlencode(tags)
        response = self._client.put_object(Bucket=self._bucket, Key=key, Body=body, **extra)
        return WriteResult(sha256=digest, etag=response["ETag"])

    def put_new(self, key: str, body: bytes, *, tags: dict[str, str] | None = None) -> WriteResult:
        """Create an object that must not exist yet.

        Raises
        ------
        FileExistsError
            When the key already exists.
        """
        try:
            return self._put(key, body, condition={"IfNoneMatch": "*"}, tags=tags)
        except ClientError as error:
            if _error_code(error) in CONDITIONAL_CONFLICT_ERROR_CODES:
                raise FileExistsError(
                    f"Object already exists: {s3_uri(self._bucket, key)}"
                ) from error
            raise

    def replace(self, key: str, body: bytes, *, etag: str | None) -> WriteResult:
        """Replace an object only if its ETag still equals ``etag``, or create it when ``etag`` is None.

        Raises
        ------
        ConditionalWriteConflict
            When another writer changed or created the object first.
        """
        condition = {"IfNoneMatch": "*"} if etag is None else {"IfMatch": etag}
        try:
            return self._put(key, body, condition=condition, tags=None)
        except ClientError as error:
            if _error_code(error) in CONDITIONAL_CONFLICT_ERROR_CODES:
                raise ConditionalWriteConflict(
                    f"Conditional write lost for {s3_uri(self._bucket, key)}"
                ) from error
            raise

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def list_keys(self, prefix: str) -> list[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        keys = [
            item["Key"]
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix)
            for item in page.get("Contents", [])
        ]
        return sorted(keys)

    def get_tags(self, key: str) -> dict[str, str]:
        response = self._client.get_object_tagging(Bucket=self._bucket, Key=key)
        return {tag["Key"]: tag["Value"] for tag in response.get("TagSet", [])}

    def append_jsonl(self, key: str, records: list[dict[str, Any]]) -> None:
        """Logically append newline terminated JSON records through read, append, and conditional replace.

        Raises
        ------
        ConditionalWriteConflict
            When ``MAX_CONDITIONAL_WRITE_ATTEMPTS`` replaces in a row lost to
            another writer.
        """
        if not records:
            return
        addition = "".join(f"{json.dumps(record)}\n" for record in records).encode("utf-8")
        for _ in range(MAX_CONDITIONAL_WRITE_ATTEMPTS):
            current = self.get(key)
            body = (current.body if current else b"") + addition
            try:
                self.replace(key, body, etag=current.etag if current else None)
                return
            except ConditionalWriteConflict:
                continue
        raise ConditionalWriteConflict(
            f"append to {s3_uri(self._bucket, key)} lost {MAX_CONDITIONAL_WRITE_ATTEMPTS} times"
        )


def new_manifest(
    *,
    campaign: CampaignRunConfig,
    spec: FeatureSpec,
    expected_row_count: int,
) -> dict[str, Any]:
    raise NotImplementedError


def load_manifest(
    store: CampaignObjectStore, paths: FeaturePaths
) -> tuple[dict[str, Any] | None, str | None]:
    raise NotImplementedError


def save_manifest(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    etag: str | None,
) -> str:
    """Conditionally replace ``manifest.json`` and return its new ETag."""
    raise NotImplementedError


def load_active_state(
    store: CampaignObjectStore, paths: FeaturePaths
) -> tuple[dict[str, Any] | None, str | None]:
    raise NotImplementedError


def save_active_state(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    state: dict[str, Any],
    etag: str | None,
) -> str:
    raise NotImplementedError


def delete_active_state(store: CampaignObjectStore, paths: FeaturePaths) -> None:
    raise NotImplementedError


def append_progress(
    store: CampaignObjectStore, paths: FeaturePaths, record: dict[str, Any]
) -> None:
    raise NotImplementedError


def append_errors(
    store: CampaignObjectStore, paths: FeaturePaths, records: list[dict[str, Any]]
) -> None:
    raise NotImplementedError


class ActiveStateMirror:
    """Keeps the engine's local ``active_openai_batch.json`` and its S3 copy in step.

    The OpenAI engine only writes its state file to a local run directory.
    The mirror copies that file to S3 whenever the engine waits between polls
    and whenever rows arrive, and it seeds the local file from S3 before a
    chunk starts so a process on a new machine reattaches to the same job.
    """

    def __init__(
        self,
        store: CampaignObjectStore,
        paths: FeaturePaths,
        *,
        run_dir: Path,
        feature_name: str,
        campaign_id: str,
    ) -> None:
        raise NotImplementedError

    def seed_local(self) -> None:
        """Write the S3 state to the local state path when the local file is missing."""
        raise NotImplementedError

    def sync(self) -> None:
        """Copy the local state file to S3 when its content changed since the last sync."""
        raise NotImplementedError

    def sleep(self, seconds: float) -> None:
        """``sleep_fn`` for the engine: sync, then sleep."""
        raise NotImplementedError
