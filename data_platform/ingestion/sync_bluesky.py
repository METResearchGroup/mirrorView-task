"""Sync Bluesky posts from a YAML config to storage.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \\
        --config data_platform/ingestion/configs/bluesky/mirrorview.yaml

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data_platform.ingestion.integrations.bluesky import (
    POSTS_RECORD_TYPE,
    BlueskyClient,
)
from data_platform.ingestion.query_terms import quote_query_term
from data_platform.ingestion.sync_checkpoint import (
    TaskStatus,
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
    run_checkpointed_sync,
    run_sync_cli,
)
from data_platform.utils.config_paths import load_yaml_config
from data_platform.utils.deduplication import (
    DedupeConfig,
    DedupeSession,
    policy_includes_prior_runs,
)
from data_platform.utils.storage import BlueskyStorageManager, StorageStage


@dataclass(frozen=True)
class BlueskyTask:
    """One keyword search task tracked by the checkpoint system.

    It stores a stable task ID and the API query string.
    """

    task_id: str
    query: str


def build_sync_tasks(ingestion_params: dict[str, Any]) -> list[BlueskyTask]:
    """Build one sync task for each entry in ingestion_params.keywords."""
    keywords = ingestion_params.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        raise ValueError("ingestion_params must include 'keywords' as a non-empty list of strings")

    items: list[BlueskyTask] = []
    for raw in keywords:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("ingestion_params.keywords entries must be non-empty strings")
        keyword = raw.strip()
        items.append(BlueskyTask(task_id=keyword, query=quote_query_term(keyword)))
    return items


def _initial_task_progress(task: BlueskyTask) -> dict[str, Any]:
    """Return the pending entry for the task ledger that is written into run metadata at sync start."""
    return {
        "status": TaskStatus.PENDING.value,
        "kind": "bluesky",
        "keyword": task.task_id,
        "pages_fetched": 0,
        "rows_collected": 0,
        "hits_total": None,
        "last_error": None,
    }


def init_sync_metadata(
    config: dict[str, Any],
    config_path: Path,
    sync_timestamp: str,
    sync_tasks: list[BlueskyTask],
) -> dict[str, Any]:
    """Return the initial metadata.json payload for a new raw run directory."""
    return build_base_sync_metadata(
        config,
        config_path,
        sync_timestamp,
        sync_tasks,
        task_progress_builder=_initial_task_progress,
    )


def run_sync_tasks(
    client: BlueskyClient,
    ingestion_params: dict[str, Any],
    output_dir: Path,
    storage: BlueskyStorageManager,
    metadata: dict[str, Any],
    sync_tasks: list[BlueskyTask],
    *,
    filename: str,
) -> None:
    """Run the keyword loop for each checkpointed task.

    For each task, fetch rows for the keyword. Append the deduped rows, and flush the metadata.
    On resume, skip tasks that are already completed. Stop early when max_posts is reached.
    Record failures for each task without aborting the whole run.
    """
    max_posts_int = parse_max_posts(ingestion_params)
    dedupe_session = DedupeSession(
        DedupeConfig(
            id_column="uri",
            filename=filename,
            include_prior_runs=policy_includes_prior_runs(
                resolve_dedupe_policy(ingestion_params)
            ),
        )
    )
    dedupe_session.warm(storage, output_dir)

    def process_task(task: BlueskyTask, entry: dict[str, Any]) -> None:
        """Fetch rows for one keyword. Persist the deduped rows, and update the task ledger entry."""
        mark_task_in_progress(entry, storage, output_dir, metadata)

        remaining: int | None = None
        if max_posts_int is not None:
            remaining = max_posts_int - int(metadata["row_count"])
            if remaining <= 0:
                return

        try:
            result = client.fetch_posts_for_keyword(
                ingestion_params,
                task.query,
                task_id=task.task_id,
                sync_timestamp=str(metadata["sync_timestamp"]),
                remaining_posts=remaining,
            )
        except Exception as exc:  # noqa: BLE001  # record and continue
            mark_task_failed(entry, exc, task.task_id, storage, output_dir, metadata)
            return

        storage_result = storage.append_deduped_records(
            result.rows,
            output_dir,
            dedupe_session=dedupe_session,
            filename=filename,
        )
        increment_duplicate_skip_counters(
            metadata,
            record_type=POSTS_RECORD_TYPE,
            skipped=storage_result.skipped,
        )
        metadata["row_count"] = len(dedupe_session.seen_ids)
        mark_task_completed(
            entry,
            storage,
            output_dir,
            metadata,
            entry_updates={
                "pages_fetched": result.stats["pages_fetched"],
                "rows_collected": result.stats["rows_collected"],
                "hits_total": result.stats["hits_total"],
            },
        )

        print(
            f"sync_records: {task.task_id} -> {result.stats['rows_collected']} rows "
            f"(appended {storage_result.kept}, pages={result.stats['pages_fetched']})"
        )

    run_checkpointed_sync(
        sync_tasks,
        metadata,
        storage,
        output_dir,
        record_cap=max_posts_int,
        tqdm_desc="Syncing keywords",
        process_task=process_task,
    )


def sync_records(
    config_path: Path,
    *,
    run_dir_name: str | None = None,
) -> Path:
    """Load the config and prepare or resume a raw run.

    Then sync all keyword tasks to posts.csv. Creates the dataset manifest on first run
    and returns the output run directory path.
    """
    config = load_yaml_config(config_path)
    dataset_id = require_dataset_id(config, platform="bluesky")

    # Create a temporary storage manager just to locate the dataset root for the manifest.
    # The manifest must exist before we create the real storage manager.
    # New datasets have no dataset.json yet, so the manager cannot read the format without it.
    ensure_dataset_manifest(
        BlueskyStorageManager(StorageStage.RAW, dataset_id),
        "bluesky",
        dataset_id,
        config,
        config_path,
    )
    storage = BlueskyStorageManager(StorageStage.RAW, dataset_id)

    ingestion_params = config["ingestion_params"]
    sync_tasks = build_sync_tasks(ingestion_params)
    record_types: list[str] = config["record_types"]

    if POSTS_RECORD_TYPE not in record_types:
        raise ValueError(f"Unsupported record types for checkpoint sync: {record_types}")

    filename = storage.records_filename
    client = BlueskyClient()

    output_dir, metadata = prepare_sync_run(
        storage,
        sync_tasks,
        run_dir_name=run_dir_name,
        init_metadata_fn=lambda ts: init_sync_metadata(config, config_path, ts, sync_tasks),
        entity_label="keywords",
    )

    run_sync_tasks(
        client,
        ingestion_params,
        output_dir,
        storage,
        metadata,
        sync_tasks,
        filename=filename,
    )

    finalize_local_disk_sync(storage, output_dir, metadata)

    total_rows = metadata["row_count"]
    print(
        f"sync_records: wrote {total_rows} rows to {output_dir} (status={metadata['sync_status']})"
    )
    return output_dir


def main() -> None:
    """CLI entrypoint for sync_bluesky.py. Supports --config, --resume, and --run-dir."""
    run_sync_cli(
        sync_records_fn=sync_records,
        config_help=(
            "Ingestion YAML path relative to the repo root. "
            "For example, data_platform/ingestion/configs/bluesky/mirrorview.yaml."
        ),
    )


if __name__ == "__main__":
    main()
