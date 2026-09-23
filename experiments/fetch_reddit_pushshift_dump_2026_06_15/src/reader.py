"""Stream validated Pushshift comments from compressed JSONL inputs."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from pathlib import Path

import zstandard as zstd

from experiments.fetch_reddit_pushshift_dump_2026_06_15.src.models import PushshiftCommentRaw


def iter_pushshift_comments(input_path: Path) -> Iterator[PushshiftCommentRaw]:
    """Yield valid comment records from a compressed Pushshift JSONL file.

    Invalid JSON lines and records that fail schema validation are skipped so a
    single malformed row does not abort the file-level run.
    """

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
