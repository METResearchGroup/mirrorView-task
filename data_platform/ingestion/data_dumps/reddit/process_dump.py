"""Filter, sample, and write Reddit dump comments to parquet.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/process_dump.py

Process one file:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/process_dump.py \\
        --input-file data_platform/ingestion/data_dumps/reddit/RC_2025-05.zst
"""

from __future__ import annotations

from pathlib import Path

DUMP_DIR = Path("data_platform/ingestion/data_dumps/reddit")
FILTERED_DIR = DUMP_DIR / "filtered"
DEFAULT_DUMP_STEMS = ("RC_2025-05", "RC_2025-06")


def process_dump_file(
    input_path: Path,
    output_path: Path,
    sample_size: int,
    sample_seed: int,
    sync_timestamp: str,
) -> Path:
    """Filter, sample, and write one dump file to parquet.

    Parameters
    ----------
    input_path
        Compressed dump JSONL file.
    output_path
        Destination parquet path. Must not already exist.
    sample_size
        Maximum number of kept comments to write.
    sample_seed
        Seed for reservoir sampling.
    sync_timestamp
        Run timestamp written onto every output row.

    Returns
    -------
    Path
        ``output_path`` after a successful write.

    Raises
    ------
    FileNotFoundError
        When ``input_path`` is not a file.
    FileExistsError
        When ``output_path`` already exists.
    """
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    """Process dump files from command-line arguments.

    Parameters
    ----------
    argv
        Argument list without the program name. ``None`` reads ``sys.argv``.
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
