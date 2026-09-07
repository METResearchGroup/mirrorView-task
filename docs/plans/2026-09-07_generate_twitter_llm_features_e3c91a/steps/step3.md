# Step 3: Consolidate seven Twitter LLM features and write the MirrorView curated export

## Goal

Operators need one wide table and a MirrorView export, so the implementer joins seven verified `final.parquet` files to pinned preprocessed `posts.csv` on `source_record_id`, uploads `wide/features.parquet`, and writes a curated run through `data_platform/curate/configs/twitter/mirrorview.yaml`.

## Dependencies

- **Step 2 merged** on the GitHub stack: seven features each have `final.parquet` with 6,374 unique ids and a matching `manifest.json`.
- Step 1 identities and S3 csv must still match the inventory hash.

## Main caller and implementation scope

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/features.parquet
```

**One implementation scope:** add `consolidate_twitter_llm_campaign.py`. Download pinned `posts.csv` (not parquet). Verify each feature manifest `row_count=6374` and SHA-256 of `final.parquet`. Inner-join on `source_record_id` to the 21-column contract. Upload `wide/features.parquet` and `wide/manifest.json`. Run `apply_rules` with `twitter/mirrorview.yaml`. Write curated output with `TwitterStorageManager("curated", dataset_id)`. Write `reports/wide_run_report.md`.

Reuse join helpers from `data_platform/curate/consolidate.py` only where they already take column lists. Do not change Bluesky `PREPROCESSED_WIDE_COLUMNS` or `EXPECTED_WIDE_ROW_COUNT = 200000`. Do not change `twitter/mirrorview.yaml` filter semantics.

**Out of scope:** relabeling features, pytest, GitHub posting, lifecycle rules, converting the dated dataset to parquet.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py` | Campaign join, manifest checks, curation write |
| `/workspace/data_platform/curate/consolidate.py` | `LLM_CAMPAIGN_FEATURE_NAMES`, feature aliases |
| `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml` | Filter set |
| `/workspace/data_platform/utils/storage.py` | `TwitterStorageManager` |
| `/workspace/data_platform/models/sync.py` | `PreprocessedTwitterPostModel` |
| `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md` | 21-column contract |

## Files allowed to change

