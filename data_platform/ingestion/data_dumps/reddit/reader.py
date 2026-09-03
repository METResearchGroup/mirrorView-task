"""Stream JSONL comment records from compressed Reddit dump files."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from pathlib import Path

import zstandard as zstd

from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw

ZSTD_MAX_WINDOW_SIZE = 2**31


def iter_dump_comments(input_path: Path) -> Iterator[DumpCommentRaw]:
    """Yield parsed dump comments from a compressed JSONL file.

    Blank lines, invalid JSON, and rows that fail validation are skipped.

    Parameters
    ----------
    input_path
        Path to a zstd-compressed JSONL dump file.

    Yields
    ------
    DumpCommentRaw
        One validated dump comment.

    Raises
    ------
    FileNotFoundError
        When ``input_path`` is not a file.
    """
    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    decompressor = zstd.ZstdDecompressor(max_window_size=ZSTD_MAX_WINDOW_SIZE)
    with input_path.open("rb") as handle:
        with decompressor.stream_reader(handle) as compressed_reader:
            text_reader = io.TextIOWrapper(compressed_reader, encoding="utf-8")
            for line in text_reader:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    raw = json.loads(stripped)
                    yield DumpCommentRaw.model_validate(raw)
                except (json.JSONDecodeError, ValueError):
                    continue
