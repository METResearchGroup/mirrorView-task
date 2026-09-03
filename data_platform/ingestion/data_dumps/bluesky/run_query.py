"""Download Bluesky Jetstream posts for one UTC day via Athena.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""

from __future__ import annotations

from pathlib import Path

from data_platform.ingestion.data_dumps.bluesky.athena import Athena
from data_platform.ingestion.data_dumps.bluesky.queries import (
    ATHENA_WORKGROUP,
    GLUE_DATABASE,
    posts_for_utc_day_sql,
)

RAW_OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "raw" / "posts.csv"


def main() -> int:
    """Run the posts SELECT and download the Athena result CSV.

    Returns
    -------
    int
        Process exit code; ``0`` on success.
    """
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
