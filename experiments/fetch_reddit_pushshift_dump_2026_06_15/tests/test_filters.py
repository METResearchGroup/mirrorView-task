"""Unit tests for Pushshift comment filters."""

from experiments.fetch_reddit_pushshift_dump_2026_06_15.filters import passes_filters
from experiments.fetch_reddit_pushshift_dump_2026_06_15.models import PushshiftCommentRaw


def _comment(**overrides) -> PushshiftCommentRaw:
    base = {
        "id": "abc123",
        "author": "user1",
        "link_id": "t3_post1",
        "parent_id": "t3_post1",
        "subreddit": "politics",
        "body": "This is a valid comment body here.",
        "score": 3,
        "created_utc": 1_700_000_000,
    }
    base.update(overrides)
    return PushshiftCommentRaw.model_validate(base)


def test_keeps_valid_comment():
    assert passes_filters(_comment()) is True


def test_drops_wrong_subreddit():
    assert passes_filters(_comment(subreddit="news")) is False


def test_drops_deleted_author():
    assert passes_filters(_comment(author="[deleted]")) is False


def test_drops_automoderator():
    assert passes_filters(_comment(author="AutoModerator")) is False


def test_drops_short_body():
    assert passes_filters(_comment(body="too short")) is False


def test_drops_long_body():
    assert passes_filters(_comment(body="x" * 301)) is False
