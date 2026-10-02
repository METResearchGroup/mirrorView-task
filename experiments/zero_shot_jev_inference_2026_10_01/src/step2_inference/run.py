"""Resumable zero-shot Jev inference for one Study 2 run.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run --help
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

from experiments.zero_shot_jev_inference_2026_10_01.shared.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_WORKERS,
    INPUT_MANIFEST_KEY,
    INPUT_RECORDS_KEY,
    JEV_MODEL,
    S3_BUCKET,
)
from experiments.zero_shot_jev_inference_2026_10_01.shared.jev import (
    build_remove_request,
    to_prediction_record,
)
from experiments.zero_shot_jev_inference_2026_10_01.shared.schemas import (
    JEV_RUN_MANIFEST_SCHEMA_VERSION,
    JevRunManifest,
)
from experiments.zero_shot_jev_inference_2026_10_01.shared.storage import (
    build_failure_batch_key,
    build_failures_prefix,
    build_manifest_key,
    build_manifests_prefix,
    build_prediction_batch_key,
    build_predictions_prefix,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    FAILURE_SCHEMA_VERSION,
    FAILURE_WRAPPER_CALL_COUNT,
    FailureRecord,
    InputManifest,
    ModelRunManifestStatus,
    PredictionRecord,
    Study2InputRecord,
    validate_failure_record_identity,
    validate_prediction_record_identity,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    load_json_objects_under_prefix,
    load_jsonl_records_under_prefix,
    next_sequence_for_prefix,
    parse_study2_input_jsonl_bytes,
    put_immutable_object,
    serialize_json_document,
    serialize_jsonl_models,
    sha256_hex,
    validate_path_segment,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run import (
    completed_post_ids_for_requested_set,
    unresolved_failure_post_ids,
)
_BATCH_OBJECT_PREFIX = "batch-"
_JSONL_OBJECT_SUFFIX = ".jsonl"
_MANIFEST_OBJECT_PREFIX = "manifest-"
_JSON_OBJECT_SUFFIX = ".json"


@dataclass(frozen=True)
class PreparedRequest:
    """Validated input and the ordered records selected for this run."""

    manifest: InputManifest
    prepared_records: tuple[Study2InputRecord, ...]
    requested_records: tuple[Study2InputRecord, ...]


@dataclass(frozen=True)
class StoredRunState:
    """Objects already stored under the Jev run folder."""

    manifests: tuple[JevRunManifest, ...]
    prediction_keys: tuple[str, ...]
    predictions: tuple[PredictionRecord, ...]
    failure_keys: tuple[str, ...]
    failures: tuple[FailureRecord, ...]


@dataclass(frozen=True)
class WrittenCounts:
    """Rows created by the current process."""

    predictions: int
    failures: int


def run_inference(
    store: CampaignObjectStore,
    scorer: object,
    run_id: str,
    limit: int | None,
    batch_size: int,
    max_workers: int,
) -> JevRunManifest:
    """Score pending pairs for one run and write one new manifest.

    Parameters
    ----------
    store
        Object store for the experiment bucket.
    scorer
        Object with ``score(request) -> JevResult``.
    run_id
        Safe run identifier.
    limit
        Optional positive cap applied after the full input is validated.
    batch_size
        Maximum pending records scored before a write.
    max_workers
        Maximum worker threads sharing ``scorer``.

    Returns
    -------
    JevRunManifest
        Manifest written from the recounted run folder.

    Raises
    ------
    ValueError
        When the input, resume state, or options are invalid.
    FileExistsError
        When an immutable write collides. No manifest is written after that.
    """
    _validate_options(run_id, limit, batch_size, max_workers)
    prepared = _load_prepared_request(store, limit)
    state = _load_stored_run_state(store, run_id, prepared.prepared_records)
    _reject_option_mismatch(state.manifests, limit, batch_size, max_workers)
    pending = _pending_records(prepared.requested_records, state.predictions)
    written = _write_scored_batches(store, scorer, run_id, pending, batch_size, max_workers)
    manifest, recounted = _write_recounted_manifest(
        store,
        prepared,
        run_id,
        limit,
        batch_size,
        max_workers,
    )
    _print_summary(manifest, prepared.requested_records, state, recounted, written)
    return manifest


def main() -> None:
    """Parse arguments, then run one Jev process."""
    args = _parse_args()
    _exit_when_options_invalid(args.run_id, args.limit, args.batch_size, args.max_workers)
    apply_lab_aws_credentials_when_unset()
    store = CampaignObjectStore(S3_BUCKET)
    from shared.models.jev import build_jev_scorer

    scorer = build_jev_scorer()
    run_inference(store, scorer, args.run_id, args.limit, args.batch_size, args.max_workers)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run resumable zero-shot Jev inference.")
    parser.add_argument("--run-id", required=True, help="Safe run identifier segment")
    parser.add_argument("--limit", type=int, default=None, help="Positive record limit")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    return parser.parse_args()


def _exit_when_options_invalid(
    run_id: str,
    limit: int | None,
    batch_size: int,
    max_workers: int,
) -> None:
    try:
        _validate_options(run_id, limit, batch_size, max_workers)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error


def _validate_options(
    run_id: str,
    limit: int | None,
    batch_size: int,
    max_workers: int,
) -> None:
    validate_path_segment(run_id)
    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer when provided")
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    if max_workers <= 0:
        raise ValueError("max_workers must be a positive integer")


def _load_prepared_request(store: CampaignObjectStore, limit: int | None) -> PreparedRequest:
    manifest_bytes = _required_bytes(store, INPUT_MANIFEST_KEY)
    records_bytes = _required_bytes(store, INPUT_RECORDS_KEY)
    manifest = InputManifest.model_validate_json(manifest_bytes)
    if sha256_hex(records_bytes) != manifest.records_sha256:
        raise ValueError("prepared input records digest mismatch")
    records = tuple(parse_study2_input_jsonl_bytes(records_bytes))
    _reject_duplicate_post_ids(records)
    requested = records if limit is None else records[:limit]
    return PreparedRequest(manifest, records, requested)


def _required_bytes(store: CampaignObjectStore, key: str) -> bytes:
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(key)
    return stored.body


def _reject_duplicate_post_ids(records: tuple[Study2InputRecord, ...]) -> None:
    seen: set[str] = set()
    for record in records:
        if record.post_id in seen:
            raise ValueError(f"duplicate prepared post_id: {record.post_id}")
        seen.add(record.post_id)


def _load_stored_run_state(
    store: CampaignObjectStore,
    run_id: str,
    prepared_records: tuple[Study2InputRecord, ...],
) -> StoredRunState:
    known_ids = frozenset(record.post_id for record in prepared_records)
    manifests = _load_manifests(store, run_id)
    prediction_batches = load_jsonl_records_under_prefix(
        store,
        build_predictions_prefix(run_id),
        PredictionRecord,
    )
    failure_batches = load_jsonl_records_under_prefix(
        store,
        build_failures_prefix(run_id),
        FailureRecord,
    )
    predictions = _validated_predictions(prediction_batches, run_id, known_ids)
    failures = _validated_failures(failure_batches, run_id, known_ids)
    return StoredRunState(
        manifests,
        tuple(key for key, _ in prediction_batches),
        predictions,
        tuple(key for key, _ in failure_batches),
        failures,
    )


def _load_manifests(store: CampaignObjectStore, run_id: str) -> tuple[JevRunManifest, ...]:
    loaded = load_json_objects_under_prefix(
        store,
        build_manifests_prefix(run_id),
        _JSON_OBJECT_SUFFIX,
        JevRunManifest,
    )
    manifests: list[JevRunManifest] = []
    for _, manifest in loaded:
        _reject_manifest_identity(manifest, run_id)
        manifests.append(manifest)
    return tuple(manifests)


def _reject_manifest_identity(manifest: JevRunManifest, run_id: str) -> None:
    if manifest.run_id != run_id:
        raise ValueError("manifest run_id mismatch")
    if manifest.model_folder != JEV_MODEL.folder_name:
        raise ValueError("manifest model_folder mismatch")
    if manifest.model_id != JEV_MODEL.model_id:
        raise ValueError("manifest model_id mismatch")


def _validated_predictions(
    batches: list[tuple[str, list[PredictionRecord]]],
    run_id: str,
    known_ids: frozenset[str],
) -> tuple[PredictionRecord, ...]:
    rows: list[PredictionRecord] = []
    seen: set[str] = set()
    for _, batch in batches:
        for record in batch:
            validate_prediction_record_identity(
                record,
                run_id,
                JEV_MODEL.folder_name,
                JEV_MODEL.model_id,
                known_ids,
            )
            if record.post_id in seen:
                raise ValueError(f"duplicate prediction post_id: {record.post_id}")
            seen.add(record.post_id)
            rows.append(record)
    return tuple(rows)


def _validated_failures(
    batches: list[tuple[str, list[FailureRecord]]],
    run_id: str,
    known_ids: frozenset[str],
) -> tuple[FailureRecord, ...]:
    rows: list[FailureRecord] = []
    for _, batch in batches:
        for record in batch:
            validate_failure_record_identity(
                record,
                run_id,
                JEV_MODEL.folder_name,
                JEV_MODEL.model_id,
                known_ids,
            )
            rows.append(record)
    return tuple(rows)


def _reject_option_mismatch(
    manifests: tuple[JevRunManifest, ...],
    limit: int | None,
    batch_size: int,
    max_workers: int,
) -> None:
    if not manifests:
        return
    first = manifests[0]
    if first.configured_limit != limit:
        raise ValueError("configured limit mismatch with existing manifest")
    if first.configured_batch_size != batch_size:
        raise ValueError("configured batch size mismatch with existing manifest")
    if first.max_workers != max_workers:
        raise ValueError("configured max workers mismatch with existing manifest")


def _pending_records(
    requested: tuple[Study2InputRecord, ...],
    predictions: tuple[PredictionRecord, ...],
) -> tuple[Study2InputRecord, ...]:
    requested_ids = frozenset(record.post_id for record in requested)
    completed = completed_post_ids_for_requested_set(predictions, requested_ids)
    return tuple(record for record in requested if record.post_id not in completed)


def _write_scored_batches(
    store: CampaignObjectStore,
    scorer: object,
    run_id: str,
    pending: tuple[Study2InputRecord, ...],
    batch_size: int,
    max_workers: int,
) -> WrittenCounts:
    predictions_written = 0
    failures_written = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        predictions, failures = _score_batch_in_order(scorer, run_id, batch, max_workers)
        _put_jsonl_batch(
            store,
            run_id,
            predictions,
            build_predictions_prefix(run_id),
            build_prediction_batch_key,
        )
        _put_jsonl_batch(
            store,
            run_id,
            failures,
            build_failures_prefix(run_id),
            build_failure_batch_key,
        )
        predictions_written += len(predictions)
        failures_written += len(failures)
    return WrittenCounts(predictions_written, failures_written)


def _score_batch_in_order(
    scorer: object,
    run_id: str,
    records: tuple[Study2InputRecord, ...],
    max_workers: int,
) -> tuple[list[PredictionRecord], list[FailureRecord]]:
    ordered: list[PredictionRecord | FailureRecord | None] = [None] * len(records)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_score_one, scorer, run_id, record): index
            for index, record in enumerate(records)
        }
        for future, index in futures.items():
            ordered[index] = future.result()
    return _split_outcomes([row for row in ordered if row is not None])


def _score_one(
    scorer: object,
    run_id: str,
    record: Study2InputRecord,
) -> PredictionRecord | FailureRecord:
    try:
        result = scorer.score(build_remove_request(record))
        return to_prediction_record(run_id, record, result)
    except Exception as error:
        return _failure_from_exception(run_id, record, error)


def _failure_from_exception(
    run_id: str,
    record: Study2InputRecord,
    error: Exception,
) -> FailureRecord:
    message = _exception_message(error)
    return FailureRecord(
        schema_version=FAILURE_SCHEMA_VERSION,
        run_id=run_id,
        model_folder=JEV_MODEL.folder_name,
        model_id=JEV_MODEL.model_id,
        post_id=record.post_id,
        exception_type=error.__class__.__name__,
        error_message=message,
        wrapper_call_count=FAILURE_WRAPPER_CALL_COUNT,
    )


def _exception_message(error: Exception) -> str:
    try:
        message = str(error).strip()
    except Exception:
        message = ""
    return message or error.__class__.__name__


def _split_outcomes(
    rows: list[PredictionRecord | FailureRecord],
) -> tuple[list[PredictionRecord], list[FailureRecord]]:
    predictions = [row for row in rows if isinstance(row, PredictionRecord)]
    failures = [row for row in rows if isinstance(row, FailureRecord)]
    return predictions, failures


def _put_jsonl_batch(
    store: CampaignObjectStore,
    run_id: str,
    rows: list[PredictionRecord] | list[FailureRecord],
    prefix: str,
    key_for_sequence: Callable[[str, int], str],
) -> None:
    if not rows:
        return
    sequence = next_sequence_for_prefix(
        store,
        prefix,
        _BATCH_OBJECT_PREFIX,
        _JSONL_OBJECT_SUFFIX,
    )
    put_immutable_object(store, key_for_sequence(run_id, sequence), serialize_jsonl_models(rows))


def _write_recounted_manifest(
    store: CampaignObjectStore,
    prepared: PreparedRequest,
    run_id: str,
    limit: int | None,
    batch_size: int,
    max_workers: int,
) -> tuple[JevRunManifest, StoredRunState]:
    state = _load_stored_run_state(store, run_id, prepared.prepared_records)
    manifest = _manifest_from_state(prepared, state, run_id, limit, batch_size, max_workers)
    sequence = next_sequence_for_prefix(
        store,
        build_manifests_prefix(run_id),
        _MANIFEST_OBJECT_PREFIX,
        _JSON_OBJECT_SUFFIX,
    )
    body = serialize_json_document(manifest.model_dump(mode="json"))
    put_immutable_object(store, build_manifest_key(run_id, sequence), body)
    return manifest, state


def _manifest_from_state(
    prepared: PreparedRequest,
    state: StoredRunState,
    run_id: str,
    limit: int | None,
    batch_size: int,
    max_workers: int,
) -> JevRunManifest:
    requested_ids = frozenset(record.post_id for record in prepared.requested_records)
    completed = completed_post_ids_for_requested_set(state.predictions, requested_ids)
    unresolved = unresolved_failure_post_ids(state.failures, state.predictions, requested_ids)
    status = _status_for_counts(len(prepared.requested_records), len(completed), len(unresolved))
    return JevRunManifest(
        schema_version=JEV_RUN_MANIFEST_SCHEMA_VERSION,
        run_id=run_id,
        model_display_name=JEV_MODEL.display_name,
        model_folder=JEV_MODEL.folder_name,
        model_id=JEV_MODEL.model_id,
        prepared_input_records_key=INPUT_RECORDS_KEY,
        prepared_input_records_sha256=prepared.manifest.records_sha256,
        configured_batch_size=batch_size,
        max_workers=max_workers,
        configured_limit=limit,
        requested_record_count=len(prepared.requested_records),
        completed_prediction_count=len(completed),
        unresolved_failure_count=len(unresolved),
        prediction_object_keys=state.prediction_keys,
        failure_object_keys=state.failure_keys,
        status=status,
    )


def _status_for_counts(
    requested_count: int,
    completed_count: int,
    unresolved_count: int,
) -> ModelRunManifestStatus:
    if completed_count == requested_count and unresolved_count == 0:
        return ModelRunManifestStatus.COMPLETE
    return ModelRunManifestStatus.INCOMPLETE


def _print_summary(
    manifest: JevRunManifest,
    requested: tuple[Study2InputRecord, ...],
    state_before: StoredRunState,
    recounted: StoredRunState,
    written: WrittenCounts,
) -> None:
    requested_ids = frozenset(record.post_id for record in requested)
    skipped = len(completed_post_ids_for_requested_set(state_before.predictions, requested_ids))
    input_tokens = sum(row.usage.input_tokens for row in recounted.predictions)
    output_tokens = sum(row.usage.output_tokens for row in recounted.predictions)
    print(
        f"run_id={manifest.run_id} model_folder={manifest.model_folder} "
        f"model_id={manifest.model_id} expected={manifest.requested_record_count} "
        f"skipped={skipped} new_predictions={written.predictions} "
        f"new_failures={written.failures} "
        f"unique_valid_predictions={manifest.completed_prediction_count} "
        f"unresolved_failures={manifest.unresolved_failure_count} "
        f"input_tokens={input_tokens} output_tokens={output_tokens} "
        f"status={manifest.status.value}"
    )


if __name__ == "__main__":
    main()
