"""Sync Bluesky posts from YAML config to raw CSV storage.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \\
        --config data_platform/ingestion/configs/bluesky/mirrorview.yaml

Automatically resumes the most recent in-progress run for the dataset, or starts a new one.
Pin a specific run to resume with --run-dir:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \\
        --config data_platform/ingestion/configs/bluesky/mirrorview_scale.yaml \\
        --run-dir 2026_05_30-12:00:00

Ingestion YAML must include `dataset_id` (e.g. bluesky_<uuid>).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from data_platform.ingestion.query_terms import quote_query_term
from data_platform.ingestion.retry import retry_bluesky_request
from data_platform.ingestion.sync_checkpoint import (
    TaskStatus,
    build_base_sync_metadata,
    ensure_dataset_manifest,
    finalize_local_disk_sync,
    mark_task_completed,
    mark_task_failed,
    mark_task_in_progress,
    parse_max_posts,
    prepare_sync_run,
    require_dataset_id,
    resolve_limit_per_task,
    run_checkpointed_sync,
    run_sync_cli,
)
from data_platform.ingestion.sync_clients import init_bluesky_client
from data_platform.utils.config_paths import load_yaml_config
from data_platform.utils.deduplication import (
    DedupeConfig,
    DedupeSession,
    policy_includes_prior_runs,
)
from data_platform.utils.storage import BlueskyStorageManager, StorageStage

if TYPE_CHECKING:
    from atproto import Client

API_MAX_LIMIT = 100

POSTS_RECORD_TYPE = "app.bsky.feed.post"


@dataclass(frozen=True)
class BlueskyTask:
    """One checkpointed search unit: a stable task ID and the API query string."""

    task_id: str
    query: str


def build_sync_tasks(ingestion_params: dict[str, Any]) -> list[BlueskyTask]:
    """Build one checkpoint task per entry in ingestion_params.keywords."""
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


def _posts_to_rows(response: Any, sync_timestamp: str) -> list[dict[str, Any]]:
    """Map a searchPosts API response to flat dict rows for CSV storage.

    Parameters
    ----------
    response
        Bluesky searchPosts API response.
    sync_timestamp
        Run timestamp written onto each raw row.
    """
    rows: list[dict[str, Any]] = []
    for post in response.posts:
        rkey = post.uri.split("/")[-1]
        rows.append(
            {
                "uri": post.uri,
                "url": f"https://bsky.app/profile/{post.author.handle}/post/{rkey}",
                "author_handle": post.author.handle,
                "text": post.record.text,  # type: ignore[union-attr]
                "created_at": post.record.created_at,  # type: ignore[union-attr]
                "like_count": post.like_count,
                "repost_count": post.repost_count,
                "reply_count": post.reply_count,
                "quote_count": post.quote_count,
                "sync_timestamp": sync_timestamp,
            }
        )
    return rows


def _resolve_search_author(ingestion_params: dict[str, Any]) -> str | None:
    """Return ingestion_params author_filter when non-empty, else None."""
    author = ingestion_params.get("author_filter")
    if author:
        return author
    return None


@retry_bluesky_request()
def _search_posts_page(
    client: Client,
    ingestion_params: dict[str, Any],
    query: str,
    *,
    page_limit: int,
    cursor: str | None = None,
) -> Any:
    """Fetch one page of searchPosts results, optionally scoped to one author."""
    base_params = {
        "q": query,
        "limit": page_limit,
        "sort": ingestion_params.get("sort", "latest"),
    }
    if cursor:
        base_params["cursor"] = cursor
    author = _resolve_search_author(ingestion_params)
    if author:
        return client.app.bsky.feed.search_posts(
            params={**base_params, "author": author},  # type: ignore[arg-type]
        )
    return client.app.bsky.feed.search_posts(params=base_params)  # type: ignore[arg-type]


def fetch_posts_for_keyword(
    client: Client,
    ingestion_params: dict[str, Any],
    query: str,
    *,
    task_id: str,
    sync_timestamp: str,
    remaining_posts: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Paginate searchPosts until limit rows are collected or results are exhausted.

    Parameters
    ----------
    sync_timestamp
        Run timestamp written onto each raw row.

    Returns
    -------
    tuple[list[dict[str, Any]], dict[str, Any]]
        Rows and per-task stats (pages fetched, hits_total from the first page, etc.).
    """
    target = resolve_limit_per_task(ingestion_params)
    if remaining_posts is not None:
        target = min(target, remaining_posts)
    if target <= 0:
        stats = {
            "task_id": task_id,
            "query_len": len(query),
            "per_query_limit": target,
            "pages_fetched": 0,
            "rows_collected": 0,
            "hits_total": None,
        }
        return [], stats
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    pages_fetched = 0
    hits_total: int | None = None

    while len(rows) < target:
        page_limit = min(target - len(rows), API_MAX_LIMIT)
        response = _search_posts_page(
            client, ingestion_params, query, page_limit=page_limit, cursor=cursor
        )
        if pages_fetched == 0:
            hits_total = response.hits_total
        page_rows = _posts_to_rows(response, sync_timestamp)
        if not page_rows:
            break
        rows.extend(page_rows)
        pages_fetched += 1
        cursor = response.cursor
        if not cursor:
            break

    rows = rows[:target]
    stats = {
        "task_id": task_id,
        "query_len": len(query),
        "per_query_limit": target,
        "pages_fetched": pages_fetched,
        "rows_collected": len(rows),
        "hits_total": hits_total,
    }
    return rows, stats


