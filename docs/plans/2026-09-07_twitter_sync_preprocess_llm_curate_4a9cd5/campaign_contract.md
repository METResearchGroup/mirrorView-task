# New dated Twitter LLM campaign contract

A wrong dataset id, bucket path, or row count forces a full rerun. Step files repeat only the values their pull request needs. This file holds the rest.

## Pinned identities

| Field | Value |
|-------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Platform | `twitter` |
| Dataset id | `twitter_5901767a-e609-46fc-9a17-742516b548f2` |
| Dataset name | `mirrorview_2026-09-07` |
| Ingest config | `data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml` |
| Copy source ingest YAML | `data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` |
| Preprocessed file | `posts.csv` |
| Dataset format | `csv` (do not change `dataset.json`) |
| Batch size | `2000` |
| Engine | OpenAI Batch |
| Model id | `gpt-5.4-nano` |

Do not regenerate the dataset id. It must not equal any of:

- `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547`
- `twitter_f47ac10b-58cc-4372-a567-0e02b2c3d479`
- `twitter_a8f3c22d-6b14-4e9a-9d2f-1c7e5a9b3d48`
- `twitter_3b46b8f9-7e73-4e44-8f6a-3d0e67cfe921`
- `twitter_00000000-0000-4000-8000-000000000099`

## Values filled after Step 2

Record these in the Step 2 pull request and copy them into the Step 3 campaign YAML. Do not invent them during Step 1.

| Field | Source |
|-------|--------|
| Preprocessed run | `metadata.json` `preprocess_timestamp` under the new dataset, e.g. `2026_09_07-HH:MM:SS` |
| Preprocessed row count | `metadata.json` `row_counts.output` |
| Campaign id | `twitter_` + preprocessed run with `-` → `_` and `:` removed + `_llm_features_v1` |
| Expected rows per feature | same as preprocessed row count |
| Full-run cost scale | `--full-run-row-count` equal to that row count |
| Last batch part size | `row_count % 2000` when that remainder is not 0; otherwise the last part is a full 2000-row part |

Example: preprocessed run `2026_09_07-15:02:11` becomes campaign id `twitter_2026_09_07_150211_llm_features_v1`.

Do not reuse campaign id `twitter_2026_09_06_192847_llm_features_v1`.

## Prior campaign that must keep working

| Field | Value |
|-------|-------|
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Ingest config | `data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` |
| Preprocessed run | `2026_09_06-19:28:47` |
| Row count | `6374` |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Campaign YAML | `data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml` |

## Ingest YAML

Checked-in file after Step 1:

`data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml`

Byte-for-byte copy of `mirrorview_2026-09-05.yaml` except:

```text
dataset_id: twitter_5901767a-e609-46fc-9a17-742516b548f2
name: mirrorview_2026-09-07
description: Mirrorview topic keyword collection across Twitter (dated run 2026-09-07)
date: "2026-09-07"
```

Keep `max_posts: 8000`, `limit_per_task: 110`, 73 keywords in the same order, `lang: en`, exclude `reply` / `retweet` / `quote`, `dedupe_policy: [prior_runs_same_dataset]`, and `record_types: [twitter.tweet]`.

Do not add `output_format`, `query_batch_size`, top-level `fetch`, `current_run` in `dedupe_policy`, or a singular `keyword` key.

Twitter has no `new-run` subcommand. One command starts or resumes. Resume with `--run-dir {timestamp}`. Do not pass `--run-dir` on the first start.

## Campaign YAML

Checked-in file after Step 3:

`data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml`

Required fields, with `{preprocessed_run}`, `{row_count}`, and `{campaign_id}` from Step 2:

```yaml
campaign_id: {campaign_id}
platform: twitter
dataset_id: twitter_5901767a-e609-46fc-9a17-742516b548f2
preprocessed_run: "{preprocessed_run}"
row_count: {row_count}
batch_size: 2000
engine_type: openai
model_id: gpt-5.4-nano
features:
  - is_news_or_opinion
  - is_political
  - is_likely_spam
  - is_self_contained
  - is_structurally_complete
  - political_stance
  - llm_toxicity_tiered
```

Loader: scan `data_platform/generate_features/configs/twitter/*.yaml` for a mapping whose `campaign_id` equals the requested id. Return that mapping. If two files share an id, raise. If none match, raise `ValueError` naming the rejected id.

Do not change `FEATURE_REGISTRY` defaults. Record `engine_type` on `manifest.json` and local `metadata.json`. Do not add an `engine_type` column to feature parquet output.

Feature order above is the serial run order. Interrupt-and-resume proof runs on `is_news_or_opinion` only.

## Copy to S3

