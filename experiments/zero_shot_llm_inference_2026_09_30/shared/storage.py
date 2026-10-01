"""S3 key helpers, serialization, and immutable writes for the experiment.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import TYPE_CHECKING, Any

from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import EXPERIMENT_S3_ROOT
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import Study2InputRecord

if TYPE_CHECKING:
    from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

_RUNS_SEGMENT = "runs"


def apply_lab_aws_credentials_when_unset() -> None:
    """Copy lab AWS env vars into standard names when those are empty."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        access_key = os.environ.get("LAB_AWS_ACCESS_KEY_ID", "")
        if access_key:
            os.environ["AWS_ACCESS_KEY_ID"] = access_key
    if not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        secret_key = os.environ.get("LAB_AWS_ACCESS_KEY_SECRET", "")
        if secret_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key


def validate_path_segment(segment: str) -> str:
    """Return ``segment`` when it is one safe path component.

    Raises
    ------
    ValueError
        When the segment is empty, unsafe, or contains slashes.
    """
    if segment != segment.strip():
        raise ValueError("path segment must not have leading or trailing whitespace")
    if not segment or segment in {".", ".."}:
        raise ValueError("path segment must be nonempty and not . or ..")
    if "/" in segment or "\\" in segment:
        raise ValueError("path segment must not contain slashes")
    return segment


def join_experiment_key(*segments: str) -> str:
    """Join path segments below the fixed experiment S3 root.

    Raises
    ------
    ValueError
        When any segment fails validation or the key escapes the root.
    """
    if not segments:
        raise ValueError("at least one path segment is required")
    safe_segments = [validate_path_segment(segment) for segment in segments]
    joined = EXPERIMENT_S3_ROOT + "/".join(safe_segments)
    if not joined.startswith(EXPERIMENT_S3_ROOT):
        raise ValueError("constructed key must remain under the experiment root")
    return joined


def build_model_run_prefix(run_id: str, model_folder: str) -> str:
    """Return the S3 prefix for one model folder under a run."""
    safe_run_id = validate_path_segment(run_id)
    safe_folder = validate_path_segment(model_folder)
    return join_experiment_key(_RUNS_SEGMENT, safe_run_id, safe_folder) + "/"


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hex digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def serialize_json_document(value: dict[str, Any]) -> bytes:
    """Serialize one JSON object as compact UTF-8 bytes with a final newline."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return (encoded + "\n").encode("utf-8")


def serialize_study2_input_jsonl(records: list[Study2InputRecord]) -> bytes:
    """Serialize prepared records as sorted-key JSONL with a final newline."""
    lines = [_serialize_record_line(record) for record in records]
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def put_immutable_object(
    store: CampaignObjectStore,
    key: str,
    body: bytes,
) -> None:
    """Create one object with ``put_new`` and no overwrite behavior.

    Raises
    ------
    FileExistsError
        When the object key already exists in the store.
    """
    store.put_new(key, body)


def object_exists(store: CampaignObjectStore, key: str) -> bool:
    """Return whether ``key`` is already present in the store."""
    return store.get(key) is not None


def _serialize_record_line(record: Study2InputRecord) -> str:
    payload = record.model_dump()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
