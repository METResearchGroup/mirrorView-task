# How do we get posts for the stimulus dataset?

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

## Where does data live?

Data is stored in the following folder format:

```markdown
data_platform/data/{platform}/{dataset_id}/
  dataset.json
  raw/{timestamp}/          posts.csv or comments.csv + metadata.json
  preprocessed/{timestamp}/ same + metadata.json
  features/                 {feature}.csv + metadata.json [+ deadletter.jsonl]
  curated/{timestamp}/      mirrorview.csv + metadata.json
```

Each platform is an independent dataset under `data_platform/data/{platform}/{dataset_id}/`. `dataset_id` is `{bluesky|reddit|twitter}_{uuid}`.

## Stage 1: Ingestion

## Stage 2: Preprocessing

After ingestion finishes, you run preprocessing as a separate local CLI step. The code lives in `data_platform/preprocessing/`.

Reddit preprocessing works on comments only, not posts. You can preprocess Reddit comments from any ingestion source, as long as the file matches the expected schema.

### Preprocessing inputs

1. A valid `dataset_id` in the form `{bluesky|twitter|reddit}_{uuid}` (see `validate_dataset_id` in `data_platform/utils/dataset.py`).
2. One or more completed raw run directories at `data_platform/data/{platform}/{dataset_id}/raw/{timestamp}/`.
3. A records file in each raw run directory you want to load.
   - Twitter uses `posts.csv` only. `TwitterStorageManager.load_records` always calls `pd.read_csv`.
   - Bluesky uses `posts.csv` or `posts.parquet`.
   - Reddit uses `comments.csv` or `comments.parquet`.
   - Bluesky and Reddit pick `csv` or `parquet` from `dataset.json` via `StorageManager` in `data_platform/utils/storage.py`.
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

In each `preprocess_*.py` file, you define a `PreprocessPlatformSpec` and call `preprocess_records` in `data_platform/preprocessing/runner.py`.

| Platform | Entrypoint | Spec constant | Storage manager | Sync model |
| --- | --- | --- | --- | --- |
| Bluesky | `data_platform/preprocessing/preprocess_bluesky.py` | `BLUESKY_SPEC` | `BlueskyStorageManager` | `SyncBlueskyPostModel` |
| Twitter | `data_platform/preprocessing/preprocess_twitter.py` | `TWITTER_SPEC` | `TwitterStorageManager` | `SyncTwitterPostModel` |
| Reddit | `data_platform/preprocessing/preprocess_reddit.py` | `REDDIT_SPEC` | `RedditStorageManager` | `SyncRedditCommentModel` |

Record schemas live in `data_platform/models/sync.py`.

You look up per-platform CSV column names in `PlatformSpecificColumns` (`data_platform/utils/platform_specific_columns.py`). In each platform CLI, you set `spec.columns` to `BLUESKY_COLUMNS`, `TWITTER_COLUMNS`, or `REDDIT_COLUMNS`. During preprocessing, you read three fields on `PlatformSpecificColumns`.

- `records_id_column` for dedupe
- `text_column` for validators and transforms
- `records_file_key` for the records filename (`posts` vs `comments`)

Feature generation and curation also read `feature_file_id_column`, which is `uri` for all three platforms.

| Platform | `records_id_column` | `text_column` | `records_file_key` | `feature_file_id_column` |
| --- | --- | --- | --- | --- |
| Bluesky | `uri` | `text` | `posts` | `uri` |
| Twitter | `tweet_id` | `text` | `posts` | `uri` |
| Reddit | `comment_fullname` | `body` | `comments` | `uri` |

### Preprocessing outputs

After each successful run, you get a new timestamped directory at `data_platform/data/{platform}/{dataset_id}/preprocessed/{timestamp}/`, even when zero rows pass the filters.

1. A records file with the same basename and format as raw (`posts.csv` / `posts.parquet` or `comments.csv` / `comments.parquet`).
2. `metadata.json` with at least these fields.
   - `dataset_id`
   - `source_raw_run` (last raw run path, relative to the dataset root)
   - `source_raw_runs` (all raw run directories scanned, not only runs that contributed rows)
   - `preprocess_timestamp` (the new run directory name)
   - `row_counts.input` (rows after dedupe, before filters)
   - `row_counts.output` (rows after filters)
   - `files` (map from records file key to filename, e.g. `"posts": "posts.csv"`)

