"""Schema objects shared across Reddit toxicity pipeline stages."""

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
    """Raw Pushshift comment fields required by the pipeline."""

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
    """Scoring payload passed to the Perspective batching layer."""

    comment_id: str
    text: str


class ToxicityScore(BaseModel):
    """Perspective label outcome for one candidate comment."""

    comment_id: str
    prob_toxic: float | None = None
    was_successfully_labeled: bool
    reason: str | None = None


class MirrorviewCommentRow(BaseModel):
    """Mirrorview-compatible comment row emitted before toxicity filtering."""

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
    """Mirrorview row extended with the retained toxicity score."""

    prob_toxic: float


class FileRunMetadata(BaseModel):
    """Per-input-file processing counts and completion metadata."""

    source_file: str
    rows_read: int
    rows_after_filter: int
    rows_scored: int
    rows_high_toxic: int
    toxicity_threshold: float = 0.7
    skipped_scoring: bool = False
    finished_at: str


class TotalRunMetadata(BaseModel):
    """Aggregated run state across all processed input files."""

    files_processed: list[str] = Field(default_factory=list)
    high_toxic_by_file: dict[str, int] = Field(default_factory=dict)
    total_high_toxic: int = 0
    stop_threshold: int = 50_000
    stopped_reason: str = "files_exhausted"
