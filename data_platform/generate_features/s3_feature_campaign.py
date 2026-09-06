"""S3 layout and small mutable files of one feature in an LLM labeling campaign.

Owns the per-feature prefix, the boto3 calls the campaign needs (conditional
put, conditional replace, get with ETag, delete, list, tags), and the read,
append, and conditional replace pattern behind ``manifest.json``,
``progress.jsonl``, ``errors.jsonl``, ``watcher.json``, and
``active_openai_batch.json``.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import boto3
from botocore.exceptions import ClientError

from data_platform.generate_features.metadata import model_id_for_spec, prompt_hash
from data_platform.generate_features.models import CampaignRunConfig, FeatureSpec
from data_platform.generate_features.openai_batch_state import (
    load_active_batch_state,
    write_active_batch_state,
)
from data_platform.utils.object_store import (
    DEFAULT_S3_BUCKET,
    DEFAULT_S3_REGION,
    PRECONDITION_FAILED_ERROR_CODES,
    S3_BUCKET_ENV_VAR,
    S3_KEY_PREFIX,
    sha256_hex,
)
from lib.aws.s3 import NOT_FOUND_ERROR_CODES
from lib.timestamp_utils import get_current_timestamp

DEFAULT_CAMPAIGN_PLATFORM = "bluesky"
DEFAULT_CAMPAIGN_DATASET_ID = "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"
INTERMEDIATE_ARTIFACT_TAG = {"intermediate-artifact": "true"}
ACTIVE_STATE_FILENAME = "active_openai_batch.json"
MANIFEST_FILENAME = "manifest.json"
PROGRESS_FILENAME = "progress.jsonl"
ERRORS_FILENAME = "errors.jsonl"
WATCHER_FILENAME = "watcher.json"
FINAL_FILENAME = "final.parquet"
BATCHES_DIRNAME = "batches"
SMOKE_DIRNAME = "smoke"
SMOKE_INPUT_KEY_SUFFIX = f"{SMOKE_DIRNAME}/input.parquet"
SMOKE_OUTPUT_KEY_SUFFIX = f"{SMOKE_DIRNAME}/output.parquet"
SMOKE_COST_REPORT_KEY_SUFFIX = f"{SMOKE_DIRNAME}/cost_report.json"
SMOKE_RESUME_EVIDENCE_KEY_SUFFIX = f"{SMOKE_DIRNAME}/resume_evidence.json"
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
    """Return the ``s3://bucket/key`` form of one object key."""
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
        """Paths under the pinned campaign feature prefix, in the bucket named by the environment by default."""
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
    def watcher_key(self) -> str:
        return f"{self.prefix}{WATCHER_FILENAME}"

    @property
    def final_key(self) -> str:
        return f"{self.prefix}{FINAL_FILENAME}"

    @property
    def smoke_prefix(self) -> str:
        return f"{self.prefix}{SMOKE_DIRNAME}/"

    @property
    def smoke_input_key(self) -> str:
        return f"{self.prefix}{SMOKE_INPUT_KEY_SUFFIX}"

    @property
    def smoke_output_key(self) -> str:
        return f"{self.prefix}{SMOKE_OUTPUT_KEY_SUFFIX}"

    @property
    def smoke_cost_report_key(self) -> str:
        return f"{self.prefix}{SMOKE_COST_REPORT_KEY_SUFFIX}"

    @property
    def smoke_resume_evidence_key(self) -> str:
        return f"{self.prefix}{SMOKE_RESUME_EVIDENCE_KEY_SUFFIX}"

    @property
    def batches_prefix(self) -> str:
        return f"{self.prefix}{BATCHES_DIRNAME}/"

    def batch_key(self, part_index: int) -> str:
        """Return the immutable object key of chunk ``part_index``; raises ``ValueError`` when negative."""
        if part_index < 0:
            raise ValueError(f"part_index must be zero or positive, got {part_index}")
        return f"{self.batches_prefix}part-{part_index:05d}.parquet"

    def uri(self, key: str) -> str:
        return s3_uri(self.bucket, key)


@dataclass(frozen=True)
class StoredObject:
    """Bytes of one S3 object with the ETag to pass back as ``If-Match`` on a later replace."""

    body: bytes
    etag: str


@dataclass(frozen=True)
class WriteResult:
    """SHA-256 of the bytes just written and the ETag S3 assigned to them."""

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
        """Return the object at ``key``, or None when it does not exist."""
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
        """Delete ``key``; deleting a missing key is not an error."""
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def list_keys(self, prefix: str) -> list[str]:
        """Return every key under ``prefix`` in sorted order, following pagination."""
        paginator = self._client.get_paginator("list_objects_v2")
        keys = [
            item["Key"]
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix)
            for item in page.get("Contents", [])
        ]
        return sorted(keys)

    def get_tags(self, key: str) -> dict[str, str]:
        """Return the object tags of ``key`` as a plain mapping."""
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


def _json_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, indent=2).encode("utf-8")


def _load_json(
    store: CampaignObjectStore, key: str
) -> tuple[dict[str, Any] | None, str | None]:
    stored = store.get(key)
    if stored is None:
        return None, None
    return json.loads(stored.body.decode("utf-8")), stored.etag


