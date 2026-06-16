"""Write per-file parquet deliverables and metadata."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import OUTPUTS_DIR
from experiments.fetch_reddit_pushshift_dump_2026_06_15.models import (
    FileRunMetadata,
    HighToxicCommentRow,
    TotalRunMetadata,
)

CHICAGO = ZoneInfo("America/Chicago")


def _now_iso() -> str:
    return datetime.now(tz=CHICAGO).isoformat()


def file_output_dir(stem: str) -> Path:
    return OUTPUTS_DIR / stem


def metadata_path(stem: str) -> Path:
    return file_output_dir(stem) / "metadata.json"


def parquet_path(stem: str) -> Path:
    return file_output_dir(stem) / "high_toxic_comments.parquet"


def total_metadata_path() -> Path:
    return OUTPUTS_DIR / "total_metadata.json"


def metadata_exists(stem: str) -> bool:
    return metadata_path(stem).is_file()


def write_high_toxic_parquet(stem: str, rows: list[HighToxicCommentRow]) -> None:
    out_dir = file_output_dir(stem)
    out_dir.mkdir(parents=True, exist_ok=True)
    if rows:
        df = pd.DataFrame([row.model_dump() for row in rows])
    else:
        df = pd.DataFrame(columns=list(HighToxicCommentRow.model_fields.keys()))
    df.to_parquet(parquet_path(stem), index=False)


def write_file_metadata(stem: str, metadata: FileRunMetadata) -> None:
    out_dir = file_output_dir(stem)
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata_path(stem).write_text(metadata.model_dump_json(indent=2) + "\n")


def load_total_metadata() -> TotalRunMetadata:
    path = total_metadata_path()
    if not path.is_file():
        return TotalRunMetadata()
    return TotalRunMetadata.model_validate_json(path.read_text())


def merge_file_into_total_metadata(
    stem: str,
    rows_high_toxic: int,
    *,
    stopped_reason: str | None = None,
) -> TotalRunMetadata:
    total = load_total_metadata()
    if stem not in total.files_processed:
        total.files_processed.append(stem)
    total.high_toxic_by_file[stem] = rows_high_toxic
    total.total_high_toxic = sum(total.high_toxic_by_file.values())
    if stopped_reason is not None:
        total.stopped_reason = stopped_reason
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    total_metadata_path().write_text(total.model_dump_json(indent=2) + "\n")
    return total


def build_file_metadata(
    *,
    source_file: str,
    rows_read: int,
    rows_after_filter: int,
    rows_scored: int,
    rows_high_toxic: int,
    toxicity_threshold: float,
    skipped_scoring: bool = False,
) -> FileRunMetadata:
    return FileRunMetadata(
        source_file=source_file,
        rows_read=rows_read,
        rows_after_filter=rows_after_filter,
        rows_scored=rows_scored,
        rows_high_toxic=rows_high_toxic,
        toxicity_threshold=toxicity_threshold,
        skipped_scoring=skipped_scoring,
        finished_at=_now_iso(),
    )
