"""Resumable feature-generation orchestrator with batch execution engines."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pandas as pd

from data_platform.generate_features.engines import build_engine
from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.engines.openai_engine import (
    CUSTOM_ID_INDEX_WIDTH,
    CUSTOM_ID_PREFIX,
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    OpenAIBatchEngine,
    create_openai_client,
)
from data_platform.generate_features.metadata import (
    flush_metadata,
    init_feature_run_metadata,
    load_feature_run_metadata,
    mark_feature_completed,
    mark_feature_in_progress,
    set_sync_status_completed,
    update_batch_counts,
)
from data_platform.generate_features.models import (
    BatchRunStats,
    CampaignRunConfig,
    FeatureGenerationConfig,
    FeatureRunConfig,
    FeatureRunMetadata,
    FeatureSpec,
    FeatureStatus,
    LabelTask,
)
from data_platform.generate_features.openai_batch_state import load_active_batch_state
from data_platform.generate_features.s3_feature_batches import (
    adopt_unrecorded_batch,
    attach_provenance,
    consolidate_final,
    parquet_rows,
    q44_columns,
    validate_q44_rows,
    write_batch,
)
from data_platform.generate_features.s3_feature_campaign import (
    ActiveStateMirror,
    CampaignObjectStore,
    FeaturePaths,
    append_errors,
    delete_active_state,
    load_manifest,
    new_manifest,
    read_failed_ids,
    run_id_for_feature,
    save_manifest,
)
from data_platform.utils.object_store import S3_KEY_PREFIX
from data_platform.utils.platform_specific_columns import (
    STANDARDIZED_SOURCE_RECORD_ID_COLUMN,
    STANDARDIZED_TEXT_COLUMN,
)
from data_platform.utils.storage import DATA_ROOT, StorageManager, StorageStage
from lib.timestamp_utils import get_current_timestamp

CAMPAIGN_ENGINE_TYPE = "openai"
# Manifest fields that must match between a resumed run and the command line.
MANIFEST_IDENTITY_FIELDS = (
    "campaign_id",
    "dataset_id",
    "preprocessed_run",
    "feature",
    "model_id",
    "prompt_hash",
    "batch_size",
    "expected_row_count",
    "run_id",
)


def tasks_from_dataframe(
    records: pd.DataFrame,
    id_column: str,
    text_column: str,
) -> list[LabelTask]:
    """Convert a posts dataframe into LabelTask rows for batch labeling."""
    if records.empty:
        return []
    return [
        LabelTask(uri=str(row[id_column]), text=str(row[text_column]))
        for _, row in records.iterrows()
    ]


def filter_records_needing_features(
    records: pd.DataFrame,
    feature_name: str,
    config: FeatureGenerationConfig,
) -> pd.DataFrame:
    """Return records that still need labels for feature_name."""
    return config.feature_label_query.filter_unlabeled(records, feature_name)


def _make_on_batch_complete(
    metadata: FeatureRunMetadata,
    feature_name: str,
    features_dir: Path,
) -> Callable[[int, int], None]:
    """Build a callback that flushes metadata after each atomic batch."""

    def on_batch_complete(labeled_delta: int, failed_delta: int) -> None:
        update_batch_counts(metadata, feature_name, labeled_delta, failed_delta)
        flush_metadata(features_dir, metadata)

    return on_batch_complete


def _all_records_labeled_once(
    records: pd.DataFrame,
    feature_name: str,
    config: FeatureGenerationConfig,
    feature_storage: StorageManager,
) -> bool:
    """Return True when no input record is unlabeled and no label id repeats."""
    if not filter_records_needing_features(records, feature_name, config).empty:
        return False
    try:
        labels = feature_storage.load_records(run_dir=config.features_dir)
    except FileNotFoundError:
        return False
    id_column = config.feature_label_query.feature_file_id_column
    return not labels[id_column].astype(str).duplicated().any()


def _run_feature_labeling(
    feature_name: str,
    spec: FeatureSpec,
    records: pd.DataFrame,
    tasks: list[LabelTask],
    config: FeatureGenerationConfig,
    metadata: FeatureRunMetadata,
    feature_storage: StorageManager,
) -> BatchRunStats:
    """Label the pending tasks for one feature and complete it on exact id coverage.

    The feature becomes ``completed`` only when every record in ``records``
    has exactly one label row. Earlier failed batches do not block completion
    once a later retry has labeled their records.
    """
    mark_feature_in_progress(metadata, feature_name)
    flush_metadata(config.features_dir, metadata)

    # LangChain or custom engine, each of which has their own way of managing
    # concurrency
    engine = build_engine(spec, config.run_config)
    stats = engine.label_records(
        tasks,
        feature_name=feature_name,
        feature_storage=feature_storage,
        batch_size=config.run_config.batch_size,
        on_batch_complete=_make_on_batch_complete(metadata, feature_name, config.features_dir),
        id_column=config.feature_label_query.feature_file_id_column,
        run_dir=config.features_dir,
    )

    feature_status = metadata.features.setdefault(feature_name, FeatureStatus())
    if stats.failed_batches > feature_status.failed_batches:
        update_batch_counts(
            metadata,
            feature_name,
            labeled_delta=0,
            failed_batches_delta=stats.failed_batches - feature_status.failed_batches,
        )

    if _all_records_labeled_once(records, feature_name, config, feature_storage):
        mark_feature_completed(metadata, feature_name, feature_status.labeled)
    flush_metadata(config.features_dir, metadata)
    return stats


def _process_one_feature(
    feature_name: str,
    spec: FeatureSpec,
    records: pd.DataFrame,
    config: FeatureGenerationConfig,
    metadata: FeatureRunMetadata,
) -> Path:
    """Label posts for a single feature and export labels."""
    feature_status = metadata.features.get(feature_name)
    feature_storage = StorageManager(
        config.platform,
        StorageStage.FEATURES,
        spec.model,
        config.input_storage.dataset_id,
        records_filename=feature_name,
    )
    feature_path = config.features_dir / feature_storage.records_filename

    if feature_status and feature_status.status == "completed":
        print(f"generate_features: skipping completed feature {feature_name}")
        return feature_path

    # Compare input posts against saved labels, to see which records need features.
    pending_df = filter_records_needing_features(records, feature_name, config)
    tasks = tasks_from_dataframe(pending_df, config.id_column, config.text_column)

    if len(tasks) == 0:
        prior_labeled = feature_status.labeled if feature_status else 0
        mark_feature_completed(metadata, feature_name, prior_labeled)
        flush_metadata(config.features_dir, metadata)
        print(f"generate_features: {feature_name} — nothing to label")
        return feature_path

    stats = _run_feature_labeling(
        feature_name, spec, records, tasks, config, metadata, feature_storage
    )
    print(
        f"generate_features: {feature_name} -> {stats.labeled} new labels "
        f"({stats.failed_batches} failed batches) -> {feature_path}"
    )
    return feature_path


def _mark_sync_completed(
    metadata: FeatureRunMetadata,
    features_dir: Path,
) -> None:
    """Set sync_status completed when every stored feature entry is completed."""
    if not metadata.features:
        return
    all_done = all(status.status == "completed" for status in metadata.features.values())
    if all_done:
        set_sync_status_completed(metadata)
        flush_metadata(features_dir, metadata)


def generate_features(
    records: pd.DataFrame,
    config: FeatureGenerationConfig,
    resume: bool,
) -> dict[str, Path]:
    """Generate configured features with resumable append to timestamped run files.

    Parameters
    ----------
    records
        Preprocessed rows to label.
    config
        Feature generation config, including the chosen ``features_dir``.
    resume
        True loads metadata for that unfinished folder. False inits metadata
        for a new folder.

    Returns
    -------
    dict[str, Path]
        Feature name to the label file written in this run folder.
    """
    if records.empty:
        print("generate_features: no records to label")
        return {}

    feature_names = tuple(config.feature_registry.keys())
    if resume:
        metadata = load_feature_run_metadata(config, feature_names)
    else:
        metadata = init_feature_run_metadata(config, feature_names)

    written: dict[str, Path] = {}

    for feature_name, spec in config.feature_registry.items():
        print(f"Generating features for {feature_name}")
        written[feature_name] = _process_one_feature(
            feature_name,
            spec,
            records,
            config,
            metadata,
        )
        print(f"Completed feature generation for {feature_name}")

    _mark_sync_completed(metadata, config.features_dir)

    print(f"generate_features: finished {len(written)} features under {config.features_dir}")
    return written


def generate_campaign_feature(
    records: pd.DataFrame,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    run_config: FeatureRunConfig,
    *,
    paths: FeaturePaths | None = None,
) -> FeaturePaths:
    """Label one feature of a campaign into immutable S3 batch objects and resume from S3 state.

    ``records`` must hold a ``source_record_id`` column and a ``text`` column.
    Rows are sorted by ``source_record_id`` and split into ``campaign.batch_size``
    chunks. Chunk ``k`` writes ``batches/part-{k:05d}.parquet`` once, and a chunk
    that already has a batch object is skipped. ``paths`` defaults to the
    canonical feature prefix for ``campaign``.

    ``final.parquet`` is written once every id is either labeled or recorded in
    ``errors.jsonl`` as failed for good, so permanent failures do not block the
    final file. Once the manifest records a final file the call returns at once
    without labeling, so a chunk whose rows all failed permanently is not
    retried after that point.

    Raises
    ------
    ValueError
        When ``spec`` is not an OpenAI feature, when ``records`` repeats an id,
        or when an existing manifest describes a different campaign, dataset,
        preprocessed run, model, prompt, batch size, or row count.
    """
    if spec.engine_type != CAMPAIGN_ENGINE_TYPE:
        raise ValueError(f"campaign mode requires engine_type {CAMPAIGN_ENGINE_TYPE!r}")
    paths = paths or FeaturePaths.canonical(
        campaign.campaign_id,
        spec.name,
        platform=campaign.platform,
        dataset_id=campaign.dataset_id,
    )
    store = CampaignObjectStore(paths.bucket)
    run_id = run_id_for_feature(campaign.campaign_id, spec.name)
    ordered_ids, texts = _ordered_campaign_input(records)
    manifest, manifest_etag = _load_or_create_manifest(
        store, paths, campaign, spec, expected_row_count=len(ordered_ids)
    )
    if manifest.get("final_parquet"):
        print(
            f"generate_features: {spec.name} final.parquet already written -> "
            f"{paths.uri(paths.final_key)}"
        )
        return paths
    prelabeled = _smoke_rows_by_id(store, paths, spec, run_id)
    run_dir = _campaign_local_run_dir(paths)
    mirror = ActiveStateMirror(
        store,
        paths,
        run_dir=run_dir,
        feature_name=spec.name,
        campaign_id=campaign.campaign_id,
    )
    engine = OpenAIBatchEngine(
        spec,
        run_config,
        create_openai_client(),
        DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
        mirror.sleep,
    )
    written_parts = {int(entry["part_index"]) for entry in manifest["batches"]}
    for part_index, chunk_ids in enumerate(_chunks(ordered_ids, campaign.batch_size)):
        if part_index in written_parts:
            continue
        adopted = adopt_unrecorded_batch(
            store, paths, manifest, manifest_etag, part_index=part_index, run_id=run_id
        )
        if adopted is not None:
            manifest_etag = adopted.manifest_etag
            delete_active_state(store, paths)
            continue
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
    if final_etag is not None:
        final = manifest["final_parquet"]
        print(
            f"generate_features: {spec.name} -> {paths.uri(paths.final_key)} "
            f"({final['row_count']} rows, {final['failed_row_count']} permanently failed ids excluded)"
        )
    return paths


def _ordered_campaign_input(records: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    """Return the input ids in ascending order and the text for each id."""
    ordered = records.sort_values(STANDARDIZED_SOURCE_RECORD_ID_COLUMN, kind="stable")
    ids = ordered[STANDARDIZED_SOURCE_RECORD_ID_COLUMN].astype(str).tolist()
    if len(set(ids)) != len(ids):
        raise ValueError("campaign input repeats a source_record_id")
    texts = dict(zip(ids, ordered[STANDARDIZED_TEXT_COLUMN].astype(str), strict=True))
    return ids, texts


def _chunks(ids: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(ids), size):
        yield ids[start : start + size]


def _campaign_local_run_dir(paths: FeaturePaths) -> Path:
    """Return the local directory that mirrors the feature prefix, for the engine state file."""
    relative = paths.prefix.removeprefix(f"{S3_KEY_PREFIX}/")
    return DATA_ROOT / relative


def _load_or_create_manifest(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    campaign: CampaignRunConfig,
    spec: FeatureSpec,
    *,
    expected_row_count: int,
) -> tuple[dict, str]:
    """Return the manifest and its ETag, creating it on the first run and checking identity on resume."""
    fresh = new_manifest(campaign=campaign, spec=spec, expected_row_count=expected_row_count)
    manifest, etag = load_manifest(store, paths)
    if manifest is None or etag is None:
        return fresh, save_manifest(store, paths, fresh, None)
    mismatched = [
        field for field in MANIFEST_IDENTITY_FIELDS if manifest.get(field) != fresh[field]
    ]
    if mismatched:
        raise ValueError(
            f"manifest at {paths.uri(paths.manifest_key)} does not match this run on {mismatched}"
        )
    return manifest, etag


def _smoke_rows_by_id(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    spec: FeatureSpec,
    run_id: str,
) -> dict[str, dict]:
    """Return the Q44 rows of ``smoke/output.parquet`` keyed by id, or an empty dict when absent."""
    stored = store.get(paths.smoke_output_key)
    if stored is None:
        return {}
    rows = parquet_rows(stored.body)[q44_columns(spec)].to_dict(orient="records")
    validate_q44_rows(rows, spec, run_id=run_id)
    return {str(row["source_record_id"]): row for row in rows}


def _spill_path(run_dir: Path, feature_name: str, part_index: int) -> Path:
    return run_dir / f"{feature_name}.part-{part_index:05d}.rows.jsonl"


def _load_spilled_rows(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return {str(row["source_record_id"]): row for row in rows}


def _append_spilled_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(f"{json.dumps(row)}\n")


def _label_campaign_chunk(
    engine: OpenAIBatchEngine,
    mirror: ActiveStateMirror,
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict,
    manifest_etag: str,
    *,
    spec: FeatureSpec,
    run_id: str,
    run_dir: Path,
    part_index: int,
    chunk_ids: list[str],
    texts: dict[str, str],
    prelabeled: dict[str, dict],
) -> str:
    """Label one chunk, write its batch object, log failures, and return the new manifest ETag.

    Rows that arrive from each provider job are appended to a local spill file
    right away, so a restart after a partial chunk reuses them instead of
    paying for those posts again. The S3 ``active_openai_batch.json`` is deleted
    only after the batch object and its manifest entry exist.
    """
    spill_path = _spill_path(run_dir, spec.name, part_index)
    rows_by_id = {**_load_spilled_rows(spill_path)}
    rows_by_id.update({uri: prelabeled[uri] for uri in chunk_ids if uri in prelabeled})
    tasks = [LabelTask(uri=uri, text=texts[uri]) for uri in chunk_ids if uri not in rows_by_id]
    failures: list[RecordLabelFailure] = []
    if tasks:
        mirror.seed_local()

        def write_rows(rows: list[dict]) -> None:
            state = load_active_batch_state(run_dir, spec.name)
            if state is None:
                raise RuntimeError("engine delivered rows without an active batch state")
            request_ids = {
                uri: f"{CUSTOM_ID_PREFIX}{index:0{CUSTOM_ID_INDEX_WIDTH}d}"
                for index, uri in enumerate(state["pending_source_record_ids"])
            }
            with_provenance = attach_provenance(
                rows,
                run_id=run_id,
                batch_id=state["batch_id"],
                request_ids=request_ids,
                attempt_count=int(state["attempt_count"]),
            )
            _append_spilled_rows(spill_path, with_provenance)
            rows_by_id.update({row["source_record_id"]: row for row in with_provenance})
            mirror.sync()

        failures = engine.label_chunk(
            tasks,
            feature_name=spec.name,
            run_dir=run_dir,
            batch_index=part_index,
            write_rows=write_rows,
        )
    rows = [rows_by_id[uri] for uri in chunk_ids if uri in rows_by_id]
    if rows:
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
        manifest_etag = result.manifest_etag
        print(
            f"generate_features: {spec.name} part {part_index:05d} -> "
            f"{paths.uri(result.key)} ({result.row_count} rows, sha256 {result.sha256})"
        )
    if failures:
        timestamp = get_current_timestamp()
        append_errors(
            store,
            paths,
            [
                {
                    "ts": timestamp,
                    "run_id": run_id,
                    "part_index": part_index,
                    "source_record_id": failure.source_record_id,
                    "error": failure.error,
                    "attempts": failure.attempts,
                }
                for failure in failures
            ],
        )
        print(
            f"generate_features: {spec.name} part {part_index:05d} left "
            f"{len(failures)} posts unlabeled -> {paths.uri(paths.errors_key)}"
        )
    delete_active_state(store, paths)
    spill_path.unlink(missing_ok=True)
    return manifest_etag
