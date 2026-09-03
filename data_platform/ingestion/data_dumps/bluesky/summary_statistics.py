"""Compute summary statistics for Bluesky Jetstream parquet dump partitions.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/summary_statistics.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import TypedDict

import pyarrow.compute as pc
import pyarrow.parquet as pq

PARQUET_ROOT = Path(__file__).resolve().parent / "data" / "parquet"
STATS_PATH = Path(__file__).resolve().parent / "data" / "summary_statistics.json"


class SummaryStatistics(TypedDict):
    total_records: int
    average_text_length: float
    average_records_per_did: float
    median_records_per_did: float


def compute_summary_statistics(parquet_root: Path) -> SummaryStatistics:
    """Aggregate dump statistics from all parquet files under ``parquet_root``.

    Parameters
    ----------
    parquet_root
        Root directory containing Hive-style parquet partitions.

    Returns
    -------
    SummaryStatistics
        Row counts and text/DID aggregates for the dump.

    Raises
    ------
    ZeroDivisionError
        When no distinct DIDs are present in the parquet files.
    """
    totals = _scan_parquet_totals(parquet_root)
    return _build_summary_statistics(totals)


def _scan_parquet_totals(parquet_root: Path) -> tuple[int, int, Counter[str]]:
    total_records = 0
    total_text_length = 0
    records_per_did: Counter[str] = Counter()
    for parquet_path in sorted(parquet_root.rglob("*.parquet")):
        row_count, text_length = _accumulate_parquet_file_stats(
            parquet_path,
            records_per_did,
        )
        total_records += row_count
        total_text_length += text_length
    return total_records, total_text_length, records_per_did


def _build_summary_statistics(
    totals: tuple[int, int, Counter[str]],
) -> SummaryStatistics:
    total_records, total_text_length, records_per_did = totals
    if not records_per_did:
        raise ZeroDivisionError("no distinct DIDs")
    return SummaryStatistics(
        total_records=total_records,
        average_text_length=total_text_length / total_records,
        average_records_per_did=total_records / len(records_per_did),
        median_records_per_did=float(median(records_per_did.values())),
    )


def _accumulate_parquet_file_stats(
    parquet_path: Path,
    records_per_did: Counter[str],
) -> tuple[int, int]:
    table = pq.read_table(parquet_path, columns=["did", "text"])
    text_column = table.column("text")
    text_lengths = pc.utf8_length(pc.fill_null(text_column, ""))
    records_per_did.update(table.column("did").to_pylist())
    return table.num_rows, pc.sum(text_lengths).as_py()


def write_summary_statistics(stats: SummaryStatistics, stats_path: Path) -> None:
    """Serialize summary statistics to JSON.

    Parameters
    ----------
    stats
        Computed dump statistics.
    stats_path
        Destination path for the JSON output.
    """
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with stats_path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
        handle.write("\n")


def main() -> int:
    """Compute dump statistics and write them to ``STATS_PATH``.

    Returns
    -------
    int
        Process exit code; ``0`` on success.

    Raises
    ------
    ZeroDivisionError
        When no distinct DIDs are present in the parquet files.
    """
    stats = compute_summary_statistics(PARQUET_ROOT)
    write_summary_statistics(stats, STATS_PATH)
    _print_summary_statistics(stats)
    return 0


def _print_summary_statistics(stats: SummaryStatistics) -> None:
    print(STATS_PATH)
    print(stats["total_records"])
    print(stats["average_text_length"])
    print(stats["average_records_per_did"])
    print(stats["median_records_per_did"])


if __name__ == "__main__":
    raise SystemExit(main())
