"""Copy dump parquet Git LFS pointers into pipeline raw runs.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/promote_to_raw.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

DUMP_DATASET_CONFIG = Path(
    "data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml"
)
COMMENTS_PARQUET_FILENAME = "comments.parquet"
SYNC_STATUS_COMPLETED = "completed"


def promote_dump_sources_to_raw(
    config_path: Path,
    data_root: Path | None,
) -> Path:
    """Copy each dump parquet pointer into a completed raw run for the dump dataset."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    """Promote dump parquet pointers using the dump dataset YAML."""
    parser = argparse.ArgumentParser(
        description="Copy Reddit dump parquet pointers into pipeline raw runs."
    )
    parser.add_argument("--config", type=Path, default=DUMP_DATASET_CONFIG)
    args = parser.parse_args(argv)
    promote_dump_sources_to_raw(args.config, None)


if __name__ == "__main__":
    main()
