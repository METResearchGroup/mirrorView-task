# Step 1: Add the Twitter consolidator

## Scope

- **Caller:** `data_platform/curate/consolidate_twitter_llm_campaign.py` `main`
- **Task:** Download pinned `posts.csv`, verify its SHA-256 against the inventory, verify seven feature manifests at row_count 6374, inner-join on `source_record_id` to the 21-column contract, upload untagged `wide/features.parquet` and `wide/manifest.json`, apply `twitter/mirrorview.yaml`, and write a curated run under the dataset `curated/` stage.
- **Out of scope:** pytest, GitHub posting, relabeling features, converting the dated dataset to parquet, editing Bluesky consolidator code, editing `twitter/mirrorview.yaml`, editing `consolidate.py`, editing `generate_features/**`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py` | Campaign join, manifest checks, stdout, curated write, crosstab |
| `/workspace/data_platform/curate/consolidate.py` | `LLM_CAMPAIGN_FEATURE_NAMES`, `FEATURE_WIDE_COLUMNS` aliases, DuckDB feature CTE pattern. Do not call `build_llm_campaign_wide_table`. |
| `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml` | Filter set. Stem is `mirrorview`. |
| `/workspace/data_platform/utils/storage.py` | `TwitterStorageManager` |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `FeaturePaths.for_campaign`, `CampaignObjectStore` |
| `/workspace/data_platform/curate/apply_rules.py` | `apply_rules`, `load_rules_config` |
| `/workspace/data_platform/curate/runner.py` | `build_curate_metadata` |
| `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/s3_preprocessed_inventory.json` | Expected csv SHA-256 |
| `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md` | 21-column contract |
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/wide_run_report.md` | Report shape |

## Files allowed to change

- `/workspace/data_platform/curate/consolidate_twitter_llm_campaign.py` (new)

## Files forbidden to change

- `/workspace/data_platform/curate/consolidate.py`
- `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/generate_features/**`
- `/workspace/tests/**`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/plan.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step3.md`
- Any file outside the allowed list

## Locked identities

| Field | Value |
|-------|-------|
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Preprocessed run | `2026_09_06-19:28:47` |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Left table | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv` |
| Inventory SHA-256 | `7233223b21210d0937372d9d906abfd914962784402d6b167805952a7415fa4a` |
| Wide rows | `6374` |
| Wide columns | `21` |
| Sort | `source_record_id ASC` |
| Platform argument | `twitter` |
| Rules | `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml` |

