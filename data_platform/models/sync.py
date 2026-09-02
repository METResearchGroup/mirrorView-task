from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SyncBlueskyPostModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uri: str
    url: str
    author_handle: str
    text: str
    created_at: str
    like_count: int
    repost_count: int
    reply_count: int
    quote_count: int
    sync_timestamp: str


class SyncRedditPostModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reddit_id: str
    reddit_fullname: str
    subreddit: str
    title: str
    selftext: str
    author: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_at: str
    permalink: str
    url: str
    is_self: bool
    sync_timestamp: str


class SyncTwitterPostModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tweet_id: str
    text: str
    author_id: str
    username: str
    created_at: str
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    url: str
    keyword: str
    sync_timestamp: str


class SyncRedditCommentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    post_reddit_id: str
    post_reddit_fullname: str
    subreddit: str
    comment_id: str
    comment_fullname: str
    parent_id: str
    author: str
    body: str
    score: int
    created_at: str
    permalink: str
    depth: int
    comment_rank: int
    sync_timestamp: str


class PreprocessedBlueskyPostModel(SyncBlueskyPostModel):
    """A Bluesky post after preprocess, with shared source record id.

    Raw ingest still uses ``SyncBlueskyPostModel``. The original ``uri`` stays
    on the inherited sync model.
    """

    source_record_id: str


class PreprocessedRedditCommentModel(SyncRedditCommentModel):
    """A Reddit comment after preprocess, with original body, shared text, shared author handle, and shared source record id.

    Raw ingest still uses ``SyncRedditCommentModel``. Feature generation reads
    ``text`` from the preprocessed CSV described by this model.
    """

    text: str
    author_handle: str
    source_record_id: str


class PreprocessedTwitterPostModel(SyncTwitterPostModel):
    """A Twitter post after preprocess, with shared author handle and shared source record id.

    Raw ingest still uses ``SyncTwitterPostModel``. ``author_id`` stays on the
    inherited sync model.
    """

    author_handle: str
    source_record_id: str
