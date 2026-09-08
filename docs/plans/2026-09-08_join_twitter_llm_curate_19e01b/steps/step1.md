# Step 1: Read expected wide row count from the campaign YAML

## Scope

- **Caller:** `data_platform/curate/consolidate_twitter_llm_campaign.py` `main`
- **Task:** Load expected wide row count from `load_twitter_campaign_config(campaign_id)["row_count"]`. Fail if CLI `--dataset-id` or `--preprocessed-run` disagrees with that YAML. Keep csv left-table load, manifest checks, 21-column join, wide upload, and MirrorView curation. Thread the YAML row count through manifest checks, wide validation, and the wide manifest.
- **Out of scope:** pytest, GitHub posting, relabeling features, converting the dated dataset to parquet, editing Bluesky consolidator code, editing `twitter/mirrorview.yaml`, editing `consolidate.py`, editing `generate_features/**`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/curate/consolidate_twitter_llm_campaign.py` | Hardcoded `TWITTER_EXPECTED_WIDE_ROW_COUNT = 6374` |
| `/workspace/data_platform/generate_features/twitter_campaign_config.py` | Directory loader. Do not edit. |
| `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml` | New `row_count` 6408 |
| `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml` | Old `row_count` 6374. Do not edit. |
| `/workspace/data_platform/curate/consolidate.py` | `LLM_CAMPAIGN_FEATURE_NAMES`, feature aliases. Do not edit. |
| `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml` | Filter set. Do not edit. |
| `/workspace/data_platform/utils/storage.py` | `TwitterStorageManager` |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `FeaturePaths.for_campaign`, `CampaignObjectStore` |
| `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/wide_run_report.md` | Report shape to copy in Step 2 |

## Files allowed to change

- `/workspace/data_platform/curate/consolidate_twitter_llm_campaign.py`

## Files forbidden to change

- `/workspace/data_platform/curate/consolidate.py`
- `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/generate_features/**`
- `/workspace/tests/**`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`
- Any file outside the allowed list

## Locked identities

| Field | Value |
|-------|-------|
| Dataset id | `twitter_5901767a-e609-46fc-9a17-742516b548f2` |
| Preprocessed run | `2026_09_08-01:48:08` |
| Campaign id | `twitter_2026_09_08_014808_llm_features_v1` |
| Left table | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/2026_09_08-01:48:08/posts.csv` |
| Inventory SHA-256 | `0461a0dc7ac5ecf1c5699fa893013dc7165af482a5347067e413bf4315ffdbd2` |
| Wide rows | `6408` |
| Wide columns | `21` |
| Sort | `source_record_id ASC` |
| Platform argument | `twitter` |
| Rules | `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml` |

Wide output URI:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/wide/features.parquet`

Wide columns in this exact order:

`tweet_id`, `record_id`, `url`, `username`, `author_handle`, `text`, `created_at`, `like_count`, `retweet_count`, `reply_count`, `quote_count`, `keyword`, `sync_timestamp`, `source_record_id`, `news_or_opinion_category`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tier`

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run 2026_09_08-01:48:08 \
  --campaign-id twitter_2026_09_08_014808_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/wide/features.parquet
```

## Work

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then live checks below, written in the module docstring. The consolidator already exists, so do not replace working bodies with `NotImplementedError`.

### Campaign YAML row count

Call `load_twitter_campaign_config(campaign_id)`. Read `row_count`, `dataset_id`, and `preprocessed_run` from that mapping. Put `expected_row_count` on `CampaignConsolidateArgs`. Raise `ValueError` when CLI `--dataset-id` or `--preprocessed-run` disagrees with the YAML. Remove `TWITTER_EXPECTED_WIDE_ROW_COUNT`. Use the YAML row count for feature `final.parquet.row_count` checks, wide row count, distinct `source_record_id` count, and the wide manifest `row_count` fields.

A run against `twitter_2026_09_06_192847_llm_features_v1` must still expect 6374 because that YAML still says 6374.

### Path helper

Call `FeaturePaths.for_campaign(campaign_id, feature_name, platform="twitter", dataset_id=dataset_id)`.

### Posts csv

Download the pinned S3 object as csv. Hash full object bytes with SHA-256. Compare to the inventory object for that key. Raise before joining if the hash does not match. Do not load `posts.parquet`. Do not convert the csv to a parquet left table.

### Feature manifests

For each name in `LLM_CAMPAIGN_FEATURE_NAMES`, load `manifest.json`, require `final_parquet.row_count` to equal the YAML row count, download `final.parquet`, and require its SHA-256 to match the manifest. Print `accepted {feature} manifest sha256={digest}` for each accepted manifest.

### Join

Keep the existing Twitter-local DuckDB join. `read_csv` for posts, `read_parquet` for features. Inner join on `CAST(source_record_id AS VARCHAR)`. Select only the 21 contract columns, in contract order. Sort `source_record_id ASC`. Duplicate feature ids keep the latest `label_timestamp`. Do not import or call `build_llm_campaign_wide_table`. Do not use Bluesky `PREPROCESSED_WIDE_COLUMNS` or `EXPECTED_WIDE_ROW_COUNT`.

### Validate

Raise if column names or order differ, if row count is not the YAML row count, if distinct `source_record_id` is not that count, if sort is not ascending, if any of the seven label columns has nulls, or if a forbidden column is present.

### Wide upload and curation

Keep the existing wide upload and MirrorView curation. Curated files stay under the dataset `curated/` stage as `mirrorview.parquet` plus `metadata.json`. Do not write under `wide/curated/`. Do not use `BlueskyStorageManager`. Do not change filter YAML semantics.

### Stdout

Print each accepted manifest digest, then:

- `wide_rows=6408` for this campaign
- `wide_columns=21`
- `sort_key=source_record_id ASC`
- `manifest=` plus the wide manifest URI
- `curated_rows=` plus the filtered count
- `curated=` plus the curated parquet URI
- `curated_crosstab_political_stance_by_llm_toxicity_tier=` plus the JSON table

## Implement-from-spec phases

Phase 1 is this scope block.

Phase 2 and Phase 3: add `expected_row_count` to `CampaignConsolidateArgs`. Add a helper that loads the campaign YAML and raises when CLI dataset id or preprocessed run disagrees. Keep existing join and curate bodies. Full auto, so do not wait. Commit.

Phase 4: write the given/when/then live checks in the module docstring. Do not add `tests/`. Commit.

Phase 5 units of work, in this order, one commit each:

1. Load campaign YAML, fail on CLI identity mismatch, and thread `expected_row_count` through manifest checks, wide validation, and the wide manifest. Remove `TWITTER_EXPECTED_WIDE_ROW_COUNT`.

Phase 6: checklist. The live commands in Step 2 are the designed checks. Do not run pytest.

## Given / when / then (Phase 4)

given campaign YAML row_count 6408, seven feature manifests whose final.parquet SHA-256 and row_count are 6408, and posts.csv whose SHA-256 matches the inventory
when the CLI joins pinned posts on source_record_id with matching dataset id and preprocessed run
then stdout includes each accepted manifest digest, wide_rows=6408, wide_columns=21, sort_key=source_record_id ASC, and the wide manifest URI

given CLI --dataset-id or --preprocessed-run that disagrees with the campaign YAML
when parse_args or run_campaign_consolidation runs
then it raises ValueError before writing wide/features.parquet

given campaign id twitter_2026_09_06_192847_llm_features_v1
when load_twitter_campaign_config returns that YAML
then expected wide row count is 6374

given a missing or SHA-mismatched feature final.parquet, or a posts.csv SHA-256 that does not match the inventory
when the CLI verifies inputs
then it raises before writing wide/features.parquet

given the uploaded wide parquet
when the columns and row count are checked
then column names match the 21-name contract, n=6408, and no llm_toxicity_tier is null

given the same wide table and data_platform/curate/configs/twitter/mirrorview.yaml
when apply_rules runs
then curated row count and political_stance x llm_toxicity_tier counts are written under the dataset curated/ stage, in a timestamped run directory, as mirrorview.parquet plus metadata.json

## Pass

- Expected row count for the new campaign is 6408 from YAML, not a module constant of 6374.
- CLI dataset id or preprocessed run that disagrees with YAML raises before the join.
- Old campaign YAML still yields expected 6374.
- Path building uses `FeaturePaths.for_campaign` with platform `twitter`.
- Posts load from csv. Inventory SHA-256 is checked.
- Join produces 21 columns in contract order.
- Curation uses `TwitterStorageManager` and writes `mirrorview.parquet`.
- No pytest files. No edits to forbidden files.

## Fail

- Expected row count is still the module constant 6374 for the new campaign.
- Left table loaded from parquet.
- `build_llm_campaign_wide_table` is called.
- Bluesky `EXPECTED_WIDE_ROW_COUNT` is changed.
- Curated files land under `wide/curated/` or through `BlueskyStorageManager`.
- Filter YAML semantics changed.
- Any file under `tests/` is added or edited.
