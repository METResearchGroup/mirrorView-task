"""Sync Twitter posts from YAML config to raw records storage.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \\
        --config data_platform/ingestion/configs/twitter/mirrorview.yaml

Automatically resumes the most recent in-progress run for the dataset, or starts a new one.
Pin a specific run to resume with --run-dir:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \\
        --config data_platform/ingestion/configs/twitter/mirrorview.yaml \\
        --run-dir 2026_06_01-12:00:00

Ingestion YAML must include `dataset_id` (e.g. twitter_<uuid>).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    resolve_limit_per_task,
    run_checkpointed_sync,
    run_sync_cli,
)
from data_platform.ingestion.sync_clients import init_twitter_client
from data_platform.ingestion.twitter_client import fetch_posts_for_keyword
from data_platform.utils.config_paths import load_yaml_config
from data_platform.utils.deduplication import (
    DedupeConfig,
    DedupeSession,
    policy_includes_prior_runs,
)
from data_platform.utils.storage import StorageStage, TwitterStorageManager

TWEETS_RECORD_TYPE = "twitter.tweet"


@dataclass(frozen=True)
class TwitterTask:
    task_id: str
    keyword: str


def build_sync_tasks(ingestion_params: dict[str, Any]) -> list[TwitterTask]:
    """Build one checkpoint task per search term in ingestion_params."""
    keywords = ingestion_params.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        raise ValueError("ingestion_params must include 'keywords' as a non-empty list of strings")

    items: list[TwitterTask] = []
    for raw in keywords:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("ingestion_params.keywords entries must be non-empty strings")
        keyword = raw.strip()
        items.append(TwitterTask(task_id=keyword, keyword=keyword))
    return items


def _initial_task_progress(task: TwitterTask) -> dict[str, Any]:
    return {
        "status": TaskStatus.PENDING.value,
        "kind": "twitter",
        "keyword": task.keyword,
        "pages_fetched": 0,
        "rows_collected": 0,
        "last_error": None,
    }


def init_sync_metadata(
    config: dict[str, Any],
    config_path: Path,
    sync_timestamp: str,
    sync_tasks: list[TwitterTask],
) -> dict[str, Any]:
    return build_base_sync_metadata(
        config,
        config_path,
        sync_timestamp,
        sync_tasks,
        task_progress_builder=_initial_task_progress,
    )


def _effective_limit_per_keyword(ingestion_params: dict[str, Any], remaining: int | None) -> int:
    per_keyword = resolve_limit_per_task(ingestion_params)
    if remaining is None:
        return per_keyword
    return max(0, min(per_keyword, remaining))


def _remaining_post_budget(metadata: dict[str, Any], max_posts_int: int | None) -> int | None:
    if max_posts_int is None:
        return None
    return max_posts_int - metadata["row_count"]


def run_sync_tasks(
    client: Any,
    ingestion_params: dict[str, Any],
    output_dir: Path,
    storage: TwitterStorageManager,
    metadata: dict[str, Any],
    sync_tasks: list[TwitterTask],
    *,
    sync_timestamp: str,
    filename: str,
) -> None:
    """Run the checkpointed keyword loop: fetch, dedupe-append, and flush metadata per task.

    Skips completed tasks on resume, stops early when max_posts is reached, and records failures
    without aborting the full run.

    Parameters
    ----------
    filename
        Records file name from ``storage.records_filename``, including the dataset format suffix.
    """
    max_posts_int = parse_max_posts(ingestion_params)
    lang = str(ingestion_params.get("lang", "en"))
    exclude = list(ingestion_params.get("exclude", ["reply", "retweet", "quote"]))
    dedupe_session = DedupeSession(
        DedupeConfig(
            id_column="tweet_id",
            filename=filename,
        )
    )
    if policy_includes_prior_runs(resolve_dedupe_policy(ingestion_params)):
        dedupe_session.load_seen_ids_from_all_runs(storage)
    else:
        dedupe_session.load_seen_ids(storage, output_dir)

    def process_task(task: TwitterTask, entry: dict[str, Any]) -> None:
        mark_task_in_progress(entry, storage, output_dir, metadata)

        limit = _effective_limit_per_keyword(
            ingestion_params,
            _remaining_post_budget(metadata, max_posts_int),
        )
        try:
            rows, stats = fetch_posts_for_keyword(
                client,
                task.keyword,
                limit=limit,
                lang=lang,
                exclude=exclude,
                sync_timestamp=sync_timestamp,
            )
        except Exception as exc:  # noqa: BLE001 — record and continue
            mark_task_failed(entry, exc, task.task_id, storage, output_dir, metadata)
            return

        result = storage.append_deduped_records(
            rows,
            output_dir,
            dedupe_session=dedupe_session,
            filename=filename,
        )
        increment_duplicate_skip_counters(
            metadata,
            record_type=TWEETS_RECORD_TYPE,
            skipped=result.skipped,
        )
        metadata["row_count"] = len(dedupe_session.seen_ids)
        mark_task_completed(
            entry,
            storage,
            output_dir,
            metadata,
            entry_updates={
                "pages_fetched": stats["pages_fetched"],
                "rows_collected": stats["rows_collected"],
            },
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
        tqdm_desc="Syncing keywords",
        process_task=process_task,
    )


load_config = load_yaml_config


def sync_records(
    config_path: Path,
    *,
    run_dir_name: str | None = None,
) -> Path:
    """Fetch Twitter records per config and write raw records plus metadata.

    Creates the dataset manifest first so storage can read the declared format.
    Stops before creating the Twitter client when ``record_types`` is missing
    or does not include ``TWEETS_RECORD_TYPE``.

    Raises
    ------
    KeyError
        When the config has no ``record_types`` key.
    ValueError
        When ``record_types`` is empty or does not include
        ``TWEETS_RECORD_TYPE``.
    """
    config = load_config(config_path)
    dataset_id = require_dataset_id(config, platform="twitter")
    ensure_dataset_manifest(
        TwitterStorageManager(StorageStage.RAW, dataset_id),
        "twitter",
        dataset_id,
        config,
        config_path,
    )
    storage = TwitterStorageManager(StorageStage.RAW, dataset_id)

    ingestion_params = config["ingestion_params"]
    sync_tasks = build_sync_tasks(ingestion_params)
    record_types = config["record_types"]
    if not isinstance(record_types, list) or TWEETS_RECORD_TYPE not in record_types:
        raise ValueError(f"Unsupported record types for checkpoint sync: {record_types}")
    client = init_twitter_client()

    output_dir, metadata = prepare_sync_run(
        storage,
        sync_tasks,
        run_dir_name=run_dir_name,
        init_metadata_fn=lambda ts: init_sync_metadata(config, config_path, ts, sync_tasks),
        entity_label="keywords",
    )
    sync_timestamp = str(metadata["sync_timestamp"])
    filename = storage.records_filename

    run_sync_tasks(
        client,
        ingestion_params,
        output_dir,
        storage,
        metadata,
        sync_tasks,
        sync_timestamp=sync_timestamp,
        filename=filename,
    )
    finalize_local_disk_sync(storage, output_dir, metadata)

    total_rows = metadata["row_count"]
    print(
        f"sync_records: wrote {total_rows} rows to {output_dir} (status={metadata['sync_status']})"
    )
    return output_dir


def main() -> None:
    run_sync_cli(
        sync_records_fn=sync_records,
        config_help=(
            "Ingestion YAML path relative to the repo root "
            "(e.g. data_platform/ingestion/configs/twitter/mirrorview.yaml)"
        ),
    )


if __name__ == "__main__":
    main()
