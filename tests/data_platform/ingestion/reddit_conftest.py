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
        "record_types": [sync_reddit.COMMENTS_RECORD_TYPE],
        "ingestion_params": {
            "comments_dedupe_policy": ["current_run", PRIOR_RUN_POLICY],
            "subreddits": ["AlphaSub", "BetaSub"],
            "listing": "hot",
            "limit_per_task": 2,
            "comments_per_post": 5,
            "min_comment_body_length": 10,
        },
    }


def mock_comment_row(comment_fullname: str) -> dict[str, Any]:
    return {
        "comment_fullname": comment_fullname,
        "record_id": f"reddit_{comment_fullname}",
        "author": "user",
        "body": "comment text long enough",
        "created_at": "2026-05-30T00:00:00+00:00",
        "sync_timestamp": "2026_05_30-10:00:00",
    }
