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
PLATFORM_REDDIT = "reddit"
MANIFEST_FORMAT_KEY = "format"
INGESTION_CONFIG_KEY = "ingestion_config"
SOURCE_DUMP_FILE_KEY = "source_dump_file"
SYNC_STATUS_KEY = "sync_status"
DATASET_ID_KEY = "dataset_id"
SOURCES_KEY = "sources"
SOURCE_PARQUET_KEY = "parquet"
SOURCE_RAW_RUN_KEY = "raw_run"
NAME_KEY = "name"
OUTPUT_FORMAT_KEY = "output_format"


def promote_dump_sources_to_raw(
    config_path: Path,
    data_root: Path | None,
) -> Path:
    """Copy each dump parquet pointer into a completed raw run for the dump dataset.

    Parameters
    ----------
    config_path
        Dump dataset YAML. Must include ``dataset_id`` and ``sources``.
    data_root
        Optional data-platform data directory for tests. ``None`` uses the
        package data root.

    Returns
    -------
    pathlib.Path
        Dataset root that contains ``dataset.json`` and ``raw/``.

    Raises
    ------
    FileNotFoundError
        When the YAML or a source parquet file is missing.
    FileExistsError
        When a destination ``comments.parquet`` already exists.
    ValueError
        When ``dataset_id`` is missing or malformed.
    """
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    """Promote dump parquet pointers using the dump dataset YAML.

    Parameters
    ----------
    argv
        Argument list without the program name. ``None`` reads ``sys.argv``.
    """
    parser = argparse.ArgumentParser(
        description="Copy Reddit dump parquet pointers into pipeline raw runs."
    )
    parser.add_argument("--config", type=Path, default=DUMP_DATASET_CONFIG)
    args = parser.parse_args(argv)
    promote_dump_sources_to_raw(args.config, None)


if __name__ == "__main__":
    main()
