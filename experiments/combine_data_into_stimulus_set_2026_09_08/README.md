# Combine curated data into a stimulus set

Download the four pinned MirrorView curated parquet files (Bluesky, two Twitter collections, and Reddit v2). Concatenate them into one table. Write `dataset.parquet` locally and to S3. Print counts of posts by political stance and toxicity, overall and by platform.

## Run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/combine_data_into_stimulus_set_2026_09_08/run.py
```

Expected stdout includes `combined_rows=55573` and the S3 URI for `dataset.parquet`. The write fails if that S3 object already exists.
