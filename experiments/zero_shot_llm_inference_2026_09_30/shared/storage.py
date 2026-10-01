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
_PREDICTIONS_SEGMENT = "predictions"
_FAILURES_SEGMENT = "failures"
_MANIFESTS_SEGMENT = "manifests"
_BATCH_FILE_PREFIX = "batch-"
_MANIFEST_FILE_PREFIX = "manifest-"
_SEQUENCE_WIDTH = 6
_JSONL_SUFFIX = ".jsonl"
_JSON_SUFFIX = ".json"


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


def build_predictions_prefix(run_id: str, model_folder: str) -> str:
    """Return the predictions prefix for one model folder under a run."""
    return build_model_run_prefix(run_id, model_folder) + f"{_PREDICTIONS_SEGMENT}/"


def build_failures_prefix(run_id: str, model_folder: str) -> str:
    """Return the failures prefix for one model folder under a run."""
    return build_model_run_prefix(run_id, model_folder) + f"{_FAILURES_SEGMENT}/"


def build_manifests_prefix(run_id: str, model_folder: str) -> str:
    """Return the manifests prefix for one model folder under a run."""
    return build_model_run_prefix(run_id, model_folder) + f"{_MANIFESTS_SEGMENT}/"


def build_prediction_batch_key(run_id: str, model_folder: str, sequence: int) -> str:
    """Return the immutable prediction batch key for ``sequence``.

    Raises
    ------
    ValueError
        When ``sequence`` is negative or path segments are unsafe.
    """
    return _build_batch_key(run_id, model_folder, _PREDICTIONS_SEGMENT, sequence)


def build_failure_batch_key(run_id: str, model_folder: str, sequence: int) -> str:
    """Return the immutable failure batch key for ``sequence``.

    Raises
    ------
    ValueError
        When ``sequence`` is negative or path segments are unsafe.
    """
    return _build_batch_key(run_id, model_folder, _FAILURES_SEGMENT, sequence)


def build_manifest_key(run_id: str, model_folder: str, sequence: int) -> str:
    """Return the immutable manifest key for ``sequence``.

    Raises
    ------
    ValueError
        When ``sequence`` is negative or path segments are unsafe.
    """
    _validate_sequence(sequence)
    filename = f"{_MANIFEST_FILE_PREFIX}{sequence:0{_SEQUENCE_WIDTH}d}{_JSON_SUFFIX}"
    prefix = build_manifests_prefix(run_id, model_folder)
    return prefix + filename


def next_sequence_for_prefix(
    store: CampaignObjectStore,
    prefix: str,
    file_prefix: str,
    suffix: str,
) -> int:
    """Return the next six-digit sequence under ``prefix`` for ``file_prefix``."""
    keys = store.list_keys(prefix)
    return _max_sequence_from_keys(keys, prefix, file_prefix, suffix) + 1


def _build_batch_key(
    run_id: str,
    model_folder: str,
    artifact_segment: str,
    sequence: int,
) -> str:
    _validate_sequence(sequence)
    filename = f"{_BATCH_FILE_PREFIX}{sequence:0{_SEQUENCE_WIDTH}d}{_JSONL_SUFFIX}"
    run_prefix = build_model_run_prefix(run_id, model_folder)
    return run_prefix + f"{artifact_segment}/" + filename


def _validate_sequence(sequence: int) -> None:
    if sequence < 0:
        raise ValueError("sequence must be nonnegative")


def _max_sequence_from_keys(
    keys: list[str],
    prefix: str,
    file_prefix: str,
    suffix: str,
) -> int:
    max_sequence = -1
    for key in keys:
        if not key.startswith(prefix):
            continue
        filename = key[len(prefix) :]
        parsed = _parse_sequence_filename(filename, file_prefix, suffix)
        if parsed is None:
            continue
        max_sequence = max(max_sequence, parsed)
    return max_sequence


def _parse_sequence_filename(
    filename: str,
    file_prefix: str,
    suffix: str,
) -> int | None:
    if not filename.startswith(file_prefix) or not filename.endswith(suffix):
        return None
    middle = filename[len(file_prefix) : -len(suffix)]
    if len(middle) != _SEQUENCE_WIDTH or not middle.isdigit():
        return None
    return int(middle)


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
