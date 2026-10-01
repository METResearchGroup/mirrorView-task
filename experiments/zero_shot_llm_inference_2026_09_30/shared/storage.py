"""S3 key helpers, serialization, and immutable writes for the experiment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore


def apply_lab_aws_credentials_when_unset() -> None:
    """Copy lab AWS env vars into standard names when those are empty."""
    raise NotImplementedError


def join_experiment_key(*segments: str) -> str:
    """Join path segments below the fixed experiment S3 root."""
    raise NotImplementedError


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hex digest of ``data``."""
    raise NotImplementedError


def serialize_json_document(value: dict[str, Any]) -> bytes:
    """Serialize one JSON object as compact UTF-8 bytes with a final newline."""
    raise NotImplementedError


def serialize_study2_input_jsonl(records: list[Any]) -> bytes:
    """Serialize prepared records as sorted-key JSONL with a final newline."""
    raise NotImplementedError


def put_immutable_object(
    store: CampaignObjectStore,
    key: str,
    body: bytes,
) -> None:
    """Create one object with ``put_new`` and no overwrite behavior."""
    raise NotImplementedError
