"""Filter Reddit dump comments and write a sampled parquet file.

Run this from the repo root.

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/process_dump.py

To process one file, pass `--input-file` like this.

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/process_dump.py \\
        --input-file data_platform/ingestion/data_dumps/reddit/RC_2025-05.zst
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from pathlib import Path
from random import Random

import pandas as pd

from data_platform.ingestion.data_dumps.reddit.filters import keep_dump_comment
from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw
from data_platform.ingestion.data_dumps.reddit.reader import iter_dump_comments
from data_platform.ingestion.data_dumps.reddit.sample import (
    DEFAULT_SAMPLE_SEED,
    DEFAULT_SAMPLE_SIZE,
    reservoir_sample,
)
from data_platform.ingestion.data_dumps.reddit.transform import dump_comment_to_sync_row
from data_platform.models.sync import SyncRedditCommentModel
from lib.timestamp_utils import get_current_timestamp

DUMP_DIR = Path("data_platform/ingestion/data_dumps/reddit")
FILTERED_DIR = DUMP_DIR / "filtered"
DEFAULT_DUMP_STEMS = ("RC_2025-05", "RC_2025-06")
PARQUET_INDEX = False
ZST_SUFFIX = ".zst"
PARQUET_SUFFIX = ".parquet"


def _require_processable_paths(input_path: Path, output_path: Path) -> None:
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if output_path.exists():
        raise FileExistsError(output_path)


def _iter_kept_dump_comments(input_path: Path) -> Iterator[DumpCommentRaw]:
    for comment in iter_dump_comments(input_path):
        if keep_dump_comment(comment):
            yield comment


def _rows_for_sampled_comments(
    comments: list[DumpCommentRaw],
    sync_timestamp: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for comment in comments:
        mapped = dump_comment_to_sync_row(comment, sync_timestamp)
        rows.append(SyncRedditCommentModel.model_validate(mapped).model_dump())
    return rows


def _write_comment_parquet(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(SyncRedditCommentModel.model_fields.keys())
    frame = pd.DataFrame(rows) if rows else pd.DataFrame(columns=fieldnames)
    frame.to_parquet(output_path, index=PARQUET_INDEX)


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
    _require_processable_paths(input_path, output_path)
    sampled = reservoir_sample(
        _iter_kept_dump_comments(input_path),
        sample_size,
        Random(sample_seed),
    )
    rows = _rows_for_sampled_comments(sampled, sync_timestamp)
    _write_comment_parquet(rows, output_path)
    return output_path


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter Reddit dump comments, sample the comments that remain, and write them to parquet."
    )
    parser.add_argument("--input-file", action="append", dest="input_files")
    parser.add_argument("--output-dir", type=Path, default=FILTERED_DIR)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SAMPLE_SEED)
    return parser.parse_args(argv)


def _input_paths(input_files: Sequence[str] | None) -> list[Path]:
    if input_files:
        return [Path(path) for path in input_files]
    return [DUMP_DIR / f"{stem}{ZST_SUFFIX}" for stem in DEFAULT_DUMP_STEMS]


def main(argv: list[str] | None = None) -> None:
    """Process dump files from command-line arguments.

    Parameters
    ----------
    argv
        Argument list without the program name. ``None`` reads ``sys.argv``.
    """
    args = _parse_args(argv)
    for input_path in _input_paths(args.input_files):
        output_path = args.output_dir / f"{input_path.stem}{PARQUET_SUFFIX}"
        process_dump_file(
            input_path,
            output_path,
            args.sample_size,
            args.seed,
            get_current_timestamp(),
        )


if __name__ == "__main__":
    main()
