# Reddit curated Perspective v2

Load the pinned curated Reddit parquet, score medium LLM-toxicity comments with the Perspective thread-pool engine, and write `mirrorview_v2.parquet` beside the original.

## Load only

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --load-only
```

Expected stdout includes `curated_rows=43061`, `medium_rows=20727`, and the pinned source SHA-256.

## Score medium comments

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --score
```

Expected stdout includes `medium_rows=20727` and a scores parquet with 20727 distinct ids. A second `--score` prints `already_scored=20727` and `newly_scored=0`.
