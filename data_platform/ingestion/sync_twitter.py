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

from data_platform.ingestion.runner import (
    KeywordSyncParams,
    SyncPlatformSpec,
    effective_limit_per_keyword,
    remaining_record_budget,
    run_keyword_sync_tasks,
    sync_with_spec,
)
from data_platform.ingestion.sync_checkpoint import (
    TaskStatus,
    build_base_sync_metadata,
    run_sync_cli,
)
from data_platform.ingestion.sync_clients import init_twitter_client
from data_platform.ingestion.twitter_client import fetch_posts_for_keyword
from data_platform.utils.config_paths import load_yaml_config
from data_platform.utils.storage import TwitterStorageManager

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
    return effective_limit_per_keyword(ingestion_params, remaining)


def _remaining_post_budget(metadata: dict[str, Any], max_posts_int: int | None) -> int | None:
    return remaining_record_budget(metadata, max_posts_int)


def _validate_twitter_config(config: dict[str, Any]) -> None:
    record_types = config["record_types"]
    if not isinstance(record_types, list) or TWEETS_RECORD_TYPE not in record_types:
        raise ValueError(f"Unsupported record types for checkpoint sync: {record_types}")


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
    """Run the checkpointed keyword loop: fetch, dedupe-append, and flush metadata per task."""
    lang = str(ingestion_params.get("lang", "en"))
    exclude = list(ingestion_params.get("exclude", ["reply", "retweet", "quote"]))

    def fetch_for_task(
        fetch_client: Any,
        task: TwitterTask,
        _sync_timestamp: str,
        remaining: int | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        limit = _effective_limit_per_keyword(ingestion_params, remaining)
        return fetch_posts_for_keyword(
            fetch_client,
            task.keyword,
            limit=limit,
            lang=lang,
            exclude=exclude,
            sync_timestamp=sync_timestamp,
        )

    run_keyword_sync_tasks(
        client,
        ingestion_params,
        output_dir,
        storage,
        metadata,
        sync_tasks,
        filename=filename,
        params=KeywordSyncParams(
            id_column="tweet_id",
            record_type=TWEETS_RECORD_TYPE,
        ),
        fetch_for_task=fetch_for_task,
    )


def _twitter_run_sync_tasks(
    client: Any,
    ingestion_params: dict[str, Any],
    output_dir: Path,
    storage: TwitterStorageManager,
    metadata: dict[str, Any],
    sync_tasks: list[TwitterTask],
    *,
    config: dict[str, Any],
    config_path: Path,
) -> None:
    _ = config, config_path
    run_sync_tasks(
        client,
        ingestion_params,
        output_dir,
        storage,
        metadata,
        sync_tasks,
        sync_timestamp=str(metadata["sync_timestamp"]),
        filename=storage.records_filename,
    )


def _summarize_twitter_run(metadata: dict[str, Any], output_dir: Path) -> None:
    print(
        f"sync_records: wrote {metadata['row_count']} rows to {output_dir} "
        f"(status={metadata['sync_status']})"
    )


TWITTER_SYNC_SPEC = SyncPlatformSpec(
    platform="twitter",
    storage_cls=TwitterStorageManager,
    entity_label="keywords",
    init_client=lambda: init_twitter_client(),
    build_sync_tasks=build_sync_tasks,
    task_progress_builder=_initial_task_progress,
    validate_config=_validate_twitter_config,
    run_sync_tasks=_twitter_run_sync_tasks,
    summarize_run=_summarize_twitter_run,
)


load_config = load_yaml_config


def sync_records(
    config_path: Path,
    *,
    run_dir_name: str | None = None,
) -> Path:
    """Fetch Twitter records per config and write raw records plus metadata."""
    return sync_with_spec(
        config_path,
        run_dir_name=run_dir_name,
        spec=TWITTER_SYNC_SPEC,
        config_loader=load_config,
    )


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
