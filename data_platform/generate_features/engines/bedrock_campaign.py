"""Bedrock S3 campaign writer for mixed-engine Reddit LLM features.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.generate_features.engines.bedrock_campaign import BEDROCK_CAMPAIGN_MAX_CONCURRENCY; \\
        print(BEDROCK_CAMPAIGN_MAX_CONCURRENCY)"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_platform.generate_features.campaign_engine_map import BEDROCK_ENGINE_TYPE
from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.engines.bedrock_engine import (
    create_bedrock_runtime_client,
    label_tasks_collecting_failures,
)
from data_platform.generate_features.engines.openai_engine import (
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    OpenAIBatchEngine,
    create_openai_client,
)
from data_platform.generate_features.generate_features import (
    _append_spilled_rows,
    _campaign_local_run_dir,
    _chunks,
    _label_campaign_chunk,
    _load_or_create_manifest,
    _load_spilled_rows,
    _ordered_campaign_input,
    _smoke_rows_by_id,
    _spill_path,
)
from data_platform.generate_features.models import (
    CampaignRunConfig,
    FeatureRunConfig,
    FeatureSpec,
    LabelTask,
)
from data_platform.generate_features.s3_feature_batches import (
    adopt_unrecorded_batch,
    attach_row_metadata,
    consolidate_final,
    labeled_ids,
    write_batch,
)
from data_platform.generate_features.s3_feature_campaign import (
    ActiveStateMirror,
    CampaignObjectStore,
    FeaturePaths,
    append_errors,
    delete_active_bedrock_state,
    delete_active_state,
    load_active_bedrock_state,
    read_failed_ids,
    run_id_for_feature,
    save_active_bedrock_state,
    save_manifest,
)
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO, DEFAULT_LLM_MODEL
from lib.timestamp_utils import get_current_timestamp

BEDROCK_CAMPAIGN_MAX_CONCURRENCY = 8
BEDROCK_JOB_STATE_RUNNING = "running"
BEDROCK_JOB_STATE_WRITING = "writing"
BEDROCK_JOB_STATE_TERMINAL = "terminal"
CONTENT_FILTER_REASON = "bedrock_content_filter"
BEDROCK_REQUEST_ID_PREFIX = "bedrock-"
BEDROCK_ATTEMPT_COUNT = 1


def run_bedrock_campaign_feature(
    records: Any,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    run_config: FeatureRunConfig,
    paths: FeaturePaths,
    engine_type: str,
) -> FeaturePaths:
    """Label one Bedrock-mapped campaign feature into immutable S3 batch objects.

    Content-filter ids are recorded, then retried through OpenAI Batch in this
    same call. Other Bedrock failures stay failed.

    Parameters
    ----------
    records
        Preprocessed rows with ``source_record_id`` and ``text``.
    spec
        Feature spec whose prompt and schema Bedrock uses.
    campaign
        Campaign identity, including batch size.
    run_config
        OpenAI retry settings. Bedrock parts always use eight threads.
    paths
        S3 prefix for this feature. Must not default a Reddit run to Bluesky.
    engine_type
        Must be ``bedrock`` and is stored on the manifest.

    Returns
    -------
    FeaturePaths
        The same prefix, after parts, retries, and optional final file.
    """
    store = CampaignObjectStore(paths.bucket)
    run_id = run_id_for_feature(campaign.campaign_id, spec.name)
    ordered_ids, texts = _ordered_campaign_input(records)
    manifest, manifest_etag = _load_or_create_manifest(
        store,
        paths,
        campaign,
        spec,
        expected_row_count=len(ordered_ids),
        engine_type=engine_type,
    )
    if manifest.get("final_parquet"):
        return paths
    manifest_etag = _label_bedrock_parts(
        store, paths, manifest, manifest_etag, spec, campaign, ordered_ids, texts, run_id
    )
    manifest_etag = _retry_content_filters_with_openai(
        store, paths, manifest, manifest_etag, spec, campaign, texts, run_id, run_config
    )
    _consolidate_bedrock_final(store, paths, manifest, manifest_etag, spec, ordered_ids, run_id)
    return paths


def _label_bedrock_parts(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    ordered_ids: list[str],
    texts: dict[str, str],
    run_id: str,
) -> str:
    written_parts = {int(entry["part_index"]) for entry in manifest["batches"]}
    for part_index, chunk_ids in enumerate(_chunks(ordered_ids, campaign.batch_size)):
        if part_index in written_parts:
            _delete_active_bedrock_job_if_part_in(store, paths, written_parts)
            continue
        adopted = adopt_unrecorded_batch(
            store, paths, manifest, manifest_etag, part_index=part_index, run_id=run_id
        )
        if adopted is not None:
            manifest_etag = adopted.manifest_etag
            written_parts.add(part_index)
            _delete_active_bedrock_job_if_part_in(store, paths, {part_index})
            continue
        manifest_etag = _label_bedrock_part(
            store, paths, manifest, manifest_etag, spec, campaign, part_index, chunk_ids, texts, run_id
        )
    return manifest_etag


def _label_bedrock_part(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    part_index: int,
    chunk_ids: list[str],
    texts: dict[str, str],
    run_id: str,
) -> str:
    run_dir = _campaign_local_run_dir(paths)
    spill_path = _spill_path(run_dir, spec.name, part_index)
    rows_by_id = _load_spilled_rows(spill_path)
    job, job_etag = _load_or_start_bedrock_job(
        store, paths, part_index, chunk_ids, campaign.campaign_id, spec.name, rows_by_id
    )
    pending = [uri for uri in chunk_ids if uri not in rows_by_id]
    if pending:
        outcome = _label_pending_bedrock_tasks(spec, pending, texts)
        _record_bedrock_outcome(
            store, paths, spill_path, rows_by_id, outcome, chunk_ids, run_id, job["job_id"], part_index
        )
        _persist_bedrock_job(store, paths, job, job_etag, chunk_ids, rows_by_id)
    return _finish_bedrock_part(
        store, paths, manifest, manifest_etag, spec, run_id, part_index, chunk_ids, rows_by_id, spill_path
    )


def _delete_active_bedrock_job_if_part_in(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    recorded_parts: set[int],
) -> None:
    """Delete ``active_bedrock_job.json`` when its part is already durable.

    Loads the active Bedrock cursor and deletes it only if
    ``logical_batch_index`` is in ``recorded_parts``. A cursor for a later
    unrecorded part is left in place so resume of that part can keep the job.

    Parameters
    ----------
    store
        Campaign object store for this feature prefix.
    paths
        Feature prefix that holds ``active_bedrock_job.json``.
    recorded_parts
        Part indexes already in the manifest, or the single part just adopted.
    """
    remote, _etag = load_active_bedrock_state(store, paths)
    if remote is None:
        return
    if int(remote["logical_batch_index"]) in recorded_parts:
        delete_active_bedrock_state(store, paths)


def _label_pending_bedrock_tasks(
    spec: FeatureSpec,
    pending: list[str],
    texts: dict[str, str],
) -> Any:
    tasks = [LabelTask(uri=uri, text=texts[uri]) for uri in pending]
    return label_tasks_collecting_failures(
        create_bedrock_runtime_client(),
        DEFAULT_BEDROCK_NOVA_MICRO,
        spec,
        tasks,
        BEDROCK_CAMPAIGN_MAX_CONCURRENCY,
        get_current_timestamp(),
    )


def _record_bedrock_outcome(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    spill_path: Path,
    rows_by_id: dict[str, dict],
    outcome: Any,
    chunk_ids: list[str],
    run_id: str,
    job_id: str,
    part_index: int,
) -> None:
    if outcome.rows:
        with_metadata = attach_row_metadata(
            outcome.rows,
            run_id=run_id,
            batch_id=job_id,
            request_ids=_bedrock_request_ids(chunk_ids),
            attempt_count=BEDROCK_ATTEMPT_COUNT,
        )
        _append_spilled_rows(spill_path, with_metadata)
        rows_by_id.update({row["source_record_id"]: row for row in with_metadata})
    _append_bedrock_failures(store, paths, outcome, run_id, part_index)


def _bedrock_request_ids(chunk_ids: list[str]) -> dict[str, str]:
    return {
        uri: f"{BEDROCK_REQUEST_ID_PREFIX}{index:05d}"
        for index, uri in enumerate(chunk_ids)
    }


def _append_bedrock_failures(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    outcome: Any,
    run_id: str,
    part_index: int,
) -> None:
    filter_records = [
        _content_filter_error_record(failure, run_id, part_index)
        for failure in outcome.content_filter_failures
    ]
    other_records = [
        _other_bedrock_error_record(failure, run_id, part_index)
        for failure in outcome.other_failures
    ]
    append_errors(store, paths, filter_records + other_records)


def _content_filter_error_record(
    failure: RecordLabelFailure, run_id: str, part_index: int
) -> dict[str, Any]:
    return {
        "source_record_id": failure.source_record_id,
        "reason": CONTENT_FILTER_REASON,
        "engine_type": BEDROCK_ENGINE_TYPE,
        "detail": failure.error,
        "recorded_at": get_current_timestamp(),
        "run_id": run_id,
        "part_index": part_index,
        "error": failure.error,
        "attempts": failure.attempts,
    }


def _other_bedrock_error_record(
    failure: RecordLabelFailure, run_id: str, part_index: int
) -> dict[str, Any]:
    return {
        "ts": get_current_timestamp(),
        "run_id": run_id,
        "part_index": part_index,
        "source_record_id": failure.source_record_id,
        "error": failure.error,
        "attempts": failure.attempts,
    }


def _finish_bedrock_part(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    run_id: str,
    part_index: int,
    chunk_ids: list[str],
    rows_by_id: dict[str, dict],
    spill_path: Path,
) -> str:
    rows = [rows_by_id[uri] for uri in chunk_ids if uri in rows_by_id]
    if rows:
        manifest_etag = _write_labeled_part(
            store, paths, manifest, manifest_etag, spec, run_id, part_index, rows
        )
    _delete_active_bedrock_job_if_part_in(store, paths, {part_index})
    spill_path.unlink(missing_ok=True)
    return manifest_etag


def _write_labeled_part(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    run_id: str,
    part_index: int,
    rows: list[dict],
) -> str:
    result = write_batch(
        store,
        paths,
        manifest,
        manifest_etag,
        part_index=part_index,
        rows=rows,
        spec=spec,
        run_id=run_id,
    )
    print(
        f"generate_features: {spec.name} part {part_index:05d} -> "
        f"{paths.uri(result.key)} ({result.row_count} rows, sha256 {result.sha256})"
    )
    return result.manifest_etag


def _load_or_start_bedrock_job(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    part_index: int,
    chunk_ids: list[str],
    campaign_id: str,
    feature: str,
    rows_by_id: dict[str, dict],
) -> tuple[dict[str, Any], str]:
    remote, etag = load_active_bedrock_state(store, paths)
    if remote is not None:
        _require_matching_bedrock_part(remote, part_index, paths)
        return remote, etag or ""
    job = _new_bedrock_job(part_index, chunk_ids, campaign_id, feature, rows_by_id)
    return job, save_active_bedrock_state(store, paths, job, None)


def _require_matching_bedrock_part(
    remote: dict[str, Any], part_index: int, paths: FeaturePaths
) -> None:
    if int(remote["logical_batch_index"]) != part_index:
        raise ValueError(
            f"active Bedrock job at {paths.uri(paths.active_bedrock_state_key)} "
            f"is for part {remote['logical_batch_index']}, expected {part_index}"
        )


def _new_bedrock_job(
    part_index: int,
    chunk_ids: list[str],
    campaign_id: str,
    feature: str,
    rows_by_id: dict[str, dict],
) -> dict[str, Any]:
    completed = [uri for uri in chunk_ids if uri in rows_by_id]
    pending = [uri for uri in chunk_ids if uri not in rows_by_id]
    return {
        "logical_batch_index": part_index,
        "pending_source_record_ids": pending,
        "completed_source_record_ids": completed,
        "state": BEDROCK_JOB_STATE_RUNNING,
        "job_id": _bedrock_job_id(campaign_id, feature, part_index),
        "campaign_id": campaign_id,
    }


def _bedrock_job_id(campaign_id: str, feature: str, part_index: int) -> str:
    return f"bedrock-{campaign_id}-{feature}-part-{part_index:05d}"


def _persist_bedrock_job(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    job: dict[str, Any],
    job_etag: str,
    chunk_ids: list[str],
    rows_by_id: dict[str, dict],
) -> tuple[dict[str, Any], str]:
    updated = {
        **job,
        "pending_source_record_ids": [uri for uri in chunk_ids if uri not in rows_by_id],
        "completed_source_record_ids": [uri for uri in chunk_ids if uri in rows_by_id],
        "state": BEDROCK_JOB_STATE_WRITING,
    }
    return updated, save_active_bedrock_state(store, paths, updated, job_etag)


def _retry_content_filters_with_openai(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    texts: dict[str, str],
    run_id: str,
    run_config: FeatureRunConfig,
) -> str:
    retry_ids = _pending_content_filter_ids(store, paths, labeled_ids(store, manifest))
    if not retry_ids:
        return manifest_etag
    engine, mirror, run_dir = _openai_retry_engine(store, paths, spec, campaign, run_config)
    prelabeled = _smoke_rows_by_id(store, paths, spec, run_id)
    before_parts = {int(entry["part_index"]) for entry in manifest["batches"]}
    manifest_etag = _write_openai_retry_parts(
        engine,
        mirror,
        store,
        paths,
        manifest,
        manifest_etag,
        spec,
        campaign,
        texts,
        run_id,
        run_dir,
        retry_ids,
        prelabeled,
    )
    return _save_openai_retry_metadata(store, paths, manifest, manifest_etag, retry_ids, before_parts)


def _openai_retry_engine(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    run_config: FeatureRunConfig,
) -> tuple[OpenAIBatchEngine, ActiveStateMirror, Path]:
    run_dir = _campaign_local_run_dir(paths)
    mirror = ActiveStateMirror(
        store, paths, run_dir=run_dir, feature_name=spec.name, campaign_id=campaign.campaign_id
    )
    engine = OpenAIBatchEngine(
        spec, run_config, create_openai_client(), DEFAULT_OPENAI_BATCH_ENGINE_CONFIG, mirror.sleep
    )
    return engine, mirror, run_dir


def _write_openai_retry_parts(
    engine: OpenAIBatchEngine,
    mirror: ActiveStateMirror,
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    texts: dict[str, str],
    run_id: str,
    run_dir: Path,
    retry_ids: list[str],
    prelabeled: dict[str, dict],
) -> str:
    remaining = list(retry_ids)
    while remaining:
        part_index = _next_part_index(manifest)
        adopted = adopt_unrecorded_batch(
            store, paths, manifest, manifest_etag, part_index=part_index, run_id=run_id
        )
        if adopted is not None:
            manifest_etag = adopted.manifest_etag
            labeled = labeled_ids(store, manifest)
            remaining = [uri for uri in remaining if uri not in labeled]
            continue
        chunk_ids = remaining[: campaign.batch_size]
        remaining = remaining[campaign.batch_size :]
        manifest_etag = _label_one_openai_retry_chunk(
            engine,
            mirror,
            store,
            paths,
            manifest,
            manifest_etag,
            spec,
            texts,
            run_id,
            run_dir,
            part_index,
            chunk_ids,
            prelabeled,
        )
    return manifest_etag


def _label_one_openai_retry_chunk(
    engine: OpenAIBatchEngine,
    mirror: ActiveStateMirror,
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    texts: dict[str, str],
    run_id: str,
    run_dir: Path,
    part_index: int,
    chunk_ids: list[str],
    prelabeled: dict[str, dict],
) -> str:
    manifest_etag = _label_campaign_chunk(
        engine,
        mirror,
        store,
        paths,
        manifest,
        manifest_etag,
        spec=spec,
        run_id=run_id,
        run_dir=run_dir,
        part_index=part_index,
        chunk_ids=chunk_ids,
        texts=texts,
        prelabeled=prelabeled,
    )
    delete_active_state(store, paths)
    return manifest_etag


def _pending_content_filter_ids(
    store: CampaignObjectStore, paths: FeaturePaths, already_labeled: set[str]
) -> list[str]:
    pending: list[str] = []
    seen: set[str] = set()
    for record in _error_records(store, paths):
        uri = str(record.get("source_record_id", ""))
        if record.get("reason") != CONTENT_FILTER_REASON or uri in already_labeled or uri in seen:
            continue
        seen.add(uri)
        pending.append(uri)
    return pending


def _error_records(store: CampaignObjectStore, paths: FeaturePaths) -> list[dict[str, Any]]:
    stored = store.get(paths.errors_key)
    if stored is None:
        return []
    return [json.loads(line) for line in stored.body.decode("utf-8").splitlines() if line]


def _next_part_index(manifest: dict[str, Any]) -> int:
    if not manifest["batches"]:
        return 0
    return max(int(entry["part_index"]) for entry in manifest["batches"]) + 1


def _save_openai_retry_metadata(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    retry_ids: list[str],
    before_parts: set[int],
) -> str:
    provider_batch_ids: list[str] = []
    for entry in manifest["batches"]:
        if int(entry["part_index"]) in before_parts:
            continue
        provider_batch_ids.extend(str(batch_id) for batch_id in entry["provider_batch_ids"])
    manifest["openai_content_filter_retry"] = {
        "count": len(retry_ids),
        "model_id": DEFAULT_LLM_MODEL,
        "provider_batch_ids": provider_batch_ids,
    }
    return save_manifest(store, paths, manifest, manifest_etag)


def _consolidate_bedrock_final(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    ordered_ids: list[str],
    run_id: str,
) -> None:
    final_etag = consolidate_final(
        store,
        paths,
        manifest,
        manifest_etag,
        expected_ids=ordered_ids,
        failed_ids=read_failed_ids(store, paths),
        spec=spec,
        run_id=run_id,
    )
    if final_etag is None:
        return
    final = manifest["final_parquet"]
    print(
        f"generate_features: {spec.name} -> {paths.uri(paths.final_key)} "
        f"({final['row_count']} rows, {final['failed_row_count']} permanently failed ids excluded)"
    )
