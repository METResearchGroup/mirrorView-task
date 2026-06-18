"""Pydantic schemas for the Reddit Pushshift toxicity smoke pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field

TARGET_SUBREDDITS = frozenset(
    {
        "Conservative",
        "Republican",
        "AskConservatives",
        "politics",
        "liberal",
        "democrats",
    }
)


class PushshiftCommentRaw(BaseModel):
    """Minimal Pushshift comment object parsed from one JSONL line."""

    id: str
    author: str
    link_id: str
    parent_id: str
    subreddit: str
    body: str
    score: int
    created_utc: int
    permalink: str | None = None


class CommentToScore(BaseModel):
    """Input to Perspective batch scorer."""

    comment_id: str
    text: str


class ToxicityScore(BaseModel):
    comment_id: str
    prob_toxic: float | None = None
    was_successfully_labeled: bool
    reason: str | None = None


class MirrorviewCommentRow(BaseModel):
    """Output row shape (mirrorview columns only)."""

    post_reddit_id: str
    post_reddit_fullname: str
    subreddit: str
    comment_id: str
    comment_fullname: str
    parent_id: str
    author: str
    body: str
    score: int
    created_utc: str
    permalink: str
    depth: int
    comment_rank: int = 0
    sync_timestamp: str


class HighToxicCommentRow(MirrorviewCommentRow):
    prob_toxic: float


class FileRunMetadata(BaseModel):
    source_file: str
    rows_read: int
    rows_after_filter: int
    rows_scored: int
    rows_high_toxic: int
    toxicity_threshold: float = 0.7
    skipped_scoring: bool = False
    finished_at: str


class TotalRunMetadata(BaseModel):
    files_processed: list[str] = Field(default_factory=list)
    high_toxic_by_file: dict[str, int] = Field(default_factory=dict)
    total_high_toxic: int = 0
    stop_threshold: int = 50_000
    stopped_reason: str = "files_exhausted"
