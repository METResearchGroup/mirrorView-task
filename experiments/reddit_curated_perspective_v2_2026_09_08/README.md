# Reddit curated Perspective, second file

Download the recorded curated Reddit Parquet file. Score the comments whose LLM toxicity tier is medium, using the same Perspective path that feature generation already uses. Write `mirrorview_v2.parquet` in the same S3 prefix as the original file.

## Load only

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --load-only
```

Expected stdout includes `curated_rows=43061`, `medium_rows=20727`, and the SHA-256 of the recorded source file.

## Score medium comments

`GOOGLE_API_KEY` must be set. Scoring uses it through `EnvVarsContainer`.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --score
```

Expected stdout includes `medium_rows=20727` and a scores parquet with 20727 distinct ids. A second `--score` prints `already_scored=20727` and `newly_scored=0`.

## Write the second curated file

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --write-v2
```

Expected stdout includes `promotions=3000`, `v2_rows=43061`, and a line that the original SHA-256 is unchanged. The command fails if `mirrorview_v2.parquet` already exists. The SHA-256 values and the political stance by toxicity tier counts are in `RESULTS.md`.
