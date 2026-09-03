"""Stream JSONL comment records from compressed Reddit dump files."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw


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
    raise NotImplementedError
