"""Compute summary statistics for Bluesky Jetstream parquet dump partitions.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/summary_statistics.py
"""

from __future__ import annotations

from pathlib import Path

PARQUET_ROOT = Path(__file__).resolve().parent / "data" / "parquet"
STATS_PATH = Path(__file__).resolve().parent / "data" / "summary_statistics.json"


def main() -> int:
    """Write summary statistics JSON for the parquet dump.

    Returns
    -------
    int
        Process exit code; ``0`` on success.
    """
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