Upload only:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/posts.csv`

Keep Git LFS for the local copy. Keep `dataset.json` in git with format `csv`. Do not upload raw `posts.csv`, `metadata.json`, or any Bluesky or Reddit path. Hash is SHA-256 of object bytes. Never use S3 ETag as a content hash. Abort if the local file still starts with Git LFS pointer text.

Inventory path:

`data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/s3_preprocessed_inventory.json`

## S3 feature root and layout

Feature root:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/{campaign_id}/`

Per feature `{feature}` under that root:

| Object | Path | Notes |
|--------|------|-------|
| Smoke input | `{feature}/smoke/input.parquet` | Ten-post sample input. Untagged. |
| Smoke output | `{feature}/smoke/output.parquet` | Ten labeled rows with label metadata columns. Untagged. |
| Smoke cost report | `{feature}/smoke/cost_report.json` | Token and pricing estimates. Untagged. |
| Smoke resume evidence | `{feature}/smoke/resume_evidence.json` | Present for `is_news_or_opinion` only. Untagged. |
| Active OpenAI state | `{feature}/active_openai_batch.json` | Mutable. Untagged. Conditional atomic replace. |
| Batch parquet | `{feature}/batches/part-NNNNN.parquet` | Zero-based five-digit index. Immutable once written. Tagged `intermediate-artifact=true`. |
| Final parquet | `{feature}/final.parquet` | One consolidated file per feature. Untagged. |
| Manifest | `{feature}/manifest.json` | SHA-256 digests. Records `engine_type=openai`. Untagged. |
| Progress | `{feature}/progress.jsonl` | One line per finished part. Untagged. |
| Errors | `{feature}/errors.jsonl` | Same append semantics when needed. Untagged. |
| Watcher state | `{feature}/watcher.json` | Untagged. `--once` only. Never posted to GitHub. |

Wide outputs under the same feature root:

| Object | Path |
|--------|------|
| Wide parquet | `wide/features.parquet` |
| Wide manifest | `wide/manifest.json` |

Forbidden layout elements:

- No `campaigns/` prefix.
- No `shards/` directory or `shard_*` object names.
- No `final/` subdirectory.
- No parquet copy of the dated preprocessed `posts.csv`.
- No GitHub posting from repository code.

## Smoke sample

Shared by all seven features:

1. Load the Step 2 preprocessed run.
2. Keep rows with non-empty `text`.
3. Sort by ascending `source_record_id`.
4. Take the first ten rows.

Smoke never writes `batches/part-00000.parquet` or any other production batch object.

Temporary Git copies of smoke evidence live under `docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/smoke/{feature}/` during Step 4 Phase A and are deleted before merge. S3 smoke evidence under `{feature}/smoke/` remains.

## Production batch schedule (after parent approval)

Let `n` be campaign YAML `row_count`.

| Part | Row composition |
|------|-----------------|
| `part-00000` | Ten unchanged smoke output rows (original smoke `batch_id` and `request_id` preserved) plus up to 1,990 new labeled rows |
| later full parts | 2,000 new labeled rows each |
| last part | `n % 2000` new labeled rows when that remainder is not 0; omit a trailing empty part |

`part-00000` is 10 smoke rows plus the remaining rows of the first 2,000-row window. Do not assume last-part size 374.

The existing campaign writer already folds `smoke/output.parquet` into `part-00000` through `_smoke_rows_by_id` in `generate_campaign_feature`.

## Label row schema

Every row in `smoke/output.parquet`, `batches/part-*.parquet`, and `final.parquet`:

| Column | Meaning |
|--------|---------|
| `source_record_id` | Preprocessed tweet id |
| `run_id` | `{campaign_id}:{feature}` |
| `batch_id` | Provider batch id |
| `request_id` | Provider request id |
| `attempt_count` | 1–4 |
| `label_timestamp` | UTC from `get_current_timestamp` |
| `{label_field}` | Feature-specific column below |

| Feature | Raw label column | Accepted values |
|---------|------------------|-----------------|
| `is_news_or_opinion` | `category` | `news`, `opinion`, `neither` |
| `is_political` | `is_political` | boolean |
| `is_likely_spam` | `is_likely_spam` | boolean |
| `is_self_contained` | `is_self_contained` | boolean |
| `is_structurally_complete` | `is_structurally_complete` | boolean |
| `political_stance` | `political_stance` | `left`, `right`, `neutral`, `unclear` |
| `llm_toxicity_tiered` | `toxicity_tier` | `low`, `medium`, `high` |

## Wide table

Wide output: exactly 21 columns in this order.

Fourteen preprocessed columns:

