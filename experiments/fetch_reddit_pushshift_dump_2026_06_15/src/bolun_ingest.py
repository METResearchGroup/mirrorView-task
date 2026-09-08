"""Classify and summarize files extracted from Bolun's package."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MONTH_RE = re.compile(r"(RC|RS)_(\d{4}-\d{2})")


@dataclass
class InventoryRow:
    """Inventory summary for one extracted file."""

    kind: str
    month: str | None
    size_mb: float
    rows: int | None
    path: str


def infer_kind(path: Path) -> str:
    """Classify an extracted file by dataset type and storage format.

    Parameters
    ----------
    path : pathlib.Path
        File path within the extracted Bolun package.

    Returns
    -------
    str
        One of the inventory kind labels consumed by the staging and
        reporting scripts.
    """

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
    """Extract the ``YYYY-MM`` month token embedded in a Pushshift filename."""

    match = MONTH_RE.search(path.stem)
    return match.group(2) if match else None
