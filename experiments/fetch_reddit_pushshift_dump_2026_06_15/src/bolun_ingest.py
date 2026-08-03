"""Shared helpers for Bolun package ingest."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MONTH_RE = re.compile(r"(RC|RS)_(\d{4}-\d{2})")


@dataclass
class InventoryRow:
    kind: str
    month: str | None
    size_mb: float
    rows: int | None
    path: str


def infer_kind(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("rc_") and name.endswith(".zst"):
        return "comment_zst"
    if name.startswith("rs_") and name.endswith(".zst"):
        return "submission_zst"
    if name.endswith(".parquet"):
        if "comment" in name:
            return "comment_parquet"
        if "submission" in name:
            return "submission_parquet"
        return "parquet_other"
    return "other"


def infer_month(path: Path) -> str | None:
    match = MONTH_RE.search(path.stem)
    return match.group(2) if match else None
