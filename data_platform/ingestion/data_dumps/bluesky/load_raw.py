"""Load Bluesky dump parquet files from date= and hour= folders in a pipeline raw run.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.data_dumps.bluesky.load_raw import load_hive_dump_posts"
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.ingestion.data_dumps.bluesky.transform import dump_post_to_sync_row

PARQUET_GLOB = "*.parquet"
REQUIRED_NONEMPTY_KEYS = ("uri", "did", "created_at", "text")


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        return False
    return not str(value).strip()


def _keep_dump_row(row: dict[str, object]) -> bool:
    return not any(_is_blank(row.get(key)) for key in REQUIRED_NONEMPTY_KEYS)


def _parquet_paths(run_dir: Path) -> list[Path]:
    parquet_paths = sorted(path for path in run_dir.rglob(PARQUET_GLOB) if path.is_file())
    if not parquet_paths:
        raise FileNotFoundError(run_dir)
    return parquet_paths


def _mapped_rows_from_parquet(
    parquet_path: Path,
    sync_timestamp: str,
) -> list[dict[str, object]]:
    frame = pd.read_parquet(parquet_path)
    mapped: list[dict[str, object]] = []
    for row in frame.to_dict(orient="records"):
        if not _keep_dump_row(row):
            continue
        mapped.append(dump_post_to_sync_row(row, sync_timestamp))
    return mapped


def load_hive_dump_posts(run_dir: Path, sync_timestamp: str) -> list[dict[str, object]]:
    """Load dump parquet files from date and hour folders, and map rows onto ingest records.

    Parameters
    ----------
    run_dir
        Raw run directory that contains ``date=`` parquet partitions.
    sync_timestamp
        Value written onto each mapped row's ``sync_timestamp``.

    Returns
    -------
    list[dict[str, object]]
        Mapped ingest rows in sorted parquet path order.

    Raises
    ------
    FileNotFoundError
        When ``run_dir`` contains no parquet files.
    """
    mapped_rows: list[dict[str, object]] = []
    for parquet_path in _parquet_paths(run_dir):
        mapped_rows.extend(_mapped_rows_from_parquet(parquet_path, sync_timestamp))
    return mapped_rows
