"""Tests for Reddit dump comment read, filter, and ingest-model mapping."""

from __future__ import annotations

from data_platform.ingestion.data_dumps.reddit.filters import keep_dump_comment
from data_platform.ingestion.data_dumps.reddit.reader import iter_dump_comments
from data_platform.ingestion.data_dumps.reddit.transform import dump_comment_to_sync_row
from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw

_ = (
    DumpCommentRaw,
    dump_comment_to_sync_row,
    iter_dump_comments,
    keep_dump_comment,
)
