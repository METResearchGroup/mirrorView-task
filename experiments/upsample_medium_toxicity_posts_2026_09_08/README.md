# Upsample unused medium toxicity posts

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

Sample 2,000 unused medium toxicity posts from the leftover cleaned pool after dropping the 10,200 post sample. Take 1,000 left-leaning posts and 1,000 right-leaning posts with seed 42, without replacement.

## Sources

Combined parquet: `s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet`

10,200 post sample: `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet`

Cleanup matches pull request 267: previously used ids, previously used original text, duplicate ids, then duplicate text.

## Output

`s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/upsample_2000_medium_toxicity_posts.parquet`

A second upload of that key fails.

## Run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_medium_toxicity_posts_2026_09_08/run.py
```
