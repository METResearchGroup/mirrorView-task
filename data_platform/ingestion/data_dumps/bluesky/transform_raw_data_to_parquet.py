"""Transform raw Bluesky Jetstream posts CSV into zstd parquet partitions.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/transform_raw_data_to_parquet.py
"""

from __future__ import annotations


def main() -> int:
  raise NotImplementedError


if __name__ == "__main__":
  raise SystemExit(main())
