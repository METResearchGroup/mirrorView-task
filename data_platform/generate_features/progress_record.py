"""Schema of the ``progress.jsonl`` lines a campaign feature appends after each durable batch."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

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

    @model_validator(mode="after")
    def _totals_agree(self) -> ProgressRecord:
        expected_run_id = f"{self.campaign_id}:{self.feature}"
        if self.run_id != expected_run_id:
            raise ValueError(f"run_id {self.run_id!r} is not {expected_run_id!r}")
        if self.durable_row_total < self.batch_row_count:
            raise ValueError(
                f"durable_row_total {self.durable_row_total} is below "
                f"batch_row_count {self.batch_row_count}"
            )
        expected_percent = self.durable_row_total / self.expected_row_total
        if not math.isclose(self.percent_complete, expected_percent, abs_tol=PERCENT_TOLERANCE):
            raise ValueError(
                f"percent_complete {self.percent_complete} is not "
                f"durable_row_total / expected_row_total = {expected_percent}"
            )
        return self


def parse_batch_records(lines: Iterable[str]) -> list[ProgressRecord]:
    """Validate the ``batch`` lines of ``progress.jsonl`` and skip every other event.

    Raises
    ------
    ValueError
        Naming the one-based line number, when a batch line is not valid JSON
        or fails ``ProgressRecord`` validation.
    """
    records: list[ProgressRecord] = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"progress line {number} is not JSON: {error}") from error
        if payload.get("event", PROGRESS_EVENT_BATCH) != PROGRESS_EVENT_BATCH:
            continue
        try:
            records.append(ProgressRecord.model_validate(payload))
        except ValidationError as error:
            raise ValueError(f"progress line {number} is not a valid batch record: {error}") from error
    return records


def latest_batch_record(records: Sequence[ProgressRecord]) -> ProgressRecord | None:
    """Return the record with the largest ``durable_row_total``, or None when there are none."""
    if not records:
        return None
    return max(records, key=lambda record: record.durable_row_total)