`tweet_id`, `record_id`, `url`, `username`, `author_handle`, `text`, `created_at`, `like_count`, `retweet_count`, `reply_count`, `quote_count`, `keyword`, `sync_timestamp`, `source_record_id`

`username` is the public handle. `author_handle` on this corpus is a copy of `author_id` from Twitter preprocess.

Seven aliased label columns:

| Wide column | Source feature | Source column |
|-------------|----------------|---------------|
| `news_or_opinion_category` | `is_news_or_opinion` | `category` |
| `is_political` | `is_political` | `is_political` |
| `is_likely_spam` | `is_likely_spam` | `is_likely_spam` |
| `is_self_contained` | `is_self_contained` | `is_self_contained` |
| `is_structurally_complete` | `is_structurally_complete` | `is_structurally_complete` |
| `political_stance` | `political_stance` | `political_stance` |
| `llm_toxicity_tier` | `llm_toxicity_tiered` | `toxicity_tier` |

Join on `CAST(source_record_id AS VARCHAR)`. Sort by `source_record_id` ascending. Left table is the new dataset's S3 `posts.csv`. Do not require a parquet copy of that file.

Row count equals campaign YAML `row_count`, not 6374.

Forbidden wide columns: `toxicity_tier`, `toxicity_prob`, `label_timestamp`, `run_id`, any Perspective column, `author_id` as an extra duplicate of `author_handle`.

Do not change `FEATURE_REGISTRY`, Bluesky `EXPECTED_WIDE_ROW_COUNT = 200000` in `data_platform/curate/consolidate.py`, or Bluesky `PREPROCESSED_WIDE_COLUMNS`.

## Curation

Rules file: `data_platform/curate/configs/twitter/mirrorview.yaml`. Do not change filter semantics.

| Filter | Value |
|--------|-------|
| `news_or_opinion_category` | `opinion` |
| `is_political` | `true` |
| `is_likely_spam` | `false` |
| `political_stance` | `left` or `right` |
| `is_self_contained` | `true` |
| `is_structurally_complete` | `true` |

Write the filtered frame with `TwitterStorageManager("curated", dataset_id)`. Export stem comes from the YAML (`mirrorview.parquet`).

Resolve feature prefixes with `FeaturePaths.for_campaign(..., platform="twitter", dataset_id=...)`. Left table is csv, not parquet. Parquet bytes for campaign objects may need `CampaignObjectStore` because dataset format is csv.

## Pricing (smoke cost math)

| Engine | Input USD per 1M tokens | Output USD per 1M tokens |
|--------|-------------------------|--------------------------|
| OpenAI Batch | `0.10` | `0.625` |

Scale ten-post averages to `--full-run-row-count` equal to the new preprocessed row count. Do not use `6374` or Bluesky `FULL_RUN_POST_COUNT = 200000` for this campaign.

## Watcher

CLI never posts to GitHub. `--once` is the only mode. Pass `--platform twitter` and `--dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2`. `github_write_skipped=true`. The 10,000-row milestone does not fire for a corpus this size. Still write `progress.jsonl` after each part.

## Git tracking

Keep the 2026-09-05 git ignore and Git LFS exceptions. Add the same shape for the new dataset:

```text
!data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/
!data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/**
!data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/**/*.csv
```

`.gitattributes`:

```text
data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/**/*.csv filter=lfs diff=lfs merge=lfs -text
```

## GitHub stack and issue dependencies

Five children, one GitHub stack, parent tracking only.

| Child | Depends on | GitHub `blocked-by` | Notes |
|-------|------------|---------------------|-------|
| Step 1 | none | none | Dated YAML, live sync, raw Git LFS commit. |
| Step 2 | Step 1 | Step 1 | Preprocess and preprocessed Git LFS commit. |
| Step 3 | Step 2 | Step 2 | Campaign YAML, directory loader, S3 csv copy. |
| Step 4 | Step 3 | Step 3 | Docs and run artifacts only. Phase A then parent sign-off then Phase B on the same stack pull request. |
| Step 5 | Step 4 | Step 4 | Wide join and curation. Expected row count from campaign YAML. |

Parent-issue owner sign-off is not a GitHub `blocked-by`. Merged Step 3 is not permission to label the full preprocessed set.

Reuse: `data_platform/ingestion/sync_twitter.py`, `data_platform/preprocessing/preprocess_twitter.py` (no Twitter preprocess YAML), `data_platform/generate_features/smoke_twitter_campaign.py`, `data_platform/generate_features/generate_twitter_features.py` campaign mode, `data_platform/curate/consolidate_twitter_llm_campaign.py`, watcher `--once`, `campaign_cost_report.py --full-run-row-count`.
