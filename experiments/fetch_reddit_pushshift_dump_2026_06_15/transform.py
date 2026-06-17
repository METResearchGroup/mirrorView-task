"""Map filtered Pushshift comments to mirrorview row shape."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from experiments.fetch_reddit_pushshift_dump_2026_06_15.models import (
    MirrorviewCommentRow,
    PushshiftCommentRaw,
)

MIRRORVIEW_TZ = ZoneInfo("America/Chicago")
MAX_DEPTH_WALK = 20


def _format_created_utc(unix_ts: int) -> str:
    dt = datetime.fromtimestamp(unix_ts, tz=MIRRORVIEW_TZ)
    formatted = dt.strftime("%Y-%m-%d %H:%M:%S%z")
    if len(formatted) >= 5 and formatted[-5] in {"+", "-"} and formatted[-3] != ":":
        return f"{formatted[:-2]}:{formatted[-2:]}"
    return formatted


def _synthesize_permalink(comment: PushshiftCommentRaw) -> str:
    post_id = comment.link_id.removeprefix("t3_")
    return (
        f"/r/{comment.subreddit}/comments/{post_id}/_/{comment.id}/"
    )


def compute_depth(
    comment: PushshiftCommentRaw,
    parent_lookup: dict[str, PushshiftCommentRaw],
) -> int:
    """Walk parent_id chain within filtered comments; top-level replies depth=0."""

    if comment.parent_id.startswith("t3_"):
        return 0

    depth = 0
    current_parent = comment.parent_id
    seen: set[str] = set()

    for _ in range(MAX_DEPTH_WALK):
        if current_parent.startswith("t3_"):
            return depth
        if current_parent in seen:
            return depth
        seen.add(current_parent)

        parent = parent_lookup.get(current_parent.removeprefix("t1_"))
        if parent is None:
            return depth

        depth += 1
        current_parent = parent.parent_id

    return depth


def to_mirrorview_row(
    comment: PushshiftCommentRaw,
    *,
    depth: int,
    sync_timestamp: str,
) -> MirrorviewCommentRow:
    """Convert a filtered Pushshift comment to mirrorview column shape."""

    permalink = comment.permalink or _synthesize_permalink(comment)
    if not permalink.startswith("/"):
        permalink = f"/{permalink.lstrip('/')}"

    return MirrorviewCommentRow(
        post_reddit_id=comment.link_id.removeprefix("t3_"),
        post_reddit_fullname=comment.link_id,
        subreddit=comment.subreddit,
        comment_id=comment.id,
        comment_fullname=f"t1_{comment.id}",
        parent_id=comment.parent_id,
        author=comment.author,
        body=comment.body,
        score=comment.score,
        created_utc=_format_created_utc(comment.created_utc),
        permalink=permalink,
        depth=depth,
        comment_rank=0,
        sync_timestamp=sync_timestamp,
    )


def build_mirrorview_rows(
    comments: list[PushshiftCommentRaw],
    sync_timestamp: str,
) -> list[MirrorviewCommentRow]:
    """Build mirrorview rows with depth computed from in-file parent lookup."""

    parent_lookup = {c.id: c for c in comments}
    return [
        to_mirrorview_row(
            comment,
            depth=compute_depth(comment, parent_lookup),
            sync_timestamp=sync_timestamp,
        )
        for comment in comments
    ]
