# Twitter LLM features campaign contract

A wrong bucket path or row count forces a full rerun, so every step file repeats only the values its pull request needs and this file holds the rest.

## Pinned identities

| Field | Value |
|-------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Platform | `twitter` |
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Dataset name | `mirrorview_2026-09-05` |
| Ingest config | `data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` |
| Pinned preprocessed run | `2026_09_06-19:28:47` |
| Preprocessed row count | `6374` posts (not comments) |
| Preprocessed file | `posts.csv` |
| Dataset format | `csv` (do not change `dataset.json`) |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Batch size | `2000` |
| Expected rows per feature | `6374` |
| Batch count | `4` (`part-00000` through `part-00003`) |
| Engine | OpenAI Batch |
| Model id | `gpt-5.4-nano` |
| Full run row constant | `FULL_RUN = 6374` |

Preprocessed input object:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv`

Copy to S3 policy: upload only `posts.csv`. Keep Git LFS for the local copy. Keep `dataset.json` in git with format `csv`. Do not upload raw `posts.csv`, `metadata.json`, or any Bluesky or Reddit path.

Source pull requests: raw collection is pull request 213. Preprocess is pull request 215.

## Campaign YAML

Checked-in file:

`data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`

Required fields:

```yaml
campaign_id: twitter_2026_09_06_192847_llm_features_v1
platform: twitter
dataset_id: twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547
preprocessed_run: "2026_09_06-19:28:47"
row_count: 6374
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

Code reads this file for campaign id `twitter_2026_09_06_192847_llm_features_v1` only. Reject any other campaign id. Do not change `FEATURE_REGISTRY` defaults. Record `engine_type` on `manifest.json` and local `metadata.json`. Do not add an `engine_type` column to feature parquet output.

Reuse registry prompts for all seven features.

Feature order above is the serial run order. The interrupt-and-resume proof runs on `is_news_or_opinion` only.

## S3 feature root and layout