Wide output URI:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/features.parquet`

Wide columns in this exact order:

`tweet_id`, `record_id`, `url`, `username`, `author_handle`, `text`, `created_at`, `like_count`, `retweet_count`, `reply_count`, `quote_count`, `keyword`, `sync_timestamp`, `source_record_id`, `news_or_opinion_category`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tier`

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/features.parquet
```

## Work

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then live checks below, written in the module docstring.

### Path helper

Call `FeaturePaths.for_campaign(campaign_id, feature_name, platform="twitter", dataset_id=dataset_id)`. Do not call `FeaturePaths.canonical`.

### Posts csv

Download the pinned S3 object as csv. Hash full object bytes with SHA-256. Compare to the inventory object for that key. Raise before joining if the hash does not match. Do not load `posts.parquet`. Do not convert the csv to a parquet left table.

### Feature manifests

For each name in `LLM_CAMPAIGN_FEATURE_NAMES`, load `manifest.json`, require `final_parquet.row_count == 6374`, download `final.parquet`, and require its SHA-256 to match the manifest. Print `accepted {feature} manifest sha256={digest}` for each accepted manifest.

### Join

Twitter-local DuckDB: `read_csv` for posts, `read_parquet` for features. Inner join on `CAST(source_record_id AS VARCHAR)`. Select only the 21 contract columns, in contract order. Sort `source_record_id ASC`. Duplicate feature ids keep the latest `label_timestamp`. Reuse `FEATURE_WIDE_COLUMNS` aliases. Do not import or call `build_llm_campaign_wide_table`. Do not use Bluesky `PREPROCESSED_WIDE_COLUMNS` or `EXPECTED_WIDE_ROW_COUNT`.

Posts.csv also has `author_id`. Do not put `author_id` on the wide table.

### Validate

Raise if column names or order differ, if row count is not 6374, if distinct `source_record_id` is not 6374, if sort is not ascending, if any of the seven label columns has nulls, or if a forbidden column is present.

### Wide upload

Upload untagged `wide/features.parquet` and `wide/manifest.json`. The manifest must include dataset id, campaign id, preprocessed run, 6374, the 21 column names, sort key, wide parquet SHA-256, preprocessed csv key and SHA-256, and all seven feature manifest URIs with final parquet SHA-256 and row count.

### Curation

Call `apply_rules` with `twitter/mirrorview.yaml`. Do not change filter semantics.

`TwitterStorageManager("curated", dataset_id)` creates `curated/<timestamp>/` and writes `metadata.json`. The Twitter dataset format is csv, so `filename_for` would return `mirrorview.csv` and `write_dataframe` would write csv bytes. This issue requires `mirrorview.parquet`. Upload parquet bytes to `curated/<timestamp>/mirrorview.parquet` using the campaign object store. Stem `mirrorview` still comes from the YAML. Do not write under `wide/curated/`. Do not use `BlueskyStorageManager`.

Add the stance by toxicity table to curated metadata. Stance rows `left` and `right`. Toxicity columns `low`, `medium`, `high`. Count rows that survive the filters.

### Stdout

Print each accepted manifest digest, then:

- `wide_rows=6374`
- `wide_columns=21`
- `sort_key=source_record_id ASC`
- `manifest=` plus the wide manifest URI
- `curated_rows=` plus the filtered count
- `curated=` plus the curated parquet URI
- `curated_crosstab_political_stance_by_llm_toxicity_tier=` plus the JSON table

## Implement-from-spec phases

Phase 1 is this scope block.

Phase 2: scaffold the module with argparse, dataclasses, and stub bodies (`raise NotImplementedError`). Imports must resolve. Commit.

Phase 3: contracts only. Signatures and frozen dataclasses matching the Bluesky consolidator shape, with Twitter names (`local_csv` for posts, Twitter column tuple, expected row count 6374). Bodies stay stubs. Full auto, so do not wait. Commit.

Phase 4: write the given/when/then live checks in the module docstring. Do not add `tests/`. The CLI must still raise `NotImplementedError` if run. Commit.

Phase 5 units of work, in this order, one commit each:

1. Download and verify posts csv plus seven feature manifests.
2. Twitter DuckDB wide join.
3. Validate the wide table.
4. Curate with MirrorView rules, write parquet and metadata, build the crosstab.
5. Upload wide artifacts, wire `run_campaign_consolidation`, `print_result`, and `main`.

Phase 6: checklist. The live commands in Step 2 are the designed checks. Do not run pytest.

## Given / when / then (Phase 4)

given seven feature manifests whose final.parquet SHA-256 and row_count are 6374, and posts.csv whose SHA-256 matches the inventory
when the CLI joins pinned posts on source_record_id
then stdout includes each accepted manifest digest, wide_rows=6374, wide_columns=21, sort_key=source_record_id ASC, and the wide manifest URI

given a missing or SHA-mismatched feature final.parquet, or a posts.csv SHA-256 that does not match the inventory
when the CLI verifies inputs
then it raises before writing wide/features.parquet

given the uploaded wide parquet
when the columns and row count are checked
then column names match the 21-name contract, n=6374, and no llm_toxicity_tier is null

given the same wide table and data_platform/curate/configs/twitter/mirrorview.yaml
when apply_rules runs
then curated row count and political_stance x llm_toxicity_tier counts are written under the dataset curated/ stage, in a timestamped run directory, as mirrorview.parquet plus metadata.json

## Pass

- The module exists and the main caller parses the four required flags.
- Path building uses `FeaturePaths.for_campaign` with platform `twitter`.
- Posts load from csv. Inventory SHA-256 is checked.
- Join produces 21 columns in contract order.
- Curation uses `TwitterStorageManager` and writes `mirrorview.parquet`.
- No pytest files. No edits to forbidden files.

## Fail

- Left table loaded from parquet.
- `build_llm_campaign_wide_table` is called.
- `FeaturePaths.canonical` is called.
- Bluesky `EXPECTED_WIDE_ROW_COUNT` is changed.
- Curated files land under `wide/curated/` or through `BlueskyStorageManager`.
- Curated export is `mirrorview.csv`.
- A mismatched feature hash is accepted.
- Any file under `tests/` is added or edited.
