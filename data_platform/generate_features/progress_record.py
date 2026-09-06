"""Schema of the ``progress.jsonl`` lines a campaign feature appends after each durable batch."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field

PROGRESS_EVENT_BATCH = "batch"
PERCENT_TOLERANCE = 1e-9


class ProgressRecord(BaseModel):
    """One validated batch progress line.

    The first twelve fields are the watcher-ready counters. The remaining
    fields are the ones the Step 5 writer already appended and are kept so
    the line stays a superset of the earlier shape.
    """

    model_config = ConfigDict(extra="forbid")

    campaign_id: str = Field(min_length=1)
    feature: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    recorded_at: str = Field(min_length=1)
    part_index: int = Field(ge=0)
    batch_row_count: int = Field(ge=1)
    durable_row_total: int = Field(ge=1)
    expected_row_total: int = Field(ge=1)
    percent_complete: float = Field(ge=0.0, le=1.0)
    last_source_record_id: str = Field(min_length=1)
    manifest_sha256: str = Field(min_length=1)
    active_openai_batch_id: str | None
    ts: str | None = None
    event: str = PROGRESS_EVENT_BATCH
    key: str | None = None
    row_count: int | None = None
    sha256: str | None = None
    provider_batch_ids: list[str] | None = None
    rows_total: int | None = None
    batches_total: int | None = None


def parse_batch_records(lines: Iterable[str]) -> list[ProgressRecord]:
    raise NotImplementedError


def latest_batch_record(records: Sequence[ProgressRecord]) -> ProgressRecord | None:
    raise NotImplementedError
