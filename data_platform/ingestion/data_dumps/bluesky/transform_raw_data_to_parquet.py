"""Transform raw Bluesky Jetstream posts CSV into zstd parquet partitions.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/transform_raw_data_to_parquet.py
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.compute as pc
import pyarrow.parquet as pq

RAW_CSV = Path(__file__).resolve().parent / "data" / "raw" / "posts.csv"
PARQUET_ROOT = Path(__file__).resolve().parent / "data" / "parquet"
MAX_FILE_BYTES = 50 * 1024 * 1024
PARQUET_COMPRESSION = "zstd"
PARQUET_COMPRESSION_LEVEL = 9
UTC_SUFFIX = " UTC"
NULL_BYTE = b"\x00"
CREATED_AT_TIMESTAMP_TYPE = pa.timestamp("us", tz="UTC")


def main() -> int:
    """Read the raw CSV and write Hive-style zstd parquet partitions.

    Returns
    -------
    int
        Process exit code; ``0`` on success.

    Raises
    ------
    FileNotFoundError
        When ``RAW_CSV`` does not exist.
    """
    table = _read_csv_table(RAW_CSV)
    hour_groups = _group_table_by_utc_date_hour(table)
    for partition_key, hour_table in sorted(hour_groups.items()):
        partition_dir = _partition_directory(partition_key)
        _write_hour_partition(hour_table, partition_dir)
    print(PARQUET_ROOT)
    return 0


def _read_csv_table(csv_path: Path) -> pa.Table:
    """Load the raw posts CSV as a PyArrow table with UTC ``created_at``.

    Parameters
    ----------
    csv_path
        Path to the step-1 Athena CSV export.

    Returns
    -------
    pyarrow.Table
        Four-column table with parsed UTC ``created_at`` timestamps.

    Raises
    ------
    FileNotFoundError
        When ``csv_path`` does not exist.
    """
    raw_bytes = _read_csv_bytes(csv_path)
    table = _parse_csv_bytes(raw_bytes)
    return _with_utc_created_at(table)


def _read_csv_bytes(csv_path: Path) -> bytes:
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path.resolve())
    return csv_path.read_bytes().replace(NULL_BYTE, b"")


def _parse_csv_bytes(raw_bytes: bytes) -> pa.Table:
    parse_options = pacsv.ParseOptions(newlines_in_values=True)
    convert_options = pacsv.ConvertOptions(
        column_types={
            "uri": pa.string(),
            "did": pa.string(),
            "created_at": pa.string(),
            "text": pa.string(),
        },
    )
    return pacsv.read_csv(
        pa.BufferReader(raw_bytes),
        parse_options=parse_options,
        convert_options=convert_options,
    )


def _with_utc_created_at(table: pa.Table) -> pa.Table:
    parsed_timestamps = _parse_utc_timestamps(table.column("created_at"))
    column_index = table.schema.get_field_index("created_at")
    return table.set_column(column_index, "created_at", parsed_timestamps)


def _parse_utc_timestamps(created_at_strings: pa.ChunkedArray) -> pa.ChunkedArray:
    parsed = pd.to_datetime(created_at_strings.to_pylist(), utc=True)
    timestamp_array = pa.array(parsed, type=CREATED_AT_TIMESTAMP_TYPE)
    return pa.chunked_array([timestamp_array])


def _group_table_by_utc_date_hour(table: pa.Table) -> dict[tuple[str, str], pa.Table]:
    """Partition rows by UTC calendar date and hour of ``created_at``.

    Parameters
    ----------
    table
        Posts table containing a UTC ``created_at`` column.

    Returns
    -------
    dict[tuple[str, str], pyarrow.Table]
        Tables keyed by ``(YYYY-MM-DD, HH)`` partition labels.
    """
    created_at = table.column("created_at")
    date_labels = pc.strftime(created_at, format="%Y-%m-%d")
    hour_labels = pc.strftime(created_at, format="%H")
    row_indices: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row_index, (date_label, hour_label) in enumerate(
        zip(date_labels.to_pylist(), hour_labels.to_pylist(), strict=True),
    ):
        row_indices[(date_label, hour_label)].append(row_index)
    return {
        partition_key: table.take(indices)
        for partition_key, indices in row_indices.items()
    }


def _partition_directory(partition_key: tuple[str, str]) -> Path:
    date_label, hour_label = partition_key
    return PARQUET_ROOT / f"date={date_label}" / f"hour={hour_label}"


def _write_hour_partition(table: pa.Table, partition_dir: Path) -> None:
    partition_dir.mkdir(parents=True, exist_ok=True)
    candidate_paths = _split_table_until_small(table, partition_dir, "candidate")
    for candidate_path in candidate_paths:
        _rename_to_content_hash(candidate_path)


def _split_table_until_small(
    table: pa.Table,
    partition_dir: Path,
    prefix: str,
) -> list[Path]:
    candidate_path = partition_dir / f"{prefix}.candidate.parquet"
    _write_table_with_zstd(table, candidate_path)
    if candidate_path.stat().st_size <= MAX_FILE_BYTES:
        return [candidate_path]
    candidate_path.unlink()
    if table.num_rows <= 1:
        raise ValueError("Single row exceeds max parquet file size")
    midpoint = table.num_rows // 2
    left_paths = _split_table_until_small(
        table.slice(0, midpoint),
        partition_dir,
        f"{prefix}a",
    )
    right_paths = _split_table_until_small(
        table.slice(midpoint),
        partition_dir,
        f"{prefix}b",
    )
    return left_paths + right_paths


def _write_table_with_zstd(table: pa.Table, output_path: Path) -> None:
    pq.write_table(
        table,
        output_path,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
    )


def _rename_to_content_hash(candidate_path: Path) -> Path:
    content_hash = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    final_path = candidate_path.parent / f"{content_hash}.parquet"
    candidate_path.rename(final_path)
    return final_path


if __name__ == "__main__":
    raise SystemExit(main())
