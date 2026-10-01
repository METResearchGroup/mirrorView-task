"""Resumable per-model Bedrock inference for Study 2 zero-shot runs.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from data_platform.generate_features.engines.bedrock_engine import (
    BedrockRuntimeClient,
    BedrockUsage,
    create_bedrock_runtime_client,
)
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import DEFAULT_S3_REGION

from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    EXPERIMENT_S3_BUCKET,
    get_model_definition_by_folder,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.llm import label_record
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    FAILURE_SCHEMA_VERSION,
    FAILURE_WRAPPER_CALL_COUNT,
    MANIFEST_SCHEMA_VERSION,
    FailureRecord,
    InputManifest,
    ModelDefinition,
    ModelRunManifest,
    ModelRunManifestStatus,
    PREDICTION_SCHEMA_VERSION,
    PredictionRecord,
    RemovePrediction,
    Study2InputRecord,
    TokenUsage,
    validate_failure_record_identity,
    validate_model_run_manifest_identity,
    validate_prediction_record_identity,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    build_failure_batch_key,
    build_failures_prefix,
    build_manifest_key,
    build_manifests_prefix,
    build_prediction_batch_key,
    build_predictions_prefix,
    load_json_objects_under_prefix,
    load_jsonl_records_under_prefix,
    load_verified_prepared_input,
    next_sequence_for_prefix,
    put_immutable_object,
    serialize_json_document,
    serialize_jsonl_models,
    validate_path_segment,
)

_BATCH_OBJECT_PREFIX = "batch-"
_JSONL_OBJECT_SUFFIX = ".jsonl"
_MANIFEST_OBJECT_PREFIX = "manifest-"
_JSON_OBJECT_SUFFIX = ".json"


def run_model_inference(
    store: CampaignObjectStore,
    client: BedrockRuntimeClient,
    run_id: str,
    model_folder: str,
    limit: int | None,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
) -> None:
    """Execute one resumable inference pass for a single model folder.

    Raises
    ------
    ValueError
        When prepared input, resume state, or CLI configuration is invalid.
    FileExistsError
        When an immutable write collides with an existing object.
    """
    _load_prepared_input(store)
    _load_resume_state(store, run_id, model_folder, limit)
    _run_pending_batches(
        store,
        client,
        run_id,
        model_folder,
        batch_size,
        max_concurrency,
        max_tokens,
    )
    _write_model_manifest(store, run_id, model_folder)


def _load_prepared_input(store: CampaignObjectStore) -> None:
    raise NotImplementedError


def _load_resume_state(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    limit: int | None,
) -> None:
    raise NotImplementedError


def _run_pending_batches(
    store: CampaignObjectStore,
    client: BedrockRuntimeClient,
    run_id: str,
    model_folder: str,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
) -> None:
    raise NotImplementedError


def _write_model_manifest(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
) -> None:
    raise NotImplementedError


def main() -> None:
    """Parse CLI arguments and run one model inference task."""
    apply_lab_aws_credentials_when_unset()
    args = _parse_args()
    store = CampaignObjectStore(EXPERIMENT_S3_BUCKET, DEFAULT_S3_REGION)
    client = create_bedrock_runtime_client()
    run_model_inference(
        store,
        client,
        args.run_id,
        args.model,
        args.limit,
        args.batch_size,
        args.max_concurrency,
        args.max_tokens,
    )


def _parse_args() -> argparse.Namespace:
    raise NotImplementedError


def validate_positive_optional_limit(limit: int | None) -> None:
    """Reject nonpositive limits while allowing omission.

    Raises
    ------
    ValueError
        When ``limit`` is present but not a positive integer.
    """
    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer when provided")


def select_requested_records(
    records: tuple[Study2InputRecord, ...],
    limit: int | None,
) -> tuple[Study2InputRecord, ...]:
    """Return the ordered requested set after full input validation."""
    if limit is None:
        return records
    return records[:limit]


@dataclass(frozen=True)
class LoadedRunArtifacts:
    """Immutable artifacts already stored for one model run."""

    manifests: tuple[ModelRunManifest, ...]
    prediction_object_keys: tuple[str, ...]
    predictions: tuple[PredictionRecord, ...]
    failure_object_keys: tuple[str, ...]
    failures: tuple[FailureRecord, ...]


def load_existing_run_artifacts(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    model_id: str,
    known_post_ids: frozenset[str],
) -> LoadedRunArtifacts:
    """Load manifests, predictions, and failures for one model folder.

    Raises
    ------
    ValueError
        When stored rows are invalid or conflict with run identity.
    """
    known_ids = known_post_ids
    manifests = _load_manifest_objects(store, run_id, model_folder, model_id)
    prediction_batches = load_jsonl_records_under_prefix(
        store,
        build_predictions_prefix(run_id, model_folder),
        PredictionRecord,
    )
    failure_batches = load_jsonl_records_under_prefix(
        store,
        build_failures_prefix(run_id, model_folder),
        FailureRecord,
    )
    predictions = _flatten_and_validate_predictions(
        prediction_batches,
        run_id,
        model_folder,
        model_id,
        known_ids,
    )
    failures = _flatten_and_validate_failures(
        failure_batches,
        run_id,
        model_folder,
        model_id,
        known_ids,
    )
    return LoadedRunArtifacts(
        manifests=manifests,
        prediction_object_keys=tuple(key for key, _ in prediction_batches),
        predictions=predictions,
        failure_object_keys=tuple(key for key, _ in failure_batches),
        failures=failures,
    )


def completed_post_ids_for_requested_set(
    predictions: tuple[PredictionRecord, ...],
    requested_post_ids: frozenset[str],
) -> frozenset[str]:
    """Return requested post IDs with exactly one stored prediction."""
    counts = Counter(record.post_id for record in predictions)
    completed: set[str] = set()
    for post_id in requested_post_ids:
        count = counts.get(post_id, 0)
        if count > 1:
            raise ValueError(f"duplicate prediction post_id: {post_id}")
        if count == 1:
            completed.add(post_id)
    return frozenset(completed)


def select_pending_records(
    requested_records: tuple[Study2InputRecord, ...],
    completed_post_ids: frozenset[str],
) -> tuple[Study2InputRecord, ...]:
    """Return requested records that still need inference in prepared order."""
    return tuple(
        record for record in requested_records if record.post_id not in completed_post_ids
    )


def map_bedrock_usage_to_token_usage(usage: BedrockUsage) -> TokenUsage:
    """Convert engine usage into the experiment TokenUsage model."""
    return TokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )


def build_prediction_record(
    run_id: str,
    model: ModelDefinition,
    record: Study2InputRecord,
    prediction: RemovePrediction,
    usage: TokenUsage,
) -> PredictionRecord:
    """Build one prediction row for immutable storage."""
    return PredictionRecord(
        schema_version=PREDICTION_SCHEMA_VERSION,
        run_id=run_id,
        model_folder=model.folder_name,
        model_id=model.model_id,
        post_id=record.post_id,
        is_remove=prediction.is_remove,
        p_remove=prediction.p_remove,
        usage=usage,
    )


def build_failure_record(
    run_id: str,
    model: ModelDefinition,
    record: Study2InputRecord,
    error: BaseException,
) -> FailureRecord:
    """Build one failure row for immutable storage."""
    message = str(error).strip()
    if not message:
        message = error.__class__.__name__
    return FailureRecord(
        schema_version=FAILURE_SCHEMA_VERSION,
        run_id=run_id,
        model_folder=model.folder_name,
        model_id=model.model_id,
        post_id=record.post_id,
        exception_type=error.__class__.__name__,
        error_message=message,
        wrapper_call_count=FAILURE_WRAPPER_CALL_COUNT,
    )


def write_prediction_batch_if_nonempty(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    records: list[PredictionRecord],
) -> str | None:
    """Write one immutable prediction JSONL batch when rows are present.

    Raises
    ------
    FileExistsError
        When the target batch key already exists.
    """
    if not records:
        return None
    prefix = build_predictions_prefix(run_id, model_folder)
    sequence = next_sequence_for_prefix(
        store,
        prefix,
        _BATCH_OBJECT_PREFIX,
        _JSONL_OBJECT_SUFFIX,
    )
    key = build_prediction_batch_key(run_id, model_folder, sequence)
    put_immutable_object(store, key, serialize_jsonl_models(records))
    return key


def write_failure_batch_if_nonempty(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    records: list[FailureRecord],
) -> str | None:
    """Write one immutable failure JSONL batch when rows are present.

    Raises
    ------
    FileExistsError
        When the target batch key already exists.
    """
    if not records:
        return None
    prefix = build_failures_prefix(run_id, model_folder)
    sequence = next_sequence_for_prefix(
        store,
        prefix,
        _BATCH_OBJECT_PREFIX,
        _JSONL_OBJECT_SUFFIX,
    )
    key = build_failure_batch_key(run_id, model_folder, sequence)
    put_immutable_object(store, key, serialize_jsonl_models(records))
    return key


def run_ordered_inference_batch(
    client: BedrockRuntimeClient,
    model: ModelDefinition,
    run_id: str,
    pending_records: tuple[Study2InputRecord, ...],
    max_concurrency: int,
    max_tokens: int,
) -> tuple[list[PredictionRecord], list[FailureRecord]]:
    """Run one batch in input order with bounded concurrency."""
    if not pending_records:
        return [], []
    outcomes = _label_records_in_input_order(
        client,
        model,
        run_id,
        pending_records,
        max_concurrency,
        max_tokens,
    )
    return _split_prediction_and_failure_outcomes(outcomes)


def unresolved_failure_post_ids(
    failures: tuple[FailureRecord, ...],
    predictions: tuple[PredictionRecord, ...],
    requested_post_ids: frozenset[str],
) -> frozenset[str]:
    """Return requested post IDs with failures but no valid prediction."""
    predicted_ids = {
        record.post_id for record in predictions if record.post_id in requested_post_ids
    }
    unresolved: set[str] = set()
    for failure in failures:
        if failure.post_id not in requested_post_ids:
            continue
        if failure.post_id not in predicted_ids:
            unresolved.add(failure.post_id)
    return frozenset(unresolved)


def assert_configured_limit_matches_manifests(
    configured_limit: int | None,
    manifests: tuple[ModelRunManifest, ...],
) -> None:
    """Reject a limit change relative to prior manifests for the same run.

    Raises
    ------
    ValueError
        When ``configured_limit`` differs from a stored manifest value.
    """
    for manifest in manifests:
        if manifest.configured_limit != configured_limit:
            raise ValueError("configured limit mismatch with existing manifest")


def _load_manifest_objects(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    model_id: str,
) -> tuple[ModelRunManifest, ...]:
    prefix = build_manifests_prefix(run_id, model_folder)
    loaded = load_json_objects_under_prefix(store, prefix, ".json", ModelRunManifest)
    manifests: list[ModelRunManifest] = []
    for _, manifest in loaded:
        validate_model_run_manifest_identity(manifest, run_id, model_folder, model_id)
        manifests.append(manifest)
    return tuple(manifests)


def _flatten_and_validate_predictions(
    batches: list[tuple[str, list[PredictionRecord]]],
    run_id: str,
    model_folder: str,
    model_id: str,
    known_post_ids: frozenset[str],
) -> tuple[PredictionRecord, ...]:
    predictions: list[PredictionRecord] = []
    seen_post_ids: set[str] = set()
    for _, rows in batches:
        for record in rows:
            validate_prediction_record_identity(
                record,
                run_id,
                model_folder,
                model_id,
                known_post_ids,
            )
            if record.post_id in seen_post_ids:
                raise ValueError(f"duplicate prediction post_id: {record.post_id}")
            seen_post_ids.add(record.post_id)
            predictions.append(record)
    return tuple(predictions)


def _split_prediction_and_failure_outcomes(
    outcomes: list[PredictionRecord | FailureRecord],
) -> tuple[list[PredictionRecord], list[FailureRecord]]:
    predictions: list[PredictionRecord] = []
    failures: list[FailureRecord] = []
    for outcome in outcomes:
        if isinstance(outcome, FailureRecord):
            failures.append(outcome)
            continue
        predictions.append(outcome)
    return predictions, failures


def _label_records_in_input_order(
    client: BedrockRuntimeClient,
    model: ModelDefinition,
    run_id: str,
    records: tuple[Study2InputRecord, ...],
    max_concurrency: int,
    max_tokens: int,
) -> list[PredictionRecord | FailureRecord]:
    indexed_outcomes: list[PredictionRecord | FailureRecord | None] = [None] * len(records)
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        future_to_index = {
            executor.submit(
                _label_single_record,
                client,
                model,
                run_id,
                record,
                max_tokens,
            ): index
            for index, record in enumerate(records)
        }
        for future, index in future_to_index.items():
            indexed_outcomes[index] = future.result()
    return [outcome for outcome in indexed_outcomes if outcome is not None]


def _label_single_record(
    client: BedrockRuntimeClient,
    model: ModelDefinition,
    run_id: str,
    record: Study2InputRecord,
    max_tokens: int,
) -> PredictionRecord | FailureRecord:
    try:
        prediction, usage = label_record(client, model, record, max_tokens)
        token_usage = map_bedrock_usage_to_token_usage(usage)
        return build_prediction_record(run_id, model, record, prediction, token_usage)
    except Exception as error:
        return build_failure_record(run_id, model, record, error)


def _flatten_and_validate_failures(
    batches: list[tuple[str, list[FailureRecord]]],
    run_id: str,
    model_folder: str,
    model_id: str,
    known_post_ids: frozenset[str],
) -> tuple[FailureRecord, ...]:
    failures: list[FailureRecord] = []
    for _, rows in batches:
        for record in rows:
            validate_failure_record_identity(
                record,
                run_id,
                model_folder,
                model_id,
                known_post_ids,
            )
            failures.append(record)
    return tuple(failures)


if __name__ == "__main__":
    main()
