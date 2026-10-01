"""Resumable per-model Bedrock inference for Study 2 zero-shot runs.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from data_platform.generate_features.engines.bedrock_engine import (
    BedrockRuntimeClient,
    create_bedrock_runtime_client,
)
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import DEFAULT_S3_REGION

from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import EXPERIMENT_S3_BUCKET
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    FailureRecord,
    ModelRunManifest,
    PredictionRecord,
    Study2InputRecord,
    validate_failure_record_identity,
    validate_model_run_manifest_identity,
    validate_prediction_record_identity,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    build_failures_prefix,
    build_manifests_prefix,
    build_predictions_prefix,
    load_json_objects_under_prefix,
    load_jsonl_records_under_prefix,
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
