"""Process a single Pushshift comment .zst file end-to-end."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import typer

from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import (
    TOXICITY_THRESHOLD,
)
from experiments.fetch_reddit_pushshift_dump_2026_06_15.filters import passes_filters
from experiments.fetch_reddit_pushshift_dump_2026_06_15.models import (
    CommentToScore,
    HighToxicCommentRow,
    PushshiftCommentRaw,
)
from experiments.fetch_reddit_pushshift_dump_2026_06_15.perspective import run_batch_scoring
from experiments.fetch_reddit_pushshift_dump_2026_06_15.reader import iter_pushshift_comments
from experiments.fetch_reddit_pushshift_dump_2026_06_15.transform import build_mirrorview_rows
from experiments.fetch_reddit_pushshift_dump_2026_06_15.writer import (
    build_file_metadata,
    merge_file_into_total_metadata,
    metadata_exists,
    write_file_metadata,
    write_high_toxic_parquet,
)

app = typer.Typer(add_completion=False)
CHICAGO = ZoneInfo("America/Chicago")


def _sync_timestamp() -> str:
    return datetime.now(tz=CHICAGO).strftime("%Y_%m_%d-%H:%M:%S")


def process_input_file(input_file: Path) -> int:
    """Process one .zst file; return count of high-toxic comments written."""

    stem = input_file.stem
    if metadata_exists(stem):
        print(f"Skipping {stem}, metadata.json exists")
        return 0

    rows_read = 0
    filtered: list[PushshiftCommentRaw] = []
    for comment in iter_pushshift_comments(input_file):
        rows_read += 1
        if passes_filters(comment):
            filtered.append(comment)

    sync_ts = _sync_timestamp()
    mirrorview_rows = build_mirrorview_rows(filtered, sync_timestamp=sync_ts)
    row_by_comment_id = {row.comment_id: row for row in mirrorview_rows}

    comments_to_score = [
        CommentToScore(comment_id=row.comment_id, text=row.body)
        for row in mirrorview_rows
    ]
    scores = run_batch_scoring(comments_to_score)

    high_toxic_rows: list[HighToxicCommentRow] = []
    for score in scores:
        if not score.was_successfully_labeled or score.prob_toxic is None:
            continue
        if score.prob_toxic < TOXICITY_THRESHOLD:
            continue
        base_row = row_by_comment_id[score.comment_id]
        high_toxic_rows.append(
            HighToxicCommentRow(**base_row.model_dump(), prob_toxic=score.prob_toxic)
        )

    write_high_toxic_parquet(stem, high_toxic_rows)
    metadata = build_file_metadata(
        source_file=str(input_file),
        rows_read=rows_read,
        rows_after_filter=len(filtered),
        rows_scored=len(comments_to_score),
        rows_high_toxic=len(high_toxic_rows),
        toxicity_threshold=TOXICITY_THRESHOLD,
    )
    write_file_metadata(stem, metadata)
    merge_file_into_total_metadata(stem, len(high_toxic_rows))

    print(
        f"Processed {stem}: read={rows_read}, filtered={len(filtered)}, "
        f"scored={len(comments_to_score)}, high_toxic={len(high_toxic_rows)}"
    )
    return len(high_toxic_rows)


@app.command()
def main(
    input_file: Path = typer.Option(..., "--input-file", exists=True, dir_okay=False),
) -> None:
    process_input_file(input_file.resolve())


if __name__ == "__main__":
    app()