def new_manifest(
    *,
    campaign: CampaignRunConfig,
    spec: FeatureSpec,
    expected_row_count: int,
) -> dict[str, Any]:
    """Return a manifest with the campaign identity, an empty batch list, and no final file."""
    return {
        "campaign_id": campaign.campaign_id,
        "dataset_id": campaign.dataset_id,
        "preprocessed_run": campaign.preprocessed_run,
        "feature": spec.name,
        "model_id": model_id_for_spec(spec),
        "prompt_hash": prompt_hash(spec.system_prompt),
        "batch_size": campaign.batch_size,
        "expected_row_count": expected_row_count,
        "run_id": run_id_for_feature(campaign.campaign_id, spec.name),
        "created_at": get_current_timestamp(),
        "batches": [],
        "final_parquet": None,
    }


def load_manifest(
    store: CampaignObjectStore, paths: FeaturePaths
) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(manifest, etag)``, or ``(None, None)`` before the first run creates it."""
    return _load_json(store, paths.manifest_key)


def save_manifest(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    etag: str | None,
) -> str:
    """Conditionally replace ``manifest.json`` and return its new ETag.

    Raises
    ------
    ConditionalWriteConflict
        When the object no longer matches ``etag``, or exists while ``etag`` is None.
    """
    return store.replace(paths.manifest_key, _json_bytes(manifest), etag=etag).etag


def load_active_state(
    store: CampaignObjectStore, paths: FeaturePaths
) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(state, etag)`` of the S3 ``active_openai_batch.json``, or ``(None, None)`` when no job is open."""
    return _load_json(store, paths.active_state_key)


def save_active_state(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    state: dict[str, Any],
    etag: str | None,
) -> str:
    """Conditionally replace the S3 active state and return its new ETag; see ``save_manifest`` for the conflict rule."""
    return store.replace(paths.active_state_key, _json_bytes(state), etag=etag).etag


def delete_active_state(store: CampaignObjectStore, paths: FeaturePaths) -> None:
    """Remove the S3 active state once its chunk has a durable batch object."""
    store.delete(paths.active_state_key)


def manifest_sha256(manifest: dict[str, Any]) -> str:
    """Return the SHA-256 of the exact bytes ``save_manifest`` uploads for ``manifest``."""
    return sha256_hex(_json_bytes(manifest))


def append_progress(
    store: CampaignObjectStore, paths: FeaturePaths, record: dict[str, Any]
) -> None:
    """Append one line to ``progress.jsonl``; raises ``ConditionalWriteConflict`` after repeated lost races."""
    store.append_jsonl(paths.progress_key, [record])


def read_progress_lines(store: CampaignObjectStore, paths: FeaturePaths) -> list[str]:
    """Return the lines of ``progress.jsonl``, or an empty list before the first append."""
    stored = store.get(paths.progress_key)
    if stored is None:
        return []
    return stored.body.decode("utf-8").splitlines()


def load_watcher_state(
    store: CampaignObjectStore, paths: FeaturePaths
) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(state, etag)`` of ``watcher.json``, or ``(None, None)`` before the first watcher run."""
    return _load_json(store, paths.watcher_key)


def save_watcher_state(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    state: dict[str, Any],
    etag: str | None,
) -> str:
    """Conditionally replace ``watcher.json`` and return its new ETag; see ``save_manifest`` for the conflict rule."""
    return store.replace(paths.watcher_key, _json_bytes(state), etag=etag).etag


def append_errors(
    store: CampaignObjectStore, paths: FeaturePaths, records: list[dict[str, Any]]
) -> None:
    """Append one line per record to ``errors.jsonl``; a no-op for an empty list."""
    store.append_jsonl(paths.errors_key, records)


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
        self._store = store
        self._paths = paths
        self._run_dir = run_dir
        self._feature_name = feature_name
        self._campaign_id = campaign_id
        self._synced: dict[str, Any] | None = None
        self._etag: str | None = None

    def seed_local(self) -> None:
        """Write the S3 state to the local state path when the local file is missing.

        Also remembers the S3 copy, so the next ``sync`` replaces it with
        ``If-Match`` instead of trying to create it.
        """
        remote, etag = load_active_state(self._store, self._paths)
        self._synced, self._etag = remote, etag
        if remote is None or load_active_batch_state(self._run_dir, self._feature_name) is not None:
            return
        write_active_batch_state(self._run_dir, self._feature_name, remote)

    def sync(self) -> None:
        """Copy the local state file to S3 when its content changed since the last sync.

        The S3 copy carries the campaign id, which the engine leaves unset. A
        missing local file is not an error, because the engine deletes it once
        a chunk is done, and the campaign deletes the S3 copy separately.
        """
        local = load_active_batch_state(self._run_dir, self._feature_name)
        if local is None:
            return
        state = {**local, "campaign_id": self._campaign_id}
        if state == self._synced:
            return
        self._etag = save_active_state(self._store, self._paths, state, self._etag)
        self._synced = state

    def sleep(self, seconds: float) -> None:
        """``sleep_fn`` for the engine: sync, then sleep."""
        self.sync()
        time.sleep(seconds)
