"""S3 key helpers, serialization, and immutable writes for the experiment.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import TYPE_CHECKING, Any, TypeVar

from experiments.zero_shot_llm_inference_2026_09_30.shared.config import (
    ZERO_SHOT_VARIANT,
    Study2InferenceVariant,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    FailureRecord,
    InputManifest,
    ModelRunManifest,
    PredictionRecord,
    Study2InputRecord,
)

ModelT = TypeVar("ModelT")

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


def join_experiment_key(
    *segments: str,
    variant: Study2InferenceVariant | None = None,
) -> str:
    """Join path segments below the active experiment S3 root.

    Parameters
    ----------
    variant
        Active experiment. Omitted calls use the zero-shot variant.

    Raises
    ------
    ValueError
        When any segment fails validation or the key escapes the root.
    """
    active = _active_variant(variant)
    if not segments:
        raise ValueError("at least one path segment is required")
    safe_segments = [validate_path_segment(segment) for segment in segments]
    joined = active.s3_root + "/".join(safe_segments)
    if not joined.startswith(active.s3_root):
        raise ValueError("constructed key must remain under the experiment root")
    return joined


def build_model_run_prefix(
    run_id: str | Study2InferenceVariant,
    model_folder: str,
    variant: Study2InferenceVariant | str | None = None,
) -> str:
    """Return the S3 prefix for one model folder under a run.

    Parameters
    ----------
    run_id
        Run identifier, or the active variant when the call is variant-first.
    variant
        Active experiment for the run-id-first form. Omitted calls use zero-shot.
    """
    active, resolved_run_id, resolved_folder = _resolve_model_run_prefix_args(
        run_id,
        model_folder,
        variant,
    )
    safe_run_id = validate_path_segment(resolved_run_id)
    safe_folder = validate_path_segment(resolved_folder)
    return join_experiment_key(
        _RUNS_SEGMENT,
        safe_run_id,
        safe_folder,
        variant=active,
    ) + "/"


def _resolve_model_run_prefix_args(
    run_id: str | Study2InferenceVariant,
    model_folder: str,
    variant: Study2InferenceVariant | str | None,
) -> tuple[Study2InferenceVariant, str, str]:
    if isinstance(run_id, Study2InferenceVariant):
        if not isinstance(variant, str):
            raise ValueError("model folder is required when the variant is passed first")
        return run_id, model_folder, variant
    if isinstance(variant, str):
        raise ValueError("variant must be a Study2InferenceVariant")
    if not isinstance(run_id, str):
        raise ValueError("run_id must be a path segment")
    return _active_variant(variant), run_id, model_folder


def build_predictions_prefix(
    run_id: str,
    model_folder: str,
    variant: Study2InferenceVariant | None = None,
) -> str:
    """Return the predictions prefix for one model folder under a run."""
    return build_model_run_prefix(run_id, model_folder, variant) + f"{_PREDICTIONS_SEGMENT}/"


def build_failures_prefix(
    run_id: str,
    model_folder: str,
    variant: Study2InferenceVariant | None = None,
) -> str:
    """Return the failures prefix for one model folder under a run."""
    return build_model_run_prefix(run_id, model_folder, variant) + f"{_FAILURES_SEGMENT}/"


def build_manifests_prefix(
    run_id: str,
    model_folder: str,
    variant: Study2InferenceVariant | None = None,
) -> str:
    """Return the manifests prefix for one model folder under a run."""
    return build_model_run_prefix(run_id, model_folder, variant) + f"{_MANIFESTS_SEGMENT}/"


def build_prediction_batch_key(
    run_id: str,
    model_folder: str,
    sequence: int,
    variant: Study2InferenceVariant | None = None,
) -> str:
    """Return the immutable prediction batch key for ``sequence``.

    Raises
    ------
    ValueError
        When ``sequence`` is negative or path segments are unsafe.
    """
    return _build_batch_key(run_id, model_folder, _PREDICTIONS_SEGMENT, sequence, variant)


def build_failure_batch_key(
    run_id: str,
    model_folder: str,
    sequence: int,
    variant: Study2InferenceVariant | None = None,
) -> str:
    """Return the immutable failure batch key for ``sequence``.

    Raises
    ------
    ValueError
        When ``sequence`` is negative or path segments are unsafe.
    """
    return _build_batch_key(run_id, model_folder, _FAILURES_SEGMENT, sequence, variant)


def build_manifest_key(
    run_id: str,
    model_folder: str,
    sequence: int,
    variant: Study2InferenceVariant | None = None,
) -> str:
    """Return the immutable manifest key for ``sequence``.

    Raises
    ------
    ValueError
        When ``sequence`` is negative or path segments are unsafe.
    """
    _validate_sequence(sequence)
    filename = f"{_MANIFEST_FILE_PREFIX}{sequence:0{_SEQUENCE_WIDTH}d}{_JSON_SUFFIX}"
    prefix = build_manifests_prefix(run_id, model_folder, variant)
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
    variant: Study2InferenceVariant | None,
) -> str:
    _validate_sequence(sequence)
    filename = f"{_BATCH_FILE_PREFIX}{sequence:0{_SEQUENCE_WIDTH}d}{_JSONL_SUFFIX}"
    run_prefix = build_model_run_prefix(run_id, model_folder, variant)
    return run_prefix + f"{artifact_segment}/" + filename


def _active_variant(variant: Study2InferenceVariant | None) -> Study2InferenceVariant:
    if variant is None:
        return ZERO_SHOT_VARIANT
    return variant


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


def _sorted_artifact_keys(keys: list[str], prefix: str, suffix: str) -> list[str]:
    matching = [key for key in keys if key.startswith(prefix) and key.endswith(suffix)]
    return sorted(matching)


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


def load_verified_prepared_input(
    store: CampaignObjectStore,
    variant: Study2InferenceVariant | None = None,
) -> tuple[InputManifest, tuple[Study2InputRecord, ...]]:
    """Load prepared input bytes, verify digest, and parse records.

    Parameters
    ----------
    variant
        Active experiment. Omitted calls use the zero-shot variant.

    Raises
    ------
    ValueError
        When manifest or records are missing, digest mismatches, or IDs duplicate.
    """
    active = _active_variant(variant)
    manifest = _load_input_manifest(store, active)
    if manifest.records_s3_key != active.input_records_s3_key:
        raise ValueError("prepared input records key does not match the active variant")
    records_bytes = _load_required_bytes(store, manifest.records_s3_key)
    digest = sha256_hex(records_bytes)
    if digest != manifest.records_sha256:
        raise ValueError("prepared input records digest mismatch")
    records = parse_study2_input_jsonl_bytes(records_bytes)
    _assert_unique_post_ids(records)
    return manifest, tuple(records)


def parse_study2_input_jsonl_bytes(data: bytes) -> list[Study2InputRecord]:
    """Parse prepared input JSONL bytes into validated records."""
    return _parse_jsonl_lines(data, Study2InputRecord)


def parse_jsonl_document_bytes(
    data: bytes,
    model_type: type[ModelT],
) -> list[ModelT]:
    """Parse JSONL bytes into validated Pydantic rows."""
    return _parse_jsonl_lines(data, model_type)


def serialize_jsonl_models(rows: list[ModelT]) -> bytes:
    """Serialize Pydantic rows as sorted-key JSONL with a final newline."""
    if not rows:
        return b""
    lines = [
        json.dumps(row.model_dump(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for row in rows
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def load_json_objects_under_prefix(
    store: CampaignObjectStore,
    prefix: str,
    suffix: str,
    model_type: type[ModelT],
) -> list[tuple[str, ModelT]]:
    """Load one JSON object per key under ``prefix`` ending in ``suffix``."""
    keys = _sorted_artifact_keys(store.list_keys(prefix), prefix, suffix)
    loaded: list[tuple[str, ModelT]] = []
    for key in keys:
        stored = store.get(key)
        if stored is None:
            raise ValueError(f"missing object listed under prefix: {key}")
        loaded.append((key, model_type.model_validate_json(stored.body)))
    return loaded


def load_jsonl_records_under_prefix(
    store: CampaignObjectStore,
    prefix: str,
    model_type: type[ModelT],
) -> list[tuple[str, list[ModelT]]]:
    """Load JSONL batches under ``prefix``."""
    keys = _sorted_artifact_keys(store.list_keys(prefix), prefix, _JSONL_SUFFIX)
    loaded: list[tuple[str, list[ModelT]]] = []
    for key in keys:
        stored = store.get(key)
        if stored is None:
            raise ValueError(f"missing object listed under prefix: {key}")
        loaded.append((key, parse_jsonl_document_bytes(stored.body, model_type)))
    return loaded


def _load_input_manifest(
    store: CampaignObjectStore,
    variant: Study2InferenceVariant,
) -> InputManifest:
    manifest_bytes = _load_required_bytes(store, variant.input_manifest_s3_key)
    return InputManifest.model_validate_json(manifest_bytes)


def _load_required_bytes(store: CampaignObjectStore, key: str) -> bytes:
    stored = store.get(key)
    if stored is None:
        raise ValueError(f"missing required object: {key}")
    return stored.body


def _parse_jsonl_lines(data: bytes, model_type: type[ModelT]) -> list[ModelT]:
    text = data.decode("utf-8")
    if not text.strip():
        return []
    records: list[ModelT] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"empty JSONL line at line {line_number}")
        try:
            records.append(model_type.model_validate_json(line))
        except ValueError as error:
            raise ValueError(f"invalid JSONL at line {line_number}: {error}") from error
    return records


def _assert_unique_post_ids(records: list[Study2InputRecord]) -> None:
    seen: set[str] = set()
    for record in records:
        if record.post_id in seen:
            raise ValueError(f"duplicate prepared post_id: {record.post_id}")
        seen.add(record.post_id)


def _serialize_record_line(record: Study2InputRecord) -> str:
    payload = record.model_dump()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
