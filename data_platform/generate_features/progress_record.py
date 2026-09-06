"""Schema of the ``progress.jsonl`` lines a campaign feature appends after each durable batch."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

PROGRESS_EVENT_BATCH = "batch"


class ProgressRecord(BaseModel):
    """One validated batch progress line."""


def parse_batch_records(lines: Iterable[str]) -> list[ProgressRecord]:
    raise NotImplementedError


def latest_batch_record(records: Sequence[ProgressRecord]) -> ProgressRecord | None:
    raise NotImplementedError
