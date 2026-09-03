"""Load hive-partitioned Bluesky dump parquet from a pipeline raw run.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.data_dumps.bluesky.load_raw import load_hive_dump_posts"
"""

from __future__ import annotations

from pathlib import Path


def load_hive_dump_posts(run_dir: Path, sync_timestamp: str) -> list[dict[str, object]]:
    raise NotImplementedError
