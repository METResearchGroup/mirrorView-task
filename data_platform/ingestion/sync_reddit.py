"""Sync Reddit comments from YAML config to raw records storage.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_reddit.py \\
        --config data_platform/ingestion/configs/reddit/mirrorview.yaml

Automatically resumes the most recent in-progress run for the dataset, or starts a new one.
Pin a specific run to resume with --run-dir:

    PYTHONPATH=. uv run python data_platform/ingestion/sync_reddit.py \\
        --config data_platform/ingestion/configs/reddit/mirrorview.yaml \\
        --run-dir 2026_05_30-12:00:00

Ingestion YAML must include `dataset_id` (e.g. reddit_<uuid>).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import praw
import praw.models
import prawcore.exceptions
from praw.models.comment_forest import CommentForest

from data_platform.ingestion.retry import retry_reddit_request
from data_platform.ingestion.sync_checkpoint import (
    COMMENTS_DEDUPE_POLICY_KEY,
    DEDUPE_POLICY_KEY,
    TaskStatus,
    build_base_sync_metadata,
    ensure_dataset_manifest,
    finalize_local_disk_sync,
    increment_duplicate_skip_counters,
    mark_task_completed,
    mark_task_failed,
    mark_task_in_progress,
    parse_max_comments,
    prepare_sync_run,
    require_dataset_id,
    resolve_dedupe_policy,
    resolve_limit_per_task,
    run_checkpointed_sync,
    run_sync_cli,
)
from data_platform.ingestion.sync_clients import init_reddit_client
from data_platform.utils.config_paths import load_yaml_config
from data_platform.utils.deduplication import (
    DedupeConfig,
    DedupeSession,
    policy_includes_prior_runs,
)
from data_platform.utils.storage import RedditStorageManager, StorageStage

COMMENTS_RECORD_TYPE = "reddit.comment"
DEFAULT_LISTING = "hot"
VALID_LISTING_TIME_FILTERS = frozenset({"all", "day", "hour", "month", "week", "year"})

logger = logging.getLogger(__name__)


def is_eligible_comment(comment: praw.models.Comment, min_body_length: int) -> bool:
    """Return True if a comment passes stickied/mod/length filters."""
    if comment.stickied:
        return False
    if comment.distinguished is not None:
        return False
    if len((comment.body or "").strip()) < min_body_length:
        return False
    return True


def comment_to_row(
    comment: praw.models.Comment,
    sync_timestamp: str,
) -> dict[str, Any]:
    """Normalize a PRAW Comment to a flat dict matching the CSV schema.

    The row has ``comment_fullname``, ``author``, ``body``, ``created_at``,
    and ``sync_timestamp``. ``created_at`` is UTC ISO-8601 from the comment
    unix time.
    """
    author = "[deleted]" if comment.author is None else str(comment.author)
    created_at = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat()
    return {
        "comment_fullname": comment.name,
        "author": author,
        "body": comment.body,
        "created_at": created_at,
        "sync_timestamp": sync_timestamp,
    }


def _has_more_comments(comments_forest: CommentForest) -> bool:
    return any(isinstance(comment, praw.models.MoreComments) for comment in comments_forest)


def _expand_more_comments(comments_forest: CommentForest) -> None:
    """Fetch MoreComments batches until none remain or expansion stalls."""
    while _has_more_comments(comments_forest):
        previous_len = len(comments_forest)
        comments_forest.replace_more(limit=0)
        if len(comments_forest) == previous_len:
            break


def _walk_comments_in_order(
    comments_forest: CommentForest,
) -> Iterator[praw.models.Comment]:
    """Yield comments in Reddit default display order via depth-first walk."""
    comments_forest.replace_more(limit=0)
    _expand_more_comments(comments_forest)

    idx = 0
    while idx < len(comments_forest):
        if _has_more_comments(comments_forest):
            _expand_more_comments(comments_forest)

        if idx >= len(comments_forest):
            break

        comment = comments_forest[idx]
        idx += 1
        if isinstance(comment, praw.models.MoreComments):
            continue

        yield comment
        if comment.replies:
            yield from _walk_comments_in_order(comment.replies)


def fetch_post_comments(
    submission: praw.models.Submission,
    max_comments: int,
    min_body_length: int,
    sync_timestamp: str,
) -> list[dict[str, Any]]:
    """Collect up to max_comments eligible comments for a submission.

    The function skips stickied comments, distinguished comments, and
    comments shorter than min_body_length. Comment rows do not include depth
    or rank.
    """
    rows: list[dict[str, Any]] = []
    submission.comments.replace_more(limit=0)

    for comment in _walk_comments_in_order(submission.comments):
        if len(rows) >= max_comments:
            break
        if not is_eligible_comment(comment, min_body_length):
            continue
        rows.append(comment_to_row(comment, sync_timestamp))

    return rows


@dataclass(frozen=True)
class RedditTask:
    task_id: str
    subreddit: str


@dataclass(frozen=True)
class SubredditFetchResult:
    comment_rows: list[dict[str, Any]]
    stats: dict[str, Any]


def _normalize_subreddit_key(subreddit: str) -> str:
    return subreddit.removeprefix("r/").lower()


def build_sync_tasks(ingestion_params: dict[str, Any]) -> list[RedditTask]:
    """Return sync tasks keyed by subreddit for checkpointing."""
    subreddits = ingestion_params.get("subreddits")
    if not isinstance(subreddits, list) or not subreddits:
        raise ValueError("ingestion_params must include 'subreddits' as a non-empty list")

    items: list[RedditTask] = []
    seen_task_ids: set[str] = set()
    for subreddit in subreddits:
        if not isinstance(subreddit, str) or not subreddit.strip():
            raise ValueError("ingestion_params.subreddits entries must be non-empty strings")
        normalized_subreddit = subreddit.strip().removeprefix("r/")
        task_id = _normalize_subreddit_key(normalized_subreddit)
        if task_id in seen_task_ids:
            raise ValueError(
                f"Duplicate subreddit task_id after normalization: {task_id!r}"
            )
        seen_task_ids.add(task_id)
        items.append(RedditTask(task_id=task_id, subreddit=normalized_subreddit))
    return items


def _resolve_listing_time_filter(ingestion_params: dict[str, Any], listing: str) -> str | None:
    raw = ingestion_params.get("listing_time_filter")
    if raw is None:
        return None
    if listing != "top":
        raise ValueError("ingestion_params.listing_time_filter is only valid when listing is 'top'")
    time_filter = str(raw)
    if time_filter not in VALID_LISTING_TIME_FILTERS:
        raise ValueError(f"Unsupported ingestion_params.listing_time_filter value: {time_filter!r}")
    return time_filter


def _get_subreddit_listing(
    subreddit_obj: praw.models.Subreddit,
    listing: str,
    limit: int,
    *,
    time_filter: str | None = None,
) -> list[praw.models.Submission]:
    if listing == "new":
        return list(subreddit_obj.new(limit=limit))
    if listing == "top":
        kwargs: dict[str, Any] = {"limit": limit}
        if time_filter is not None:
            kwargs["time_filter"] = time_filter
        return list(subreddit_obj.top(**kwargs))
    if listing == "rising":
        return list(subreddit_obj.rising(limit=limit))
    if listing != "hot":
        raise ValueError(f"Unsupported ingestion_params.listing value: {listing!r}")
    return list(subreddit_obj.hot(limit=limit))


@retry_reddit_request()
def _fetch_subreddit_page(
    reddit: praw.Reddit,
    subreddit: str,
    listing: str,
    limit: int,
    *,
    time_filter: str | None = None,
) -> list[praw.models.Submission]:
    return _get_subreddit_listing(
        reddit.subreddit(subreddit), listing, limit, time_filter=time_filter
    )


def fetch_records_for_subreddit(
    reddit: praw.Reddit,
    ingestion_params: dict[str, Any],
    subreddit: str,
    *,
    sync_timestamp: str,
) -> SubredditFetchResult:
    """Fetch comments for a single subreddit by walking listing submissions."""
    limit = resolve_limit_per_task(ingestion_params)
    listing = str(ingestion_params.get("listing", DEFAULT_LISTING))
    listing_time_filter = _resolve_listing_time_filter(ingestion_params, listing)
    comments_per_post = int(ingestion_params.get("comments_per_post", 100))
    min_comment_body_length = int(ingestion_params.get("min_comment_body_length", 30))

    try:
        submissions = _fetch_subreddit_page(
            reddit, subreddit, listing, limit, time_filter=listing_time_filter
        )
    except prawcore.exceptions.NotFound:
        logger.warning("Subreddit not found: %s", subreddit)
        return SubredditFetchResult(
            comment_rows=[],
            stats={
                "subreddit": subreddit,
                "listing": listing,
                "listing_time_filter": listing_time_filter,
                "limit_per_subreddit": limit,
                "submissions_scanned": 0,
                "comments_collected": 0,
            },
        )

    comment_rows: list[dict[str, Any]] = []
    for post in submissions:
        try:
            comment_rows.extend(
                fetch_post_comments(
                    post,
                    max_comments=comments_per_post,
                    min_body_length=min_comment_body_length,
                    sync_timestamp=sync_timestamp,
                )
            )
        except Exception:
            logger.warning(
                "Failed to fetch comments for post %s in r/%s",
                post.id,
                subreddit,
                exc_info=True,
            )

    return SubredditFetchResult(
        comment_rows=comment_rows,
        stats={
            "subreddit": subreddit,
            "listing": listing,
            "listing_time_filter": listing_time_filter,
            "limit_per_subreddit": limit,
            "submissions_scanned": len(submissions),
            "comments_collected": len(comment_rows),
        },
    )


def _initial_task_progress(task: RedditTask) -> dict[str, Any]:
    return {
        "status": TaskStatus.PENDING.value,
        "kind": "reddit",
        "subreddit": task.subreddit,
        "comments_collected": 0,
        "last_error": None,
    }


def init_sync_metadata(
    config: dict[str, Any],
    config_path: Path,
    sync_timestamp: str,
    sync_tasks: list[RedditTask],
) -> dict[str, Any]:
    return build_base_sync_metadata(
        config,
        config_path,
        sync_timestamp,
        sync_tasks,
        task_progress_builder=_initial_task_progress,
    )


def _resolve_reddit_dedupe_policy(
    ingestion_params: dict[str, Any],
    type_key: str,
) -> object:
    if type_key in ingestion_params:
        return resolve_dedupe_policy(
            {**ingestion_params, DEDUPE_POLICY_KEY: ingestion_params[type_key]}
        )
    return resolve_dedupe_policy(ingestion_params)


def _open_reddit_dedupe_sessions(
    storage: RedditStorageManager,
    output_dir: Path,
    ingestion_params: dict[str, Any],
    comments_filename: str,
) -> DedupeSession:
    comment_dedupe_session = DedupeSession(
        DedupeConfig(
            id_column="comment_fullname",
            filename=comments_filename,
        )
    )
    if policy_includes_prior_runs(
        _resolve_reddit_dedupe_policy(ingestion_params, COMMENTS_DEDUPE_POLICY_KEY)
    ):
        comment_dedupe_session.load_seen_ids_from_all_runs(storage)
    else:
        comment_dedupe_session.load_seen_ids(storage, output_dir)
    return comment_dedupe_session


def _append_subreddit_deduped_rows(
    storage: RedditStorageManager,
    output_dir: Path,
    metadata: dict[str, Any],
    comment_rows: list[dict[str, Any]],
    comment_dedupe_session: DedupeSession,
    comments_filename: str,
) -> int:
    if comment_rows:
        comment_result = storage.append_deduped_records(
            comment_rows,
            output_dir,
            dedupe_session=comment_dedupe_session,
            filename=comments_filename,
        )
        increment_duplicate_skip_counters(
            metadata,
            record_type=COMMENTS_RECORD_TYPE,
            skipped=comment_result.skipped,
        )
    comment_count = len(comment_dedupe_session.seen_ids)
    metadata["row_count"] = comment_count
    return comment_count


def run_sync_tasks(
    reddit: praw.Reddit,
    ingestion_params: dict[str, Any],
    output_dir: Path,
    storage: RedditStorageManager,
    metadata: dict[str, Any],
    sync_tasks: list[RedditTask],
) -> None:
    """Run the checkpointed subreddit loop and write comments.

    Filenames come from ``storage.records_filename`` so the suffix matches the
    dataset format.
    """
    max_comments_int = parse_max_comments(ingestion_params)
    sync_timestamp = str(metadata["sync_timestamp"])
    comments_filename = storage.records_filename

    comment_dedupe_session = _open_reddit_dedupe_sessions(
        storage,
        output_dir,
        ingestion_params,
        comments_filename,
    )
    print(
        "sync_records: loaded "
        f"{len(comment_dedupe_session.seen_ids)} prior comment IDs for dedupe"
    )

    def process_task(task: RedditTask, entry: dict[str, Any]) -> None:
        mark_task_in_progress(entry, storage, output_dir, metadata)

        try:
            fetch_result = fetch_records_for_subreddit(
                reddit,
                ingestion_params,
                task.subreddit,
                sync_timestamp=sync_timestamp,
            )
        except Exception as exc:  # noqa: BLE001 — record and continue
            mark_task_failed(entry, exc, task.task_id, storage, output_dir, metadata)
            return

        comment_count = _append_subreddit_deduped_rows(
            storage,
            output_dir,
            metadata,
            fetch_result.comment_rows,
            comment_dedupe_session,
            comments_filename,
        )
        mark_task_completed(
            entry,
            storage,
            output_dir,
            metadata,
            entry_updates={
                "comments_collected": fetch_result.stats["comments_collected"],
            },
        )

        print(
            f"sync_records: {task.task_id} -> "
            f"{fetch_result.stats['comments_collected']} comments "
            f"(total comments={comment_count})"
        )

    run_checkpointed_sync(
        sync_tasks,
        metadata,
        storage,
        output_dir,
        record_cap=max_comments_int,
        tqdm_desc="Syncing subreddits",
        process_task=process_task,
    )


load_config = load_yaml_config


def sync_records(
    config_path: Path,
    *,
    run_dir_name: str | None = None,
) -> Path:
    """Fetch Reddit records per config and write raw records plus metadata.

    Creates the dataset manifest first so storage can read the declared format.
    """
    config = load_config(config_path)
    dataset_id = require_dataset_id(config, platform="reddit")
    ensure_dataset_manifest(
        RedditStorageManager(StorageStage.RAW, dataset_id),
        "reddit",
        dataset_id,
        config,
        config_path,
    )
    storage = RedditStorageManager(StorageStage.RAW, dataset_id)

    ingestion_params = config["ingestion_params"]
    sync_tasks = build_sync_tasks(ingestion_params)
    record_types: list[str] = config["record_types"]
    if COMMENTS_RECORD_TYPE not in record_types or "reddit.post" in record_types:
        raise ValueError(f"Unsupported record types for checkpoint sync: {record_types}")

    reddit = init_reddit_client()

    output_dir, metadata = prepare_sync_run(
        storage,
        sync_tasks,
        run_dir_name=run_dir_name,
        init_metadata_fn=lambda ts: init_sync_metadata(config, config_path, ts, sync_tasks),
        entity_label="subreddits",
    )

    run_sync_tasks(
        reddit,
        ingestion_params,
        output_dir,
        storage,
        metadata,
        sync_tasks,
    )
    finalize_local_disk_sync(storage, output_dir, metadata)

    print(
        f"sync_records: wrote {metadata['row_count']} comments to {output_dir} "
        f"(status={metadata['sync_status']})"
    )
    return output_dir


def main() -> None:
    run_sync_cli(
        sync_records_fn=sync_records,
        config_help=(
            "Ingestion YAML path relative to the repo root "
            "(e.g. data_platform/ingestion/configs/reddit/mirrorview.yaml)"
        ),
    )


if __name__ == "__main__":
    main()