Feature root:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/`

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
| Manifest | `{feature}/manifest.json` | SHA-256 digests. Records `engine_type=openai`. Untagged. Conditional atomic replace. |
| Progress | `{feature}/progress.jsonl` | Logical append via read, append, conditional replace. Untagged. One line per finished part. |
| Errors | `{feature}/errors.jsonl` | Same append semantics when needed. Untagged. |
| Watcher state | `{feature}/watcher.json` | Rolling comment id and last posted 10k milestone. Untagged. Conditional atomic replace. |

Wide outputs under the same feature root:

| Object | Path |
|--------|-------|
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

1. Load pinned preprocessed run `2026_09_06-19:28:47`.
2. Keep rows with non-empty `text`.
3. Sort by ascending `source_record_id`.
4. Take the first ten rows.

Smoke never writes `batches/part-00000.parquet` or any other production batch object.

Temporary Git copies of smoke evidence live under `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/{feature}/` during Step 2 Phase A and are deleted before merge. S3 smoke evidence under `{feature}/smoke/` remains.

## Production batch schedule (after parent approval)

| Part | Row composition |
|------|-----------------|
| `part-00000` | Ten unchanged smoke output rows (original smoke `batch_id` and `request_id` preserved) plus 1,990 new labeled rows |
| `part-00001` | 2,000 new labeled rows |
| `part-00002` | 2,000 new labeled rows |
| `part-00003` | 374 new labeled rows |

Total: 6,374 unique `source_record_id` values per feature. OpenAI Batch jobs: one smoke job of 10 rows per feature, then production jobs covering the remaining 6,364 rows (1,990 + 2,000 + 2,000 + 374). The existing campaign writer already folds `smoke/output.parquet` into `part-00000` through `_smoke_rows_by_id` in `generate_campaign_feature`.

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

Join on `CAST(source_record_id AS VARCHAR)`. Sort by `source_record_id` ascending. Left table is pinned `posts.csv`. Do not require a parquet copy of that file.

Forbidden wide columns: `toxicity_tier`, `toxicity_prob`, `label_timestamp`, `run_id`, any Perspective column, `author_id` as an extra duplicate of `author_handle`.

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

## Pricing (smoke cost math)

| Engine | Input USD per 1M tokens | Output USD per 1M tokens |
|--------|-------------------------|--------------------------|
| OpenAI Batch | `0.10` | `0.625` |

Scale ten-post averages to `full_run_row_count=6374`. Do not use the Bluesky `FULL_RUN_POST_COUNT = 200000` default for this campaign.

## Watcher

CLI never posts to GitHub. `--once` is the only mode. Add `--platform` and `--dataset-id`. When omitted, keep today's Bluesky defaults so existing Bluesky commands still work. At 6,374 rows the 10,000-row milestone never fires. Still write `progress.jsonl` after each part.

## GitHub stack and issue dependencies

Three children, one GitHub stack, parent tracking only.

| Child | Depends on | GitHub `blocked-by` | Notes |
|-------|------------|---------------------|-------|
| Step 1 | none | none | Product code. Mergeable without labeling 6,374 rows. |
| Step 2 | Step 1 | Step 1 | Docs and run artifacts only. Phase A then parent sign-off then Phase B on the same stack pull request. |
| Step 3 | Step 2 | Step 2 | Wide join and curation. |

Parent-issue owner sign-off is not a GitHub `blocked-by`. Merged Step 1 is not permission to label 6,374 rows.

## Parent issue body

The campaign labels 6,374 pinned Twitter posts from pull request 215 with seven OpenAI Batch LLM features (`gpt-5.4-nano`). Operators upload preprocessed `posts.csv` to `mirrorview-experimental-artifacts` while Git LFS keeps the local copy. The campaign reuses the Bluesky S3 backend, OpenAI Batch resume, 2,000-row parquet writer, progress watcher, and 30-day lifecycle rule for tagged batch objects.

Each feature writes four immutable 2,000-row parquet batch objects (last part 374 rows), a final feature parquet file, a hash manifest, progress records, and a permanent run report. Step 3 joins the seven outputs with fourteen preprocessed post columns and runs the MirrorView curation export.

Dataset id is `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` and preprocessed run is `2026_09_06-19:28:47`. Campaign artifacts live under `s3://mirrorview-experimental-artifacts/data_platform/data/` with campaign id `twitter_2026_09_06_192847_llm_features_v1`. OpenAI features persist provider job IDs in `active_openai_batch.json` before polling and resume the existing provider job after interruption.

Each child issue maps to one future pull request on a GitHub stack. The repository owner records production approval on the parent issue only. Do not start any 6,374-post feature run until Step 1 has merged, all seven smoke runs and per-feature cost estimates are posted, the aggregate estimate is posted here, and the repository owner signs off in a comment on the prerequisite pull request, smoke results, and aggregate cost.

Plan: `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/plan.md`

Done when:

1. The pinned preprocessed `posts.csv` is available from S3 with a verified hash, and Git LFS still holds the local copy.
2. Seven feature runs each produce exactly 6,374 unique, valid LLM labels across four batch objects and one permanent run report.
3. OpenAI features resume without duplicate provider jobs or duplicate charges.
4. Each feature writes progress per part and records estimated and actual cost.
5. One wide parquet artifact contains the fourteen pinned post columns and all seven LLM feature outputs, and the MirrorView curation export is written from `data_platform/curate/configs/twitter/mirrorview.yaml`.
6. Intermediate batches expire after 30 days under the existing lifecycle rule, while final artifacts and run metadata remain in S3.

## Children

- [ ] Step 1: Add Twitter campaign config, copy posts.csv to S3, and wire smoke tooling
- [ ] Step 2: Smoke and generate seven LLM features for 6,374 Twitter posts
- [ ] Step 3: Consolidate seven Twitter LLM features and write the MirrorView curated export
