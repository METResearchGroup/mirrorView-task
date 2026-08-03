"""Stream JSONL comment records from Pushshift .zst files."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from pathlib import Path

import zstandard as zstd

from experiments.fetch_reddit_pushshift_dump_2026_06_15.models import PushshiftCommentRaw


def iter_pushshift_comments(input_path: Path) -> Iterator[PushshiftCommentRaw]:
    """Yield parsed Pushshift comments from a compressed JSONL file."""

    dctx = zstd.ZstdDecompressor(max_window_size=2**31)
    with input_path.open("rb") as fh:
        with dctx.stream_reader(fh) as compressed_reader:
            text_reader = io.TextIOWrapper(compressed_reader, encoding="utf-8")
            for line in text_reader:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    yield PushshiftCommentRaw.model_validate(raw)
                except (json.JSONDecodeError, ValueError):
                    continue
