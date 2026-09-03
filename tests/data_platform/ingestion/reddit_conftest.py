from __future__ import annotations

from typing import Any

from data_platform.ingestion import sync_reddit
from data_platform.utils.deduplication import PRIOR_RUN_POLICY
from tests.data_platform.constants import VALID_REDDIT_DATASET_ID


def minimal_reddit_sync_config() -> dict[str, Any]:
    return {
        "dataset_id": VALID_REDDIT_DATASET_ID,
        "name": "test",
        "description": "test",
        "date": "2026-05-31",
        "record_types": [sync_reddit.COMMENTS_RECORD_TYPE, sync_reddit.POSTS_RECORD_TYPE],
        "ingestion_params": {
            "comments_dedupe_policy": ["current_run", PRIOR_RUN_POLICY],
            "posts_dedupe_policy": ["current_run", PRIOR_RUN_POLICY],
            "subreddits": ["AlphaSub", "BetaSub"],
            "listing": "hot",
            "limit_per_task": 2,
            "comments_per_post": 5,
            "min_comment_body_length": 10,
        },
    }


def mock_comment_row(
    comment_fullname: str,
    *,
    post_reddit_id: str = "abc123",
    subreddit: str = "alphasub",
) -> dict[str, Any]:
    del post_reddit_id, subreddit
    return {
        "comment_fullname": comment_fullname,
        "record_id": f"reddit_{comment_fullname}",
        "author": "user",
        "body": "comment text long enough",
        "created_at": "2026-05-30T00:00:00+00:00",
        "sync_timestamp": "2026_05_30-10:00:00",
    }


def mock_post_row(
    reddit_fullname: str,
    *,
    subreddit: str = "alphasub",
) -> dict[str, Any]:
    reddit_id = reddit_fullname.removeprefix("t3_")
    return {
        "reddit_id": reddit_id,
        "reddit_fullname": reddit_fullname,
        "record_id": f"reddit_{reddit_fullname}",
        "subreddit": subreddit,
        "title": "title",
        "selftext": "body",
        "author": "user",
        "score": 1,
        "upvote_ratio": 0.5,
        "num_comments": 1,
        "created_at": "2026-05-30T00:00:00+00:00",
        "permalink": f"/r/{subreddit}/comments/{reddit_id}/title/",
        "url": f"https://reddit.com/r/{subreddit}/comments/{reddit_id}/title/",
        "is_self": True,
        "sync_timestamp": "2026_05_30-10:00:00",
    }
