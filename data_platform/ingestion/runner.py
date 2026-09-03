"""Shared orchestration for ingestion sync entrypoints.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \\
        --config data_platform/ingestion/configs/bluesky/mirrorview.yaml
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data_platform.ingestion.sync_checkpoint import (
    HasTaskId,
    build_base_sync_metadata,
    ensure_dataset_manifest,
    finalize_local_disk_sync,
    increment_duplicate_skip_counters,
    mark_task_completed,
    mark_task_failed,
    mark_task_in_progress,
    parse_max_posts,
    prepare_sync_run,
    require_dataset_id,
    resolve_dedupe_policy,
    resolve_limit_per_task,
    run_checkpointed_sync,
    run_sync_cli,
)
from data_platform.utils.config_paths import load_yaml_config
from data_platform.utils.deduplication import (
    DedupeConfig,
    DedupeSession,
    policy_includes_prior_runs,
)
from data_platform.utils.storage import StorageManager, StorageStage

StorageManagerFactory = Callable[..., StorageManager]

KeywordFetchFn = Callable[
    [Any, HasTaskId, str, int | None],
    tuple[list[dict[str, Any]], dict[str, Any]] | None,
]

SyncRunHook = Callable[..., None]
SummarizeRunFn = Callable[[dict[str, Any], Path], None]


@dataclass(frozen=True)
class KeywordSyncParams:
    """Dedupe identity and progress labels for one Bluesky or Twitter keyword loop."""

    id_column: str
    record_type: str
    tqdm_desc: str = "Syncing keywords"


@dataclass(frozen=True)
class SyncPlatformSpec:
    """Platform settings for shared ingest orchestration.

    Each sync script supplies fetch, validation, and task-building hooks. The
    runner owns load-config, dataset manifest, run resume, and finalize. Reddit
    keeps its own dual-output loop; Bluesky and Twitter share the keyword loop.
    """

    platform: str
    storage_cls: StorageManagerFactory
    entity_label: str
    init_client: Callable[[], Any]
    build_sync_tasks: Callable[[dict[str, Any]], Sequence[HasTaskId]]
    task_progress_builder: Callable[[Any], dict[str, Any]]
    validate_config: Callable[[dict[str, Any]], None]
    run_sync_tasks: SyncRunHook
    summarize_run: SummarizeRunFn
    parse_record_cap: Callable[[dict[str, Any]], int | None] = parse_max_posts
    metadata_extra_fields: dict[str, Any] | None = None
    config_loader: Callable[[Path], dict[str, Any]] = load_yaml_config


def remaining_record_budget(metadata: dict[str, Any], record_cap: int | None) -> int | None:
    """Return how many records can still be written before the run cap is reached."""
    if record_cap is None:
        return None
    return record_cap - int(metadata["row_count"])


def effective_limit_per_keyword(
    ingestion_params: dict[str, Any],
    remaining: int | None,
) -> int:
    """Return the per-keyword fetch cap after applying any run-wide post budget."""
    per_keyword = resolve_limit_per_task(ingestion_params)
    if remaining is None:
        return per_keyword
    return max(0, min(per_keyword, remaining))


def run_keyword_sync_tasks(
    client: Any,
    ingestion_params: dict[str, Any],
    output_dir: Path,
    storage: StorageManager,
    metadata: dict[str, Any],
    sync_tasks: Sequence[HasTaskId],
    *,
    filename: str,
    params: KeywordSyncParams,
    fetch_for_task: KeywordFetchFn,
) -> None:
    """Run the checkpointed keyword loop shared by Bluesky and Twitter.

    Opens one dedupe session, fetches each task, appends deduped rows, and updates
    run metadata. Skips completed tasks on resume and honors ``max_posts``.
    """
    max_posts_int = parse_max_posts(ingestion_params)
    sync_timestamp = str(metadata["sync_timestamp"])
    dedupe_session = DedupeSession(
        DedupeConfig(
            id_column=params.id_column,
            filename=filename,
            include_prior_runs=policy_includes_prior_runs(
                resolve_dedupe_policy(ingestion_params)
            ),
        )
    )
    dedupe_session.warm(storage, output_dir)

    def process_task(task: HasTaskId, entry: dict[str, Any]) -> None:
        mark_task_in_progress(entry, storage, output_dir, metadata)

        remaining = remaining_record_budget(metadata, max_posts_int)
        try:
            fetch_result = fetch_for_task(client, task, sync_timestamp, remaining)
        except Exception as exc:  # noqa: BLE001 — record and continue
            mark_task_failed(entry, exc, task.task_id, storage, output_dir, metadata)
            return

        if fetch_result is None:
            return

        rows, stats = fetch_result
        result = storage.append_deduped_records(
            rows,
            output_dir,
            dedupe_session=dedupe_session,
            filename=filename,
        )
        increment_duplicate_skip_counters(
            metadata,
            record_type=params.record_type,
            skipped=result.skipped,
        )
        metadata["row_count"] = len(dedupe_session.seen_ids)
        entry_updates: dict[str, Any] = {
            "pages_fetched": stats["pages_fetched"],
            "rows_collected": stats["rows_collected"],
        }
        if "hits_total" in stats:
            entry_updates["hits_total"] = stats["hits_total"]
        mark_task_completed(
            entry,
            storage,
            output_dir,
            metadata,
            entry_updates=entry_updates,
        )

        print(
            f"sync_records: {task.task_id} -> {stats['rows_collected']} rows "
            f"(appended {result.kept}, pages={stats['pages_fetched']})"
        )

    run_checkpointed_sync(
        sync_tasks,
        metadata,
        storage,
        output_dir,
        record_cap=max_posts_int,
        tqdm_desc=params.tqdm_desc,
        process_task=process_task,
    )


def sync_with_spec(
    config_path: Path,
    *,
    run_dir_name: str | None = None,
    spec: SyncPlatformSpec,
    config_loader: Callable[[Path], dict[str, Any]] | None = None,
) -> Path:
    """Load config, prepare or resume a raw run, and delegate to the platform hook.

    Returns
    -------
    Path
        Output run directory for the sync.
    """
    load_config = config_loader or spec.config_loader
    config = load_config(config_path)
    dataset_id = require_dataset_id(config, platform=spec.platform)

    ensure_dataset_manifest(
        spec.storage_cls(StorageStage.RAW, dataset_id),
        spec.platform,
        dataset_id,
        config,
        config_path,
    )
    storage = spec.storage_cls(StorageStage.RAW, dataset_id)

    spec.validate_config(config)

    ingestion_params = config["ingestion_params"]
    sync_tasks = list(spec.build_sync_tasks(ingestion_params))
    client = spec.init_client()

    def init_metadata(sync_timestamp: str) -> dict[str, Any]:
        return build_base_sync_metadata(
            config,
            config_path,
            sync_timestamp,
            sync_tasks,
            task_progress_builder=spec.task_progress_builder,
            extra_fields=spec.metadata_extra_fields,
        )

    output_dir, metadata = prepare_sync_run(
        storage,
        sync_tasks,
        run_dir_name=run_dir_name,
        init_metadata_fn=init_metadata,
        entity_label=spec.entity_label,
    )

    spec.run_sync_tasks(
        client,
        ingestion_params,
        output_dir,
        storage,
        metadata,
        sync_tasks,
        config=config,
        config_path=config_path,
    )

    finalize_local_disk_sync(storage, output_dir, metadata)
    spec.summarize_run(metadata, output_dir)
    return output_dir


def make_sync_cli(spec: SyncPlatformSpec, *, config_help: str) -> Callable[[], None]:
    """Return a Typer ``main`` function for a platform sync script."""

    def main() -> None:
        run_sync_cli(
            sync_records_fn=lambda config_path, *, run_dir_name=None: sync_with_spec(
                config_path,
                run_dir_name=run_dir_name,
                spec=spec,
            ),
            config_help=config_help,
        )

    return main
