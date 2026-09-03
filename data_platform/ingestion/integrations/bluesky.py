"""Bluesky API client wrapper for data ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from data_platform.ingestion.retry import retry_bluesky_request
from lib.load_env_vars import EnvVarsContainer

if TYPE_CHECKING:
    from atproto import Client

API_MAX_LIMIT = 100

POSTS_RECORD_TYPE = "app.bsky.feed.post"

BLUESKY_PUBLIC_APPVIEW = "https://api.bsky.app"


@dataclass(frozen=True)
class BlueskyFetchResult:
    """Holds the rows collected for a keyword and the per-task stats produced by the fetch."""

    rows: list[dict[str, Any]]
    stats: dict[str, Any]


class BlueskyClient:
    """Wraps the atproto Client for Bluesky keyword search ingestion."""

    def __init__(self, client: Client | None = None) -> None:
        """Initialize from an optional existing Client, otherwise from environment vars.

        If ``BLUESKY_HANDLE`` and ``BLUESKY_PASSWORD`` are both set, log in to the
        default personal data server (PDS). If both are unset, use the public AppView
        host, which lets you call ``searchPosts`` without an account.
        """
        self._client = client if client is not None else _init_bluesky_client()

    @staticmethod
    def _resolve_search_author(ingestion_params: dict[str, Any]) -> str | None:
        """Return the author_filter value from ingestion_params when it is non-empty, otherwise return None."""
        author = ingestion_params.get("author_filter")
        if author:
            return author
        return None

    @retry_bluesky_request()
    def _search_posts_page(
        self,
        ingestion_params: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ) -> Any:
        """Fetch one page of searchPosts results, scoped to one author when author_filter is set."""
        base_params = {
            "q": query,
            "limit": page_limit,
            "sort": ingestion_params.get("sort", "latest"),
        }
        if cursor:
            base_params["cursor"] = cursor
        author = self._resolve_search_author(ingestion_params)
        if author:
            return self._client.app.bsky.feed.search_posts(
                params={**base_params, "author": author},  # type: ignore[arg-type]
            )
        return self._client.app.bsky.feed.search_posts(params=base_params)  # type: ignore[arg-type]

    def _posts_to_rows(self, response: Any, sync_timestamp: str) -> list[dict[str, Any]]:
        """Convert a searchPosts API response to dictionary rows for CSV storage."""
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

    def fetch_posts_for_keyword(
        self,
        ingestion_params: dict[str, Any],
        query: str,
        *,
        task_id: str,
        sync_timestamp: str,
        remaining_posts: int | None = None,
    ) -> BlueskyFetchResult:
        """Call searchPosts repeatedly until the configured row limit is reached or the results are exhausted."""
        from data_platform.ingestion.sync_checkpoint import resolve_limit_per_task

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
            return BlueskyFetchResult(rows=[], stats=stats)

        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        pages_fetched = 0
        hits_total: int | None = None

        while len(rows) < target:
            page_limit = min(target - len(rows), API_MAX_LIMIT)
            response = self._search_posts_page(
                ingestion_params,
                query,
                page_limit=page_limit,
                cursor=cursor,
            )
            if pages_fetched == 0:
                hits_total = response.hits_total
            page_rows = self._posts_to_rows(response, sync_timestamp)
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
        return BlueskyFetchResult(rows=rows, stats=stats)


def _init_bluesky_client() -> Client:
    """Return an atproto Client for Bluesky keyword search.

    When ``BLUESKY_HANDLE`` and ``BLUESKY_PASSWORD`` are both set, log in to the default
    personal data server (PDS). If both are unset, use the public AppView host, which
    lets you call ``searchPosts`` without an account.
    """
    from atproto import Client

    handle = EnvVarsContainer.get_env_var("BLUESKY_HANDLE", required=False).strip()
    password = EnvVarsContainer.get_env_var("BLUESKY_PASSWORD", required=False).strip()
    if bool(handle) != bool(password):
        raise ValueError(
            "BLUESKY_HANDLE and BLUESKY_PASSWORD must both be set, or both be unset. "
            "When both are unset, keyword search uses the public Bluesky API at "
            f"{BLUESKY_PUBLIC_APPVIEW}."
        )
    if handle and password:
        client = Client()
        client.login(handle, password)
        return client
    return Client(BLUESKY_PUBLIC_APPVIEW)
