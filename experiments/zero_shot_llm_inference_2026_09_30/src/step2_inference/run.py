"""Resumable per-model Bedrock inference for Study 2 zero-shot runs.

The default ``--max-tokens`` is 256 because the Bedrock engine's built-in
default of 32 tokens is often too small for a JSON object with both
``is_remove`` and ``p_remove``.

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

from experiments.zero_shot_llm_inference_2026_09_30.shared.config import (
    ZERO_SHOT_VARIANT,
    Study2InferenceVariant,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    get_model_definition_by_folder,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.llm import PromptFormatter, label_record
from experiments.zero_shot_llm_inference_2026_09_30.shared.prompts import (
    format_baseline_zero_shot_keep_remove_prompt,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    FAILURE_WRAPPER_CALL_COUNT,
    FailureRecord,
    InputManifest,
    ModelDefinition,
    ModelRunManifest,
    ModelRunManifestStatus,
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
DEFAULT_BATCH_SIZE = 64
DEFAULT_MAX_CONCURRENCY = 8
DEFAULT_MAX_TOKENS = 256


def run_inference_cli(
    variant: Study2InferenceVariant,
    prompt_formatter: PromptFormatter,
) -> None:
    """Parse CLI arguments and run one model folder for ``variant``."""
    args = _parse_args()
    model = validate_inference_arguments(
        args.run_id,
        args.model,
        args.limit,
        args.batch_size,
        args.max_concurrency,
        args.max_tokens,
        variant,
    )
    apply_lab_aws_credentials_when_unset()
    store = CampaignObjectStore(variant.s3_bucket, region_name=DEFAULT_S3_REGION)
    run_plan = _build_inference_run_plan(store, args.run_id, model, args.limit, variant)
    run_state = _run_state_for_plan(
        store,
        variant,
        prompt_formatter,
        args.run_id,
        model,
        run_plan,
        args.batch_size,
        args.max_concurrency,
        args.max_tokens,
    )
    _write_model_run_from_state(
        store,
        variant,
        args.run_id,
        model,
        args.limit,
        args.batch_size,
        args.max_tokens,
        run_plan,
        run_state,
    )


def run_model_inference(
    store: CampaignObjectStore,
    client: BedrockRuntimeClient,
    run_id: str,
    model_folder: str,
    limit: int | None,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
    variant: Study2InferenceVariant,
    prompt_formatter: PromptFormatter,
) -> None:
    """Execute one resumable inference pass for a single model folder.

    Raises
    ------
    ValueError
        When prepared input, resume state, or CLI configuration is invalid.
    FileExistsError
        When an immutable write collides with an existing object.
    """
    model = validate_inference_arguments(
        run_id,
        model_folder,
        limit,
        batch_size,
        max_concurrency,
        max_tokens,
        variant,
    )
    run_plan = _build_inference_run_plan(store, run_id, model, limit, variant)
    run_state = _run_pending_record_batches(
        store,
        client,
        variant,
        prompt_formatter,
        run_id,
        model,
        run_plan,
        batch_size,
        max_concurrency,
        max_tokens,
    )
    manifest = build_model_run_manifest(
        run_plan.input_manifest,
        model,
        run_id,
        limit,
        batch_size,
        max_tokens,
        run_plan.requested_records,
        tuple(run_state.predictions),
        tuple(run_state.failures),
        tuple(run_state.prediction_keys),
        tuple(run_state.failure_keys),
        variant,
    )
    write_model_run_manifest(store, run_id, model.folder_name, manifest, variant)


def main() -> None:
    """Parse CLI arguments and run one zero-shot model inference task."""
    run_inference_cli(ZERO_SHOT_VARIANT, format_baseline_zero_shot_keep_remove_prompt)


def _run_state_for_plan(
    store: CampaignObjectStore,
    variant: Study2InferenceVariant,
    prompt_formatter: PromptFormatter,
    run_id: str,
    model: ModelDefinition,
    run_plan: InferenceRunPlan,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
) -> InferenceRunState:
    if not run_plan.pending_records:
        return _inference_run_state_from_artifacts(run_plan.artifacts)
    client = create_bedrock_runtime_client()
    return _run_pending_record_batches(
        store,
        client,
        variant,
        prompt_formatter,
        run_id,
        model,
        run_plan,
        batch_size,
        max_concurrency,
        max_tokens,
    )


def _inference_run_state_from_artifacts(artifacts: LoadedRunArtifacts) -> InferenceRunState:
    return InferenceRunState(
        prediction_keys=artifacts.prediction_object_keys,
        predictions=artifacts.predictions,
        failure_keys=artifacts.failure_object_keys,
        failures=artifacts.failures,
    )


def _write_model_run_from_state(
    store: CampaignObjectStore,
    variant: Study2InferenceVariant,
    run_id: str,
    model: ModelDefinition,
    limit: int | None,
    batch_size: int,
    max_tokens: int,
    run_plan: InferenceRunPlan,
    run_state: InferenceRunState,
) -> None:
    manifest = build_model_run_manifest(
        run_plan.input_manifest,
        model,
        run_id,
        limit,
        batch_size,
        max_tokens,
        run_plan.requested_records,
        tuple(run_state.predictions),
        tuple(run_state.failures),
        tuple(run_state.prediction_keys),
        tuple(run_state.failure_keys),
        variant,
    )
    write_model_run_manifest(store, run_id, model.folder_name, manifest, variant)
    print_model_run_completion_summary(manifest)


def format_model_run_completion_line(manifest: ModelRunManifest) -> str:
    """Return the single-line CLI summary for one written model run manifest."""
    return (
        f"run_id={manifest.run_id} model_folder={manifest.model_folder} "
        f"model_id={manifest.model_id} expected={manifest.requested_record_count} "
        f"unique_valid_predictions={manifest.completed_prediction_count} "
        f"unresolved_failures={manifest.unresolved_failure_count}"
    )


def print_model_run_completion_summary(manifest: ModelRunManifest) -> None:
    """Print the completion summary and exit nonzero when the run is incomplete."""
    print(format_model_run_completion_line(manifest))
    if manifest.status is not ModelRunManifestStatus.COMPLETE:
        raise SystemExit(1)


def validate_inference_arguments(
    run_id: str,
    model_folder: str,
    limit: int | None,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
    variant: Study2InferenceVariant,
) -> ModelDefinition:
    """Validate CLI configuration before any AWS client is constructed.

    Parameters
    ----------
    variant
        Active experiment. The model must be in ``variant.model_folders``.

    Raises
    ------
    ValueError
        When arguments are unsafe, the folder is unknown, or the active
        experiment does not enable that model.
    """
    validate_path_segment(run_id)
    validate_positive_optional_limit(limit)
    _validate_positive_integer(batch_size, "batch_size")
    _validate_positive_integer(max_concurrency, "max_concurrency")
    _validate_positive_integer(max_tokens, "max_tokens")
    model = get_model_definition_by_folder(model_folder)
    _require_model_enabled(model, variant)
    return model


def _require_model_enabled(model: ModelDefinition, variant: Study2InferenceVariant) -> None:
    if model.folder_name not in variant.model_folders:
        raise ValueError(f"model folder is not enabled for this experiment: {model.folder_name}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run resumable zero-shot Bedrock inference for one Study 2 model.",
    )
    parser.add_argument("--run-id", required=True, help="Safe run identifier segment")
    parser.add_argument(
        "--model",
        required=True,
        help="Model folder enabled for the active experiment",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional positive record limit for bounded smoke runs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Positive number of pending records per inference batch",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=DEFAULT_MAX_CONCURRENCY,
        help="Positive maximum concurrent Bedrock calls within one batch",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Positive maximum output tokens forwarded to Converse",
    )
    return parser.parse_args()


def _chunk_records(
    records: tuple[Study2InputRecord, ...],
    batch_size: int,
) -> list[tuple[Study2InputRecord, ...]]:
    batches: list[tuple[Study2InputRecord, ...]] = []
    for start in range(0, len(records), batch_size):
        batches.append(records[start : start + batch_size])
    return batches


def _validate_positive_integer(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


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
class InferenceRunPlan:
    """Validated prepared input and pending work for one model run."""

    input_manifest: InputManifest
    requested_records: tuple[Study2InputRecord, ...]
    pending_records: tuple[Study2InputRecord, ...]
    artifacts: LoadedRunArtifacts


@dataclass(frozen=True)
class InferenceRunState:
    """Accumulated predictions, failures, and object keys for one pass."""

    prediction_keys: tuple[str, ...]
    predictions: tuple[PredictionRecord, ...]
    failure_keys: tuple[str, ...]
    failures: tuple[FailureRecord, ...]


@dataclass(frozen=True)
class LoadedRunArtifacts:
    """Immutable artifacts already stored for one model run."""

    manifests: tuple[ModelRunManifest, ...]
    prediction_object_keys: tuple[str, ...]
    predictions: tuple[PredictionRecord, ...]
    failure_object_keys: tuple[str, ...]
    failures: tuple[FailureRecord, ...]


def _build_inference_run_plan(
    store: CampaignObjectStore,
    run_id: str,
    model: ModelDefinition,
    limit: int | None,
    variant: Study2InferenceVariant,
) -> InferenceRunPlan:
    input_manifest, prepared_records = load_verified_prepared_input(store, variant)
    requested_records = select_requested_records(prepared_records, limit)
    prepared_post_ids = frozenset(record.post_id for record in prepared_records)
    artifacts = load_existing_run_artifacts(
        store,
        run_id,
        model.folder_name,
        model.model_id,
        prepared_post_ids,
        variant,
    )
    assert_configured_limit_matches_manifests(limit, artifacts.manifests)
    _reject_input_identity_mismatch(artifacts.manifests, input_manifest)
    requested_post_ids = frozenset(record.post_id for record in requested_records)
    completed_ids = completed_post_ids_for_requested_set(
        artifacts.predictions,
        requested_post_ids,
    )
    pending_records = select_pending_records(requested_records, completed_ids)
    return InferenceRunPlan(
        input_manifest=input_manifest,
        requested_records=requested_records,
        pending_records=pending_records,
        artifacts=artifacts,
    )


def _run_pending_record_batches(
    store: CampaignObjectStore,
    client: BedrockRuntimeClient,
    variant: Study2InferenceVariant,
    prompt_formatter: PromptFormatter,
    run_id: str,
    model: ModelDefinition,
    run_plan: InferenceRunPlan,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
) -> InferenceRunState:
    prediction_keys = list(run_plan.artifacts.prediction_object_keys)
    failure_keys = list(run_plan.artifacts.failure_object_keys)
    all_predictions = list(run_plan.artifacts.predictions)
    all_failures = list(run_plan.artifacts.failures)
    for batch in _chunk_records(run_plan.pending_records, batch_size):
        batch_predictions, batch_failures = run_ordered_inference_batch(
            client,
            model,
            variant,
            prompt_formatter,
            run_id,
            batch,
            max_concurrency,
            max_tokens,
        )
        prediction_key = write_prediction_batch_if_nonempty(
            store,
            run_id,
            model.folder_name,
            batch_predictions,
            variant,
        )
        failure_key = write_failure_batch_if_nonempty(
            store,
            run_id,
            model.folder_name,
            batch_failures,
            variant,
        )
        if prediction_key is not None:
            prediction_keys.append(prediction_key)
            all_predictions.extend(batch_predictions)
        if failure_key is not None:
            failure_keys.append(failure_key)
            all_failures.extend(batch_failures)
    return InferenceRunState(
        prediction_keys=tuple(prediction_keys),
        predictions=tuple(all_predictions),
        failure_keys=tuple(failure_keys),
        failures=tuple(all_failures),
    )


def load_existing_run_artifacts(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    model_id: str,
    known_post_ids: frozenset[str],
    variant: Study2InferenceVariant | None = None,
) -> LoadedRunArtifacts:
    """Load manifests, predictions, and failures for one model folder.

    Raises
    ------
    ValueError
        When stored rows are invalid or conflict with run identity.
    """
    known_ids = known_post_ids
    manifests = _load_manifest_objects(store, run_id, model_folder, model_id, variant)
    prediction_batches = load_jsonl_records_under_prefix(
        store,
        build_predictions_prefix(run_id, model_folder, variant),
        PredictionRecord,
    )
    failure_batches = load_jsonl_records_under_prefix(
        store,
        build_failures_prefix(run_id, model_folder, variant),
        FailureRecord,
    )
    predictions = _flatten_and_validate_predictions(
        prediction_batches,
        run_id,
        model_folder,
        model_id,
        known_ids,
        variant,
    )
    failures = _flatten_and_validate_failures(
        failure_batches,
        run_id,
        model_folder,
        model_id,
        known_ids,
        variant,
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
    variant: Study2InferenceVariant,
) -> PredictionRecord:
    """Build one prediction row for immutable storage."""
    return PredictionRecord(
        schema_version=variant.prediction_schema_version,
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
    variant: Study2InferenceVariant,
) -> FailureRecord:
    """Build one failure row for immutable storage."""
    message = str(error).strip()
    if not message:
        message = error.__class__.__name__
    return FailureRecord(
        schema_version=variant.failure_schema_version,
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
    variant: Study2InferenceVariant,
) -> str | None:
    """Write one immutable prediction JSONL batch when rows are present.

    Raises
    ------
    FileExistsError
        When the target batch key already exists.
    """
    if not records:
        return None
    prefix = build_predictions_prefix(run_id, model_folder, variant)
    sequence = next_sequence_for_prefix(
        store,
        prefix,
        _BATCH_OBJECT_PREFIX,
        _JSONL_OBJECT_SUFFIX,
    )
    key = build_prediction_batch_key(run_id, model_folder, sequence, variant)
    put_immutable_object(store, key, serialize_jsonl_models(records))
    return key


def build_model_run_manifest(
    input_manifest: InputManifest,
    model: ModelDefinition,
    run_id: str,
    configured_limit: int | None,
    batch_size: int,
    max_tokens: int,
    requested_records: tuple[Study2InputRecord, ...],
    predictions: tuple[PredictionRecord, ...],
    failures: tuple[FailureRecord, ...],
    prediction_object_keys: tuple[str, ...],
    failure_object_keys: tuple[str, ...],
    variant: Study2InferenceVariant,
) -> ModelRunManifest:
    """Summarize the observed run state for one immutable manifest."""
    requested_ids = frozenset(record.post_id for record in requested_records)
    completed = completed_post_ids_for_requested_set(predictions, requested_ids)
    unresolved = unresolved_failure_post_ids(failures, predictions, requested_ids)
    status = _manifest_status_for_counts(
        len(requested_records),
        len(completed),
        len(unresolved),
    )
    return ModelRunManifest(
        schema_version=variant.model_run_schema_version,
        run_id=run_id,
        model_display_name=model.display_name,
        model_folder=model.folder_name,
        model_id=model.model_id,
        prepared_input_records_key=input_manifest.records_s3_key,
        prepared_input_records_sha256=input_manifest.records_sha256,
        configured_batch_size=batch_size,
        configured_max_tokens=max_tokens,
        configured_limit=configured_limit,
        requested_record_count=len(requested_records),
        completed_prediction_count=len(completed),
        unresolved_failure_count=len(unresolved),
        prediction_object_keys=prediction_object_keys,
        failure_object_keys=failure_object_keys,
        status=status,
        experiment_name=variant.experiment_name,
        prompt_name=variant.prompt_name,
        prompt_sha256=variant.prompt_sha256,
    )


def write_model_run_manifest(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    manifest: ModelRunManifest,
    variant: Study2InferenceVariant,
) -> str:
    """Write one immutable manifest describing the current run state.

    Raises
    ------
    FileExistsError
        When the target manifest key already exists.
    """
    prefix = build_manifests_prefix(run_id, model_folder, variant)
    sequence = next_sequence_for_prefix(
        store,
        prefix,
        _MANIFEST_OBJECT_PREFIX,
        _JSON_OBJECT_SUFFIX,
    )
    key = build_manifest_key(run_id, model_folder, sequence, variant)
    body = serialize_json_document(manifest.model_dump(mode="json"))
    put_immutable_object(store, key, body)
    return key


def write_failure_batch_if_nonempty(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    records: list[FailureRecord],
    variant: Study2InferenceVariant,
) -> str | None:
    """Write one immutable failure JSONL batch when rows are present.

    Raises
    ------
    FileExistsError
        When the target batch key already exists.
    """
    if not records:
        return None
    prefix = build_failures_prefix(run_id, model_folder, variant)
    sequence = next_sequence_for_prefix(
        store,
        prefix,
        _BATCH_OBJECT_PREFIX,
        _JSONL_OBJECT_SUFFIX,
    )
    key = build_failure_batch_key(run_id, model_folder, sequence, variant)
    put_immutable_object(store, key, serialize_jsonl_models(records))
    return key


def run_ordered_inference_batch(
    client: BedrockRuntimeClient,
    model: ModelDefinition,
    variant: Study2InferenceVariant,
    prompt_formatter: PromptFormatter,
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
        variant,
        prompt_formatter,
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


def _reject_input_identity_mismatch(
    manifests: tuple[ModelRunManifest, ...],
    input_manifest: InputManifest,
) -> None:
    for manifest in manifests:
        if manifest.prepared_input_records_sha256 != input_manifest.records_sha256:
            raise ValueError("prepared input digest mismatch with existing manifest")
        if manifest.prepared_input_records_key != input_manifest.records_s3_key:
            raise ValueError("prepared input key mismatch with existing manifest")


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
    variant: Study2InferenceVariant | None,
) -> tuple[ModelRunManifest, ...]:
    prefix = build_manifests_prefix(run_id, model_folder, variant)
    loaded = load_json_objects_under_prefix(store, prefix, ".json", ModelRunManifest)
    manifests: list[ModelRunManifest] = []
    for _, manifest in loaded:
        validate_model_run_manifest_identity(
            manifest,
            run_id,
            model_folder,
            model_id,
            variant,
        )
        manifests.append(manifest)
    return tuple(manifests)


def _flatten_and_validate_predictions(
    batches: list[tuple[str, list[PredictionRecord]]],
    run_id: str,
    model_folder: str,
    model_id: str,
    known_post_ids: frozenset[str],
    variant: Study2InferenceVariant | None,
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
                variant,
            )
            if record.post_id in seen_post_ids:
                raise ValueError(f"duplicate prediction post_id: {record.post_id}")
            seen_post_ids.add(record.post_id)
            predictions.append(record)
    return tuple(predictions)


def _manifest_status_for_counts(
    requested_count: int,
    completed_count: int,
    unresolved_failure_count: int,
) -> ModelRunManifestStatus:
    if completed_count == requested_count and unresolved_failure_count == 0:
        return ModelRunManifestStatus.COMPLETE
    return ModelRunManifestStatus.INCOMPLETE


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
    variant: Study2InferenceVariant,
    prompt_formatter: PromptFormatter,
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
                variant,
                prompt_formatter,
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
    variant: Study2InferenceVariant,
    prompt_formatter: PromptFormatter,
    run_id: str,
    record: Study2InputRecord,
    max_tokens: int,
) -> PredictionRecord | FailureRecord:
    try:
        prediction, usage = label_record(
            client,
            model,
            record,
            max_tokens,
            prompt_formatter,
        )
        token_usage = map_bedrock_usage_to_token_usage(usage)
        return build_prediction_record(
            run_id,
            model,
            record,
            prediction,
            token_usage,
            variant,
        )
    except Exception as error:
        return build_failure_record(run_id, model, record, error, variant)


def _flatten_and_validate_failures(
    batches: list[tuple[str, list[FailureRecord]]],
    run_id: str,
    model_folder: str,
    model_id: str,
    known_post_ids: frozenset[str],
    variant: Study2InferenceVariant | None,
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
                variant,
            )
            failures.append(record)
    return tuple(failures)


if __name__ == "__main__":
    main()