- `/workspace/data_platform/curate/consolidate_twitter_llm_campaign.py` (new)
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/wide_run_report.md` (new)
- `/workspace/CHANGELOG.md`

Do not edit other plan files except this step file when correcting the spec.

## Files forbidden to change

- `/workspace/data_platform/curate/consolidate.py` unless a tiny helper must accept a column list without changing Bluesky behavior. Prefer keeping Twitter columns inside the new module.
- `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/generate_features/**`
- `/workspace/tests/**`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/plan.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`

## Locked contracts

Wide file: exactly 21 columns in this order.

`tweet_id`, `record_id`, `url`, `username`, `author_handle`, `text`, `created_at`, `like_count`, `retweet_count`, `reply_count`, `quote_count`, `keyword`, `sync_timestamp`, `source_record_id`, `news_or_opinion_category`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tier`

Row count: `6374`. Distinct `source_record_id`: `6374`. Sort: `source_record_id ASC`. No nulls in the seven label columns.

Wide manifest links all seven feature manifests plus the preprocessed csv SHA-256 from `s3_preprocessed_inventory.json`.

Forbidden wide columns: `toxicity_prob`, `toxicity_tier`, any `is_toxic_tiered` field, `label_timestamp`, `run_id`, `author_id`.

Left table key:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv`

Read that object as csv. Do not require `posts.parquet`.

Curation: `TwitterStorageManager("curated", dataset_id)` writes `curated/<timestamp>/mirrorview.parquet` plus `metadata.json`. Filename stem is `mirrorview` from the YAML.

## Ordered implementation work

1. Add `consolidate_twitter_llm_campaign.py` with Twitter column lists and csv left-table load.
2. Verify seven manifests before writing wide output.
3. Join, upload wide parquet and manifest.
4. Apply MirrorView rules. Write curated run.
5. Write `reports/wide_run_report.md` with curated row count and `political_stance` by `llm_toxicity_tier` crosstab for rows that survive the filters.
6. Run the runtime checks below.

## Live smoke and basic check commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/features.parquet
```

Expected stdout includes each accepted manifest digest, `wide_rows=6374`, `wide_columns=21`, `sort_key=source_record_id ASC`, and the wide manifest URI.

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/wide/features.parquet /tmp/twitter_wide.parquet
PYTHONPATH=. uv run python - <<'PY'
import pyarrow.parquet as pq
t = pq.read_table("/tmp/twitter_wide.parquet")
want = [
    "tweet_id","record_id","url","username","author_handle","text","created_at",
    "like_count","retweet_count","reply_count","quote_count","keyword","sync_timestamp",
    "source_record_id","news_or_opinion_category","is_political","is_likely_spam",
    "is_self_contained","is_structurally_complete","political_stance","llm_toxicity_tier",
]
assert t.column_names == want, t.column_names
assert t.num_rows == 6374
print("wide ok", t.num_rows, len(t.column_names))
PY
```

Expected: `wide ok 6374 21`.

## Acceptance criteria

- `wide/features.parquet` has exactly 6,374 rows, 21 columns, and no missing feature values.
- `wide/manifest.json` links all seven feature manifests and the preprocessed csv hash.
- MirrorView curation writes `curated/<timestamp>/mirrorview.parquet` and `metadata.json` through `TwitterStorageManager`.
- `reports/wide_run_report.md` is committed with curated row count and the stance by toxicity crosstab.
- Filter YAML semantics are unchanged.
- No pytest added or run.

## Failure conditions

- Left table loaded from parquet or from a converted copy of `posts.csv`.
- Wide column order differs from the contract.
- Bluesky `EXPECTED_WIDE_ROW_COUNT` is changed.
- Join uses `tweet_id` instead of `source_record_id`.
- Curated files land under `wide/curated/` or through `BlueskyStorageManager`.
- Any feature `final.parquet` with a mismatched hash is accepted.

## PR artifact and commit rules

- One independently mergeable PR for this step only, stacked on Step 2.
- Logical commits: consolidator module, live run report, changelog.
- PR title suggestion: `Join seven Twitter LLM features and write the MirrorView export`.

## GitHub issue body

Join seven verified Twitter LLM feature `final.parquet` files to pinned preprocessed `posts.csv` on `source_record_id`. Write untagged `wide/features.parquet` and `wide/manifest.json` for campaign `twitter_2026_09_06_192847_llm_features_v1` with 6374 rows and 21 columns. Apply `data_platform/curate/configs/twitter/mirrorview.yaml` and write `curated/<timestamp>/mirrorview.parquet` plus `metadata.json` through `TwitterStorageManager("curated", dataset_id)`. The work depends on Step 2 merged with verified `final.parquet` at 6374 rows each.

Plan step: `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step3.md`

Done when:

- `wide/features.parquet` has exactly 6374 rows, 21 columns, and no missing feature values.
- `wide/manifest.json` links all seven feature manifests and the preprocessed input hash.
- MirrorView curation writes `curated/<timestamp>/mirrorview.parquet` and `metadata.json`.
- `reports/wide_run_report.md` is committed with curated row count and `political_stance` by `llm_toxicity_tier` crosstab.

Ship as one PR. Do not bundle with sibling issues.

## Pull request description

# Join seven Twitter LLM features and write the MirrorView export

Fixes #<child>

Part of #<parent>

## Summary

Adds `consolidate_twitter_llm_campaign.py` to join seven verified `final.parquet` files to pinned preprocessed Twitter csv, upload `wide/features.parquet` with a SHA-256 manifest, and write a MirrorView curated export for dataset `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547`.

## Purpose

Step 2 leaves seven isolated feature prefixes. MirrorView needs one 21-column table and the existing Twitter filter YAML.

## How to run

See the main caller in the step file.

Expected: `wide_rows=6374`, `wide_columns=21`, plus a timestamped `mirrorview.parquet` under the dataset `curated/` stage.
