"""Unit tests for Pushshift -> mirrorview transforms."""

from experiments.fetch_reddit_pushshift_dump_2026_06_15.models import PushshiftCommentRaw
from experiments.fetch_reddit_pushshift_dump_2026_06_15.transform import (
    build_mirrorview_rows,
    compute_depth,
)


def _comment(**overrides) -> PushshiftCommentRaw:
    base = {
        "id": "child1",
        "author": "user1",
        "link_id": "t3_post1",
        "parent_id": "t3_post1",
        "subreddit": "politics",
        "body": "Top-level comment with enough length.",
        "score": 1,
        "created_utc": 1_700_000_000,
        "permalink": "/r/politics/comments/post1/title/child1/",
    }
    base.update(overrides)
    return PushshiftCommentRaw.model_validate(base)


def test_top_level_depth_is_zero():
    comment = _comment()
    assert compute_depth(comment, {comment.id: comment}) == 0


def test_nested_depth_counts_parent_chain():
    parent = _comment(id="parent1", parent_id="t3_post1")
    child = _comment(id="child2", parent_id="t1_parent1")
    lookup = {parent.id: parent, child.id: child}
    assert compute_depth(child, lookup) == 1


def test_build_mirrorview_rows_shape():
    comment = _comment()
    rows = build_mirrorview_rows([comment], sync_timestamp="2026_06_15-12:00:00")
    assert len(rows) == 1
    row = rows[0]
    assert row.post_reddit_fullname == "t3_post1"
    assert row.post_reddit_id == "post1"
    assert row.comment_fullname == "t1_child1"
    assert row.comment_rank == 0
    assert row.depth == 0
    assert row.sync_timestamp == "2026_06_15-12:00:00"
    assert "-05:00" in row.created_utc or "-06:00" in row.created_utc
