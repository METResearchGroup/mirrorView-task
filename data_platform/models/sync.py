from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SyncBlueskyPostModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uri: str
    record_id: str
    url: str
    author_handle: str
    text: str
    created_at: str
    like_count: int
    repost_count: int
    reply_count: int
    quote_count: int
    sync_timestamp: str


class SyncTwitterPostModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tweet_id: str
    record_id: str
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

    comment_fullname: str
    record_id: str
    author: str
    body: str
    created_at: str
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
