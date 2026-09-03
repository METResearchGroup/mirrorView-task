# How do we get posts for the stimulus dataset?

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

This runbook goes over how we get the posts that end up as part of our stimulus datasets.

## Overview

We have a 4-stage pipeline for getting records for the dataset.

1. **Ingestion**: Ingest records from APIs and other sources.
2. **Preprocessing**: Given the raw records, preprocess them (e.g., removing text that's too short, non-English text, etc.)
3. **Feature generation**: Given the preprocessed posts, generate features.
4. **Curation**: Given the preprocessed posts and the features, curate the subset that you want as part of your final stimulus dataset.

We use 3 separate data sources:

1. Bluesky
2. Twitter
3. Reddit (we use both `praw` as well as the Reddit PushShift dataset)

We also get data dumps from 2 sources:

1. Bluesky, from the lab data integrations interface project (see [this repo](https://github.com/METResearchGroup/lab_data_integrations_interface/tree/main/data_platform))
2. Reddit, from the pushshift data dump.

These data dumps live in `data_platform/ingestion/dumps`. They're intended to follow the same data models that the other ingestion models follow, for consistency.

The "dataset_id" determines what records each step runs on.

By default, once you've ingested a certain amount of records, downstream steps check for all records that share the same dataset_id and it'll work until all records for that dataset_id are processed.

## Where does data live?

Data is stored in the following folder format:

```markdown
data_platform/data/{platform}/{dataset_id}/
  dataset.json
  raw/{timestamp}/          posts.csv (Bluesky, Twitter) or comments.csv (Reddit) + metadata.json
  preprocessed/{timestamp}/ same + metadata.json
  features/                 {feature}.csv + metadata.json [+ deadletter.jsonl]
  curated/{timestamp}/      mirrorview.csv + metadata.json
```

Each platform is an independent dataset under `data_platform/data/{platform}/{dataset_id}/`. `dataset_id` is `{bluesky|reddit|twitter}_{uuid}`.

## Stage 1: Ingestion

Bluesky and Twitter ingest write `posts.csv` or `posts.parquet`. Reddit ingest writes `comments.csv` or `comments.parquet`. Reddit ingest still uses PRAW to open a subreddit's hot, top, or new page, and it then reads the comments under each post. Reddit only returns comments through the post they belong to, so those posts are opened during the fetch. The ingest script does not write the parent posts to `posts.csv` or `posts.parquet`. Older Reddit raw run folders may still contain leftover `posts.csv` files that later stages do not read.

We also have special logic for ingesting Bluesky and Reddit data dumps. This data will have the same interface as the other ingested records, so the downstream pipeline can treat them as the same.

## Stage 2: Preprocessing

After ingestion finishes, you run preprocessing as a separate local CLI step. The code lives in `data_platform/preprocessing/`.

### Preprocessing inputs

1. A valid `dataset_id` in the form `{bluesky|twitter|reddit}_{uuid}` (see `validate_dataset_id` in `data_platform/utils/dataset.py`).
2. One or more completed raw run directories at `data_platform/data/{platform}/{dataset_id}/raw/{timestamp}/`.
3. A records file in each raw run directory you want to load.
   - Twitter uses `posts.csv` only. `TwitterStorageManager.load_records` always calls `pd.read_csv`.
   - Bluesky uses `posts.csv` or `posts.parquet`.
   - Reddit uses `comments.csv` or `comments.parquet`.
4. `metadata.json` in every raw run directory. If `sync_status` is present, it must be `completed` (`require_all_runs_complete` in `data_platform/utils/gate_checks.py`).

You run preprocessing from the repo root:

```bash
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \
  --dataset-id bluesky_<uuid>

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py \
  --dataset-id twitter_<uuid>

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \
  --dataset-id reddit_<uuid>
```

See the preprocessing folder's README for more details.

## Stage 3: Feature generation

Once we have some preprocessed posts, we generate features.

This is run with a variety of ML-based classifiers (mostly LLM-powered).

See the feature generation folder's README for more details.

## Stage 4: Curation

Once we've finished feature generation, we curate our final dataset. We only want a certain subset of posts based on business rules and filters.

See the curation folder's README for more details.
