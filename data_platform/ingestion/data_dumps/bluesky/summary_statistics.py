"""Compute summary statistics for Bluesky Jetstream parquet dump partitions.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/summary_statistics.py
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

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
  raise NotImplementedError


def write_summary_statistics(stats: SummaryStatistics, stats_path: Path) -> None:
  """Serialize summary statistics to JSON.

  Parameters
  ----------
  stats
      Computed dump statistics.
  stats_path
      Destination path for the JSON output.
  """
  raise NotImplementedError


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
  print(STATS_PATH)
  print(stats["total_records"])
  print(stats["average_text_length"])
  print(stats["average_records_per_did"])
  print(stats["median_records_per_did"])
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