You call `save_preprocessed` in `data_platform/preprocessing/runner.py` to write both files.

### (Preprocessing) Extra details of note

```mermaid
flowchart TD
  cli["Platform CLI preprocess_*.py"]
  validate["validate_dataset_id"]
  gate["require_all_runs_complete on raw runs"]
  warm["DedupeSession.warm prior preprocessed IDs"]
  load["load_raw_records from all raw runs"]
  drop["_drop_already_preprocessed"]
  transform["apply_text_transform optional Twitter strip t.co"]
  filter["filter_records validators"]
  save["save_preprocessed new timestamped run"]

  cli --> validate --> gate --> warm --> load --> drop --> transform --> filter --> save
```

**Shared pipeline** (`data_platform/preprocessing/runner.py`)

`PreprocessPlatformSpec` fields:

- `platform`
- `storage_cls`
- `model_cls`
- `columns` (`PlatformSpecificColumns`)
- `text_validators`
- `row_validators` (optional; Reddit only)
- `text_transform` (optional; Twitter only)

You use `load_raw_records` to read every raw run directory. You validate each row with the sync model, and you concatenate the results.

You call `_drop_already_preprocessed` to skip IDs from earlier preprocessed runs. `DedupeSession` in `data_platform/utils/deduplication.py` loads prior preprocessed IDs with `include_prior_runs=True`. Within the current batch, you drop duplicate IDs and keep the last row.

You call `apply_text_transform` before filtering when the spec defines a transform.

You call `filter_records` to keep rows whose text passes all text validators. When the spec defines row validators (Reddit only), you also require the `author` column to pass them.

You call `preprocess_records` to run:

- `validate_dataset_id`
- `require_all_runs_complete` (gate)
- `DedupeSession.warm` (warm)
- `load_raw_records` (load)
- `_drop_already_preprocessed` (drop)
- `apply_text_transform` (transform, when defined)
- `filter_records` (filter)
- `save_preprocessed` (save)

It prints how many rows were kept.

**Platform filters**

Each platform wires validators under `data_platform/preprocessing/validators/`. Bluesky and Twitter apply text validators only. Reddit applies text validators and row validators.

Bluesky text validators (`preprocess_bluesky.py`)

1. You reject rows that contain phone numbers (`check_if_not_phone`).
2. You keep rows with length 100 to 300 characters (`check_if_valid_post_length`).
3. You reject rows that contain URLs (`check_if_post_has_no_urls`).
4. You keep rows with English text (`check_if_text_english`).

Twitter text validators (`preprocess_twitter.py`)

1. You strip `t.co` links before filter and save (`strip_tco_links` in `twitter_validators.py`, wired as `text_transform` on `TWITTER_SPEC`).
2. You reject rows that contain phone numbers (`check_if_not_phone`).
3. You keep rows with length 50 to 280 characters (`check_if_valid_twitter_post_length`).
4. You reject rows with external URLs after `t.co` removal (`check_if_twitter_text_has_no_external_urls`).
5. You keep rows with English text (`check_if_text_english`).

Reddit comment text validators (`preprocess_reddit.py`)

1. You reject rows with removed or deleted bodies (`check_if_body_not_removed`).
2. You reject rows with `u/` and `r/` mentions (`check_if_no_reddit_mentions`).
3. You reject rows with markdown links and images (`check_if_no_markdown_links`).
4. You reject rows with direct URLs and bare domains (`check_if_no_direct_urls`).
5. You reject rows with common media host names (`check_if_no_media_hosts`).
6. You reject rows that contain phone numbers (`check_if_not_phone`).
7. You keep rows with English text (`check_if_text_english`).

Reddit row validators (`preprocess_reddit.py`)

1. You reject rows whose author is AutoModerator (`check_if_not_automoderator`).

You can re-run preprocessing on the same dataset safely. IDs from earlier preprocessed runs are skipped, and each run still creates a fresh timestamped output directory.

## Stage 3: Feature generation

## Stage 4: Curation

...

(For Reddit, asterisk this by saying we've got 2 sources, `praw` and then the Reddit PushShift data).
