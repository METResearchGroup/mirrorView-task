"""Shared checkpoint helpers for ingestion sync scripts."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, TypeVar

import typer
from tqdm import tqdm

from data_platform.utils.config_paths import resolve_config_path, to_repo_relative
from data_platform.utils.dataset import (
    ValidDataFormats,
    validate_dataset_id,
    write_dataset_manifest,
)
from data_platform.utils.storage import StorageManager
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

RECORD_TYPE_FILENAMES: dict[str, str] = {
    "app.bsky.feed.post": "posts.csv",
    "reddit.comment": "comments.csv",
    "reddit.post": "posts.csv",
}


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SyncStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


TASKS_KEY = "tasks"


class HasTaskId(Protocol):
    @property
    def task_id(self) -> str: ...


TTask = TypeVar("TTask", bound=HasTaskId)


def get_task_progress(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return metadata[TASKS_KEY]


def validate_tasks_for_resume(
    tasks: Sequence[HasTaskId],
    metadata: dict[str, Any],
    *,
    entity_label: str,
) -> None:
    progress = get_task_progress(metadata)
    task_ids = {task.task_id for task in tasks}
    metadata_ids = set(progress)
    missing = task_ids - metadata_ids
    extra = metadata_ids - task_ids
    if missing or extra:
        raise ValueError(
            f"Config {entity_label} do not match resume metadata "
            f"(missing in metadata: {sorted(missing)}, extra in metadata: {sorted(extra)})"
        )


def mark_remaining_tasks_skipped(progress: dict[str, dict[str, Any]]) -> None:
    for entry in progress.values():
        if entry["status"] == TaskStatus.PENDING.value:
            entry["status"] = TaskStatus.SKIPPED.value


def sync_status_from_tasks(progress: dict[str, dict[str, Any]]) -> SyncStatus:
    statuses = {entry["status"] for entry in progress.values()}
    unfinished = statuses - {TaskStatus.COMPLETED.value, TaskStatus.SKIPPED.value}
    return SyncStatus.COMPLETED if not unfinished else SyncStatus.IN_PROGRESS


def finalize_local_disk_sync(
    storage: StorageManager,
    output_dir: Path,
    metadata: dict[str, Any],
) -> None:
    """Set sync_status from tasks and flush metadata for a completed local sync run."""
    metadata["sync_status"] = sync_status_from_tasks(get_task_progress(metadata)).value
    flush_run_metadata(storage, output_dir, metadata)


def require_dataset_id(config: dict[str, Any], *, platform: str | None = None) -> str:
    raw = config.get("dataset_id")
    if not raw:
        hint = f" ({platform}_<uuid>)" if platform else ""
        raise ValueError(f"ingestion config must include dataset_id{hint}")
    return validate_dataset_id(str(raw))


def record_type_to_filename(record_type: str) -> str:
    if record_type in RECORD_TYPE_FILENAMES:
        return RECORD_TYPE_FILENAMES[record_type]
    return f"{record_type.rsplit('.', 1)[-1]}.csv"


def flush_run_metadata(
    storage: StorageManager,
    run_dir: Path,
    metadata: dict[str, Any],
) -> None:
    storage.write_run_metadata_atomic(run_dir, metadata)


def find_resume_run_dir(
    storage: StorageManager,
    *,
    run_dir_name: str | None,
) -> Path | None:
    if run_dir_name is not None:
        run_dir = storage.root_dir / run_dir_name
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Run directory not found: {run_dir}")
        return run_dir

    if not storage.root_dir.exists():
        return None

    candidates: list[tuple[str, Path]] = []
    for path in storage.root_dir.iterdir():
        if not path.is_dir():
            continue
        metadata_path = path / "metadata.json"
        if not metadata_path.exists():
            continue
        metadata = storage.load_run_metadata(path)
        if metadata.get("sync_status") != SyncStatus.COMPLETED.value:
            candidates.append((path.name, path))

    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def stop_at_record_cap(
    metadata: dict[str, Any],
    storage: StorageManager,
    output_dir: Path,
    record_cap: int | None,
) -> bool:
    """Mark pending tasks skipped and flush when the counted-record cap is reached.

    Parameters
    ----------
    record_cap
        Run-wide cap already resolved by ``parse_max_posts`` or
        ``parse_max_comments``. Compared against ``metadata["row_count"]``.
        None means no cap.
    """
    if record_cap is None or metadata["row_count"] < record_cap:
        return False
    mark_remaining_tasks_skipped(get_task_progress(metadata))
    flush_run_metadata(storage, output_dir, metadata)
    return True


LIMIT_PER_TASK_KEY = "limit_per_task"
MAX_POSTS_KEY = "max_posts"
MAX_COMMENTS_KEY = "max_comments"
DEDUPE_POLICY_KEY = "dedupe_policy"
COMMENTS_DEDUPE_POLICY_KEY = "comments_dedupe_policy"
POSTS_DEDUPE_POLICY_KEY = "posts_dedupe_policy"
ROWS_SKIPPED_AS_DUPLICATES_KEY = "rows_skipped_as_duplicates"
SKIPPED_BY_RECORD_TYPE_KEY = "skipped_as_duplicates_by_record_type"


def resolve_dedupe_policy(ingestion_params: dict[str, Any]) -> object:
    """Return the YAML ``dedupe_policy`` skip list.

    Returns
    -------
    object
        The YAML list, or None when ``dedupe_policy`` is unset.
    """
    return ingestion_params.get(DEDUPE_POLICY_KEY)


def bootstrap_duplicate_skip_counters(
    metadata: dict[str, Any],
    *,
    legacy_by_record_type: dict[str, str],
) -> None:
    """Seed canonical skip counters from leftover platform names when missing.

    Parameters
    ----------
    metadata
        Run metadata. ``rows_skipped_as_duplicates`` is the run-level total.
        ``skipped_as_duplicates_by_record_type`` is the per-record-type map.
        Leftover names such as ``posts_skipped_as_duplicates`` are read only
        when those canonical keys are missing.
    legacy_by_record_type
        Map from record type to leftover metadata key. When a leftover key is
        present and that record type is not already in the breakdown, its
        integer value seeds that type. Missing canonical keys are then set
        from the seed map (total 0 and an empty map when no leftover names
        are present). When both canonical keys already exist, do nothing.
        Leftover names are not deleted or rewritten.
    """
    raise NotImplementedError


def increment_duplicate_skip_counters(
    metadata: dict[str, Any],
    *,
    record_type: str,
    skipped: int,
    legacy_by_record_type: dict[str, str],
) -> None:
    """Add skipped rows to canonical skip counters after a dedupe append.

    Parameters
    ----------
    metadata
        Run metadata to update in place. Seeds canonical keys from leftover
        names first via ``bootstrap_duplicate_skip_counters``.
    record_type
        Record type bucket to increment, e.g. ``app.bsky.feed.post``.
    skipped
        Number of rows skipped by this append.
    legacy_by_record_type
        Leftover name map passed through to bootstrap. Those leftover keys
        are never written back.
    """
    raise NotImplementedError


def _parse_optional_int_cap(
    ingestion_params: dict[str, Any],
    key: str,
) -> int | None:
    if key not in ingestion_params:
        return None
    value = ingestion_params[key]
    return int(value) if value is not None else None


def parse_max_posts(ingestion_params: dict[str, Any]) -> int | None:
    """Return the run-wide post cap from ``max_posts``.

    Parameters
    ----------
    ingestion_params
        Ingest YAML params. Only ``max_posts`` is read; ``max_comments`` is ignored.

    Returns
    -------
    int | None
        Max posts for the run, or None when ``max_posts`` is unset.
    """
    return _parse_optional_int_cap(ingestion_params, MAX_POSTS_KEY)


def parse_max_comments(ingestion_params: dict[str, Any]) -> int | None:
    """Return the run-wide comment cap from ``max_comments``.

    Parameters
    ----------
    ingestion_params
        Ingest YAML params. Only ``max_comments`` is read; ``max_posts`` is ignored.

    Returns
    -------
    int | None
        Max comments for the run, or None when ``max_comments`` is unset.
    """
    return _parse_optional_int_cap(ingestion_params, MAX_COMMENTS_KEY)


def resolve_limit_per_task(ingestion_params: dict[str, Any]) -> int:
    """Return the per-task fetch cap from ingestion_params."""
    return int(ingestion_params[LIMIT_PER_TASK_KEY])


def build_base_sync_metadata(
    config: dict[str, Any],
    config_path: Path,
    sync_timestamp: str,
    sync_tasks: Sequence[TTask],
    *,
    task_progress_builder: Callable[[TTask], dict[str, Any]],
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "sync_status": SyncStatus.IN_PROGRESS.value,
        "dataset_id": require_dataset_id(config),
        "name": config["name"],
        "description": config["description"],
        "date": config["date"],
        "sync_timestamp": sync_timestamp,
        "ingestion_config": to_repo_relative(config_path, REPO_ROOT),
        "record_types": config["record_types"],
        "ingestion_params": config["ingestion_params"],
        "row_count": 0,
        "tasks": {task.task_id: task_progress_builder(task) for task in sync_tasks},
    }
    if extra_fields:
        metadata.update(extra_fields)
    return metadata


def mark_task_in_progress(
    entry: dict[str, Any],
    storage: StorageManager,
    output_dir: Path,
    metadata: dict[str, Any],
) -> None:
    entry["status"] = TaskStatus.IN_PROGRESS.value
    entry["last_error"] = None
    flush_run_metadata(storage, output_dir, metadata)


def mark_task_failed(
    entry: dict[str, Any],
    exc: Exception,
    task_id: str,
    storage: StorageManager,
    output_dir: Path,
    metadata: dict[str, Any],
) -> None:
    entry["status"] = TaskStatus.FAILED.value
    entry["last_error"] = str(exc)
    flush_run_metadata(storage, output_dir, metadata)
    print(f"sync_records: {task_id} failed: {exc}")


def mark_task_completed(
    entry: dict[str, Any],
    storage: StorageManager,
    output_dir: Path,
    metadata: dict[str, Any],
    *,
    entry_updates: dict[str, Any],
    metadata_updates: dict[str, Any] | None = None,
) -> None:
    entry["status"] = TaskStatus.COMPLETED.value
    entry["last_error"] = None
    entry.update(entry_updates)
    if metadata_updates:
        metadata.update(metadata_updates)
    flush_run_metadata(storage, output_dir, metadata)


def run_checkpointed_sync(
    sync_tasks: Sequence[TTask],
    metadata: dict[str, Any],
    storage: StorageManager,
    output_dir: Path,
    *,
    record_cap: int | None,
    tqdm_desc: str,
    process_task: Callable[[TTask, dict[str, Any]], None],
) -> None:
    progress = get_task_progress(metadata)

    for task in tqdm(
        sync_tasks,
        desc=tqdm_desc,
        disable=not sys.stderr.isatty(),
    ):
        entry = progress[task.task_id]
        if entry["status"] in (TaskStatus.COMPLETED.value, TaskStatus.SKIPPED.value):
            continue

        if stop_at_record_cap(metadata, storage, output_dir, record_cap):
            break

        process_task(task, entry)

        if stop_at_record_cap(metadata, storage, output_dir, record_cap):
            break


def ensure_dataset_manifest(
    storage: StorageManager,
    platform: str,
    dataset_id: str,
    config: dict[str, Any],
    config_path: Path,
) -> None:
    manifest_path = storage.root_dir.parent / "dataset.json"
    if not manifest_path.exists():
        output_format = ValidDataFormats(config.get("output_format", "csv"))
        write_dataset_manifest(
            platform,
            dataset_id,
            name=str(config["name"]),
            ingestion_config=to_repo_relative(config_path, REPO_ROOT),
            data_format=output_format,
        )


def prepare_sync_run(
    storage: StorageManager,
    sync_tasks: Sequence[HasTaskId],
    *,
    run_dir_name: str | None,
    init_metadata_fn: Callable[[str], dict[str, Any]],
    entity_label: str,
) -> tuple[Path, dict[str, Any]]:
    resume_dir = find_resume_run_dir(storage, run_dir_name=run_dir_name)
    if resume_dir is not None:
        metadata = storage.load_run_metadata(resume_dir)
        if metadata.get("sync_status") != SyncStatus.IN_PROGRESS.value:
            metadata["sync_status"] = SyncStatus.IN_PROGRESS.value
            flush_run_metadata(storage, resume_dir, metadata)
        validate_tasks_for_resume(sync_tasks, metadata, entity_label=entity_label)
        print(f"sync_records: resuming {resume_dir}")
        return resume_dir, metadata

    sync_timestamp = get_current_timestamp()
    output_dir = storage.create_new_run_dir(sync_timestamp)
    metadata = init_metadata_fn(sync_timestamp)
    flush_run_metadata(storage, output_dir, metadata)
    print(f"sync_records: started new run {output_dir}")
    return output_dir, metadata


def run_sync_cli(
    *,
    sync_records_fn: Callable[..., Path],
    config_help: str,
) -> None:
    def main(
        config: Path = typer.Option(
            ...,
            "--config",
            help=config_help,
        ),
        run_dir: str | None = typer.Option(
            None,
            "--run-dir",
            help="Raw run timestamp directory name to resume (e.g. 2026_05_30-12:00:00)",
        ),
    ) -> None:
        config_path = resolve_config_path(config, REPO_ROOT)
        sync_records_fn(config_path, run_dir_name=run_dir)

    typer.run(main)
