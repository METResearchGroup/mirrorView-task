"""Load hive-partitioned Bluesky dump parquet from a pipeline raw run.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.data_dumps.bluesky.load_raw import load_hive_dump_posts"
"""

from __future__ import annotations

from pathlib import Path


def load_hive_dump_posts(run_dir: Path, sync_timestamp: str) -> list[dict[str, object]]:
    """Load hive-partitioned dump parquet and map rows onto ingest records.

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
    raise NotImplementedError
