"""Copy Bluesky dump parquet Git LFS pointers into a pipeline raw run.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/publish_dump_to_raw.py
"""

from __future__ import annotations

from pathlib import Path

DUMP_DATASET_ID = "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"
DUMP_RAW_RUN_TIMESTAMP = "2026_09_01-00:00:00"
DUMP_PARQUET_ROOT = Path("data_platform/ingestion/data_dumps/bluesky/data/parquet")
DUMP_CONFIG_PATH = Path(
    "data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml"
)


def publish_dump_to_raw(
    parquet_root: Path,
    dataset_id: str,
    raw_run_timestamp: str,
    config_path: Path,
) -> Path:
    raise NotImplementedError


def main() -> None:
    publish_dump_to_raw(
        DUMP_PARQUET_ROOT,
        DUMP_DATASET_ID,
        DUMP_RAW_RUN_TIMESTAMP,
        DUMP_CONFIG_PATH,
    )


if __name__ == "__main__":
    main()
