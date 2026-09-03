"""Resumable feature-generation orchestrator with batch execution engines."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

from data_platform.generate_features.engines import build_engine
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
    FeatureGenerationConfig,
    FeatureRunMetadata,
    FeatureSpec,
    FeatureStatus,
    LabelTask,
)
from data_platform.utils.storage import StorageManager, StorageStage


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


def _run_feature_labeling(
    feature_name: str,
    spec: FeatureSpec,
    tasks: list[LabelTask],
    config: FeatureGenerationConfig,
    metadata: FeatureRunMetadata,
    feature_storage: StorageManager,
) -> BatchRunStats:
    """Execute batch labeling for one feature and update metadata on completion."""
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

    if stats.failed_batches > 0 or feature_status.failed_batches > 0:
        flush_metadata(config.features_dir, metadata)
        return stats

    total_labeled = feature_status.labeled
    mark_feature_completed(metadata, feature_name, total_labeled)
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

    stats = _run_feature_labeling(feature_name, spec, tasks, config, metadata, feature_storage)
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
    all_done = all(
        status.status == "completed" and status.failed_batches == 0
        for status in metadata.features.values()
    )
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
