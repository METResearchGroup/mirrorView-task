"""Export one Bolun comment Parquet month to Pushshift-shaped JSONL .zst for runner.py."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pyarrow.parquet as pq
import typer
import zstandard as zstd

from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import (
    BOLUN_EXTRACTED_DIR,
    BOLUN_STAGED_DIR,
)

app = typer.Typer(add_completion=False)
EXTRACT_ROOT = BOLUN_EXTRACTED_DIR / "political_keyword_extract_20260612"
BATCH_SIZE = 10_000


def parquet_path_for_month(month: str) -> Path:
    return EXTRACT_ROOT / "parquet" / "comments" / f"month={month}" / "comments.parquet"


def row_to_pushshift(record: dict) -> dict:
    return {
        "id": record["comment_id"],
        "author": record["author"],
        "link_id": record["link_id"],
        "parent_id": record["parent_id"],
        "subreddit": record["subreddit"],
        "body": record["body"],
        "score": record["score"],
        "created_utc": record["created_utc"],
        "permalink": record["permalink"],
    }


@app.command()
def main(
    month: str = typer.Option(..., "--month", help="YYYY-MM, e.g. 2025-06"),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output .zst path (default: data/raw/bolun/comments/RC_{month}.zst)",
    ),
) -> None:
    src = parquet_path_for_month(month)
    if not src.is_file():
        raise typer.Exit(f"Parquet not found: {src}")

    dest = output or (BOLUN_STAGED_DIR / f"RC_{month}.zst")
    dest.parent.mkdir(parents=True, exist_ok=True)

    pf = pq.ParquetFile(src)
    total = pf.metadata.num_rows
    print(f"Exporting {total:,} rows from {src.name} -> {dest}")

    cctx = zstd.ZstdCompressor(level=3)
    written = 0
    with dest.open("wb") as out_fh:
        with cctx.stream_writer(out_fh) as compressor:
            text_out = io.TextIOWrapper(compressor, encoding="utf-8", write_through=True)
            for batch in pf.iter_batches(batch_size=BATCH_SIZE):
                for record in batch.to_pylist():
                    text_out.write(json.dumps(row_to_pushshift(record), ensure_ascii=False))
                    text_out.write("\n")
                    written += 1
                    if written % 100_000 == 0:
                        print(f"  {written:,} / {total:,}")
            text_out.flush()

    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"Wrote {written:,} rows ({size_mb:.1f} MB): {dest}")


if __name__ == "__main__":
    app()