def _initial_task_progress(task: BlueskyTask) -> dict[str, Any]:
    """Return the pending task-ledger entry written into run metadata at sync start."""
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
    """Build the initial metadata.json payload for a new raw run directory."""
    return build_base_sync_metadata(
        config,
        config_path,
        sync_timestamp,
        sync_tasks,
        task_progress_builder=_initial_task_progress,
    )


def run_sync_tasks(
    client: Client,
    ingestion_params: dict[str, Any],
    output_dir: Path,
    storage: BlueskyStorageManager,
    metadata: dict[str, Any],
    sync_tasks: list[BlueskyTask],
    *,
    filename: str,
) -> None:
    """Run the checkpointed keyword loop: fetch, dedupe-append, and flush metadata per task.

    Skips completed tasks on resume, stops early when max_posts is reached, and records failures
    without aborting the full run.
    """
    max_posts_int = parse_max_posts(ingestion_params)
    dedupe_session = DedupeSession(
        DedupeConfig(
            id_column="uri",
            filename=filename,
            include_prior_runs=policy_includes_prior_runs(
                ingestion_params.get("dedupe_policy")
            ),
        )
    )
    dedupe_session.warm(storage, output_dir)

    def process_task(task: BlueskyTask, entry: dict[str, Any]) -> None:
        """Fetch one keyword, persist deduped rows, and update the task ledger entry."""
        mark_task_in_progress(entry, storage, output_dir, metadata)

        remaining: int | None = None
        if max_posts_int is not None:
            remaining = max_posts_int - int(metadata["row_count"])
            if remaining <= 0:
                return

        try:
            rows, stats = fetch_posts_for_keyword(
                client,
                ingestion_params,
                task.query,
                task_id=task.task_id,
                sync_timestamp=str(metadata["sync_timestamp"]),
                remaining_posts=remaining,
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
        metadata["posts_skipped_as_duplicates"] = (
            int(metadata.get("posts_skipped_as_duplicates", 0)) + result.skipped
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
                "hits_total": stats["hits_total"],
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


def sync_records(
    config_path: Path,
    *,
    run_dir_name: str | None = None,
) -> Path:
    """Load config, prepare or resume a raw run, and sync all keyword tasks to posts.csv.

    Creates the dataset manifest on first run and returns the output run directory path.
    """
    config = load_yaml_config(config_path)
    dataset_id = require_dataset_id(config, platform="bluesky")

    # Create a temporary storage just to locate the dataset root for the manifest.
    # The manifest must exist before we create the real storage so that format is
    # read correctly (new datasets have no dataset.json yet).
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
    client = init_bluesky_client()

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
    """CLI entrypoint for sync_bluesky.py (--config, --resume, --run-dir)."""
    run_sync_cli(
        sync_records_fn=sync_records,
        config_help=(
            "Ingestion YAML path relative to the repo root "
            "(e.g. data_platform/ingestion/configs/bluesky/mirrorview.yaml)"
        ),
    )


if __name__ == "__main__":
    main()
