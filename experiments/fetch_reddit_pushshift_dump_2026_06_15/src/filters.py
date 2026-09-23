"""Apply the experiment's subreddit and text-quality filters."""

from __future__ import annotations

from experiments.fetch_reddit_pushshift_dump_2026_06_15.src.config import (
    DELETED_TOKENS,
    MAX_BODY_LEN,
    MIN_BODY_LEN,
)
from experiments.fetch_reddit_pushshift_dump_2026_06_15.src.models import (
    PushshiftCommentRaw,
    TARGET_SUBREDDITS,
)

AUTOMODERATOR = "AutoModerator"


def passes_filters(comment: PushshiftCommentRaw) -> bool:
    """Return whether a comment should be sent to Perspective for scoring.

    The filter keeps only target-subreddit comments with usable author and body
    text, and drops records whose body length falls outside the experiment's
    scoring window.
    """

    if not comment.id or not comment.link_id or not comment.body:
        return False

    if comment.subreddit not in TARGET_SUBREDDITS:
        return False

    author = (comment.author or "").strip()
    if not author or author in DELETED_TOKENS or author == AUTOMODERATOR:
        return False

    body = comment.body.strip()
    if body in DELETED_TOKENS:
        return False

    body_len = len(body)
    if body_len < MIN_BODY_LEN or body_len > MAX_BODY_LEN:
        return False

    return True
