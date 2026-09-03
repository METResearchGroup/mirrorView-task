"""Sync Bluesky posts from a YAML config to storage.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py new-run \\
        --config data_platform/ingestion/configs/bluesky/mirrorview.yaml

    PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py resume \\
        --config data_platform/ingestion/configs/bluesky/mirrorview.yaml \\
        --run-dir 2026_05_30-12:00:00

    PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py resume \\
        --config data_platform/ingestion/configs/bluesky/mirrorview.yaml \\
        --latest

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

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
    load_checkpoint_run,
    mark_task_completed,
    mark_task_failed,
    mark_task_in_progress,
    parse_max_posts,
    require_dataset_id,
    require_latest_in_progress_run_dir,
    resolve_dedupe_policy,
    run_checkpointed_sync,
    start_new_sync_run,
)
from data_platform.utils.config_paths import load_yaml_config, resolve_config_path
from data_platform.utils.deduplication import (
    DedupeConfig,
    DedupeSession,
    policy_includes_prior_runs,
)
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from lib.constants import REPO_ROOT


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
        )
    )
    if policy_includes_prior_runs(resolve_dedupe_policy(ingestion_params)):
        dedupe_session.load_seen_ids_from_all_runs(storage)
    else:
        dedupe_session.load_seen_ids(storage, output_dir)

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


@dataclass(frozen=True)
class BlueskyRuntime:
    """Execution-time state shared by Bluesky new-run and resume."""

    storage: BlueskyStorageManager
    ingestion_params: dict[str, Any]
    sync_tasks: list[BlueskyTask]
    client: BlueskyClient
    filename: str


def load_bluesky_runtime(config_path: Path) -> tuple[dict[str, Any], BlueskyRuntime]:
    """Load config and return execution-time runtime for one sync.

    Parameters
    ----------
    config_path
        Ingestion YAML path. The dataset manifest is created on first use.

    Returns
    -------
    tuple[dict[str, Any], BlueskyRuntime]
        The loaded config and the shared runtime.

    Raises
    ------
    ValueError
        When ``dataset_id`` is missing, or when ``record_types`` does not
        include Bluesky posts.
    """
    config = load_yaml_config(config_path)
    dataset_id = require_dataset_id(config, platform="bluesky")
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
    return (
        config,
        BlueskyRuntime(
            storage=storage,
            ingestion_params=ingestion_params,
            sync_tasks=sync_tasks,
            client=BlueskyClient(),
            filename=storage.records_filename,
        ),
    )


def execute_bluesky_sync(
    runtime: BlueskyRuntime,
    output_dir: Path,
    metadata: dict[str, Any],
) -> Path:
    """Run keyword tasks and finalize metadata for an opened raw run.

    Parameters
    ----------
    runtime
        Shared execution-time state.
    output_dir
        Opened raw run directory.
    metadata
        Run metadata to update in place.

    Returns
    -------
    Path
        The same ``output_dir`` after tasks are synced and metadata is flushed.
    """
    run_sync_tasks(
        runtime.client,
        runtime.ingestion_params,
        output_dir,
        runtime.storage,
        metadata,
        runtime.sync_tasks,
        filename=runtime.filename,
    )
    finalize_local_disk_sync(runtime.storage, output_dir, metadata)
    total_rows = metadata["row_count"]
    print(
        f"sync_records: wrote {total_rows} rows to {output_dir} "
        f"(status={metadata['sync_status']})"
    )
    return output_dir


def sync_records_new_run(config_path: Path) -> Path:
    """Create a new raw run and sync keyword tasks into it.

    Parameters
    ----------
    config_path
        Ingestion YAML path.

    Returns
    -------
    Path
        New raw run directory.

    Raises
    ------
    ValueError
        When an unfinished raw run already exists for this dataset.
    """
    config, runtime = load_bluesky_runtime(config_path)
    output_dir, metadata = start_new_sync_run(
        runtime.storage,
        lambda ts: init_sync_metadata(config, config_path, ts, runtime.sync_tasks),
    )
    return execute_bluesky_sync(runtime, output_dir, metadata)


def sync_records_from_checkpoint(
    config_path: Path,
    run_dir_name: str,
) -> Path:
    """Resume an unfinished raw run by name.

    Parameters
    ----------
    config_path
        Ingestion YAML path.
    run_dir_name
        Raw run timestamp directory name.

    Returns
    -------
    Path
        Resumed raw run directory.

    Raises
    ------
    FileNotFoundError
        When the named run is missing.
    ValueError
        When the run is already completed.
    """
    config, runtime = load_bluesky_runtime(config_path)
    output_dir, metadata = load_checkpoint_run(
        runtime.storage,
        runtime.sync_tasks,
        run_dir_name,
        "keywords",
    )
    return execute_bluesky_sync(runtime, output_dir, metadata)


CONFIG_HELP = (
    "Ingestion YAML path relative to the repo root. "
    "For example, data_platform/ingestion/configs/bluesky/mirrorview.yaml."
)

app = typer.Typer(no_args_is_help=True)


@app.command("new-run")
def new_run_command(
    config: Path = typer.Option(..., "--config", help=CONFIG_HELP),
) -> None:
    """Start a new Bluesky raw run. Fails if an unfinished run already exists."""
    config_path = resolve_config_path(config, REPO_ROOT)
    sync_records_new_run(config_path)


def _resolve_resume_run_dir(
    storage: BlueskyStorageManager,
    run_dir: str | None,
    latest: bool,
) -> str:
    """Return the run directory name to resume, or raise for invalid options."""
    if (run_dir is not None and latest) or (run_dir is None and not latest):
        raise ValueError(
            "Resume requires exactly one of --run-dir or --latest"
        )
    if run_dir is not None:
        return run_dir
    return require_latest_in_progress_run_dir(storage).name


@app.command("resume")
def resume_command(
    config: Path = typer.Option(..., "--config", help=CONFIG_HELP),
    run_dir: str | None = typer.Option(
        None,
        "--run-dir",
        help="Raw run timestamp directory name to resume (e.g. 2026_05_30-12:00:00)",
    ),
    latest: bool = typer.Option(
        False,
        "--latest",
        help="Resume the newest unfinished raw run for this dataset.",
    ),
) -> None:
    """Resume an unfinished Bluesky raw run. Requires --run-dir or --latest."""
    config_path = resolve_config_path(config, REPO_ROOT)
    config, runtime = load_bluesky_runtime(config_path)
    resolved_run_dir = _resolve_resume_run_dir(runtime.storage, run_dir, latest)
    sync_records_from_checkpoint(config_path, resolved_run_dir)


def main() -> None:
    """CLI entrypoint for sync_bluesky.py. Requires new-run or resume."""
    app()


if __name__ == "__main__":
    main()
