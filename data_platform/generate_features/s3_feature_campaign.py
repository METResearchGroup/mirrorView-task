"""S3 layout and small mutable files of one feature in an LLM labeling campaign.

Owns the per-feature prefix, the boto3 calls the campaign needs (conditional
put, conditional replace, get with ETag, delete, list, tags), and the read,
append, and conditional replace pattern behind ``manifest.json``,
``progress.jsonl``, ``errors.jsonl``, and ``active_openai_batch.json``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data_platform.generate_features.models import CampaignRunConfig, FeatureSpec
from data_platform.utils.object_store import DEFAULT_S3_REGION

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
MAX_CONDITIONAL_WRITE_ATTEMPTS = 5


def run_id_for_feature(campaign_id: str, feature: str) -> str:
    """Return ``{campaign_id}:{feature}``, the ``run_id`` stored on every row."""
    raise NotImplementedError


def feature_prefix(
    campaign_id: str,
    feature: str,
    *,
    platform: str = DEFAULT_CAMPAIGN_PLATFORM,
    dataset_id: str = DEFAULT_CAMPAIGN_DATASET_ID,
) -> str:
    """Return the bucket key prefix of one campaign feature, ending in ``/``."""
    raise NotImplementedError


def s3_uri(bucket: str, key: str) -> str:
    raise NotImplementedError


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Split ``s3://bucket/key`` into ``(bucket, key)``."""
    raise NotImplementedError


@dataclass(frozen=True)
class FeaturePaths:
    """Bucket and per-feature prefix of one campaign feature, plus its object keys."""

    bucket: str
    prefix: str

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
        raise NotImplementedError

    @classmethod
    def from_root_uri(cls, root_uri: str, feature: str) -> FeaturePaths:
        """Paths under an arbitrary ``s3://bucket/prefix/`` root, used by the smoke helper."""
        raise NotImplementedError

    @property
    def active_state_key(self) -> str:
        raise NotImplementedError

    @property
    def manifest_key(self) -> str:
        raise NotImplementedError

    @property
    def progress_key(self) -> str:
        raise NotImplementedError

    @property
    def errors_key(self) -> str:
        raise NotImplementedError

    @property
    def final_key(self) -> str:
        raise NotImplementedError

    @property
    def smoke_output_key(self) -> str:
        raise NotImplementedError

    @property
    def batches_prefix(self) -> str:
        raise NotImplementedError

    def batch_key(self, part_index: int) -> str:
        raise NotImplementedError

    def uri(self, key: str) -> str:
        raise NotImplementedError


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


class CampaignObjectStore:
    """The few S3 operations a campaign feature writer needs, on one bucket."""

    def __init__(self, bucket: str, *, region_name: str = DEFAULT_S3_REGION) -> None:
        raise NotImplementedError

    @property
    def bucket(self) -> str:
        raise NotImplementedError

    def get(self, key: str) -> StoredObject | None:
        raise NotImplementedError

    def put_new(self, key: str, body: bytes, *, tags: dict[str, str] | None = None) -> WriteResult:
        """Create an object that must not exist yet.

        Raises
        ------
        FileExistsError
            When the key already exists.
        """
        raise NotImplementedError

    def replace(self, key: str, body: bytes, *, etag: str | None) -> WriteResult:
        """Replace an object only if its ETag still equals ``etag``, or create it when ``etag`` is None.

        Raises
        ------
        ConditionalWriteConflict
            When another writer changed or created the object first.
        """
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def list_keys(self, prefix: str) -> list[str]:
        raise NotImplementedError

    def get_tags(self, key: str) -> dict[str, str]:
        raise NotImplementedError

    def append_jsonl(self, key: str, records: list[dict[str, Any]]) -> None:
        """Logically append newline terminated JSON records through read, append, and conditional replace."""
        raise NotImplementedError


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
