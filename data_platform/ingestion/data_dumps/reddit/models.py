"""Raw comment objects parsed from a Reddit dump JSONL line."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DumpCommentRaw(BaseModel):
    """One comment line from a Reddit dump file.

    Extra dump JSON keys are ignored. Only the fields needed to build a
    Reddit ingest comment row are kept.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    author: str
    link_id: str
    parent_id: str
    subreddit: str
    body: str
    score: int
    created_utc: int
    permalink: str | None = None
