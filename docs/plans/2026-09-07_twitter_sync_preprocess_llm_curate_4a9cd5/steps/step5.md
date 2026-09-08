# Step 5: Join seven Twitter LLM features and write the MirrorView curated export

## Goal

Operators need one wide table and a MirrorView export for the new campaign, so the implementer joins seven verified `final.parquet` files to the new preprocessed `posts.csv` on `source_record_id`, uploads `wide/features.parquet`, and writes a curated run through `data_platform/curate/configs/twitter/mirrorview.yaml`.

## Dependencies

- **Step 4 merged** on the GitHub stack: seven features each have `final.parquet` with `{row_count}` unique ids and a matching `manifest.json`.
- Step 3 identities and S3 csv must still match the new inventory hash.

Replace `{campaign_id}`, `{preprocessed_run}`, and `{row_count}` from the Step 3 campaign YAML.

## Caller / unit of work

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run {preprocessed_run} \
  --campaign-id {campaign_id} \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/{campaign_id}/wide/features.parquet
```

**One implementation scope:** change `consolidate_twitter_llm_campaign.py` so expected wide row count comes from `load_twitter_campaign_config(campaign_id)["row_count"]`, not `TWITTER_EXPECTED_WIDE_ROW_COUNT = 6374`. Require CLI `--dataset-id` and `--preprocessed-run` to match that YAML. Download the new dataset's `posts.csv` (not parquet). Verify each feature manifest `row_count={row_count}` and SHA-256 of `final.parquet`. Inner-join on `source_record_id` to the 21-column contract. Upload `wide/features.parquet` and `wide/manifest.json`. Run `apply_rules` with `twitter/mirrorview.yaml`. Write curated output with `TwitterStorageManager("curated", dataset_id)`. Write `reports/wide_run_report.md` with curated row count and `political_stance` × `llm_toxicity_tier` crosstab.

Resolve prefixes with `FeaturePaths.for_campaign(..., platform="twitter", dataset_id=...)`. Left table is csv. Parquet campaign objects may need `CampaignObjectStore` because dataset format is csv.

Reuse join helpers from `data_platform/curate/consolidate.py` only where they already take column lists. Do not change Bluesky `PREPROCESSED_WIDE_COLUMNS` or `EXPECTED_WIDE_ROW_COUNT = 200000`. Do not change `twitter/mirrorview.yaml` filter semantics.

**Out of scope:** relabeling features, pytest, GitHub posting, lifecycle rules, converting the dated dataset to parquet.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/curate/consolidate_twitter_llm_campaign.py` | Hardcoded `TWITTER_EXPECTED_WIDE_ROW_COUNT = 6374` |
| `/workspace/data_platform/generate_features/twitter_campaign_config.py` | Directory loader from Step 3 |
| `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml` | New `row_count` |
| `/workspace/data_platform/curate/consolidate.py` | `LLM_CAMPAIGN_FEATURE_NAMES`, feature aliases |
| `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml` | Filter set. Do not edit. |
| `/workspace/data_platform/utils/storage.py` | `TwitterStorageManager` |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `FeaturePaths.for_campaign` |
| `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/campaign_contract.md` | 21-column contract |

## Files allowed to change

- `/workspace/data_platform/curate/consolidate_twitter_llm_campaign.py`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/wide_run_report.md` (new)
- `/workspace/CHANGELOG.md`

Do not edit other plan files except this step file when correcting the spec.

## Files forbidden to change

- `/workspace/data_platform/curate/consolidate.py` unless a tiny helper must accept a column list without changing Bluesky behavior. Prefer keeping Twitter columns inside the Twitter module.
- `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/generate_features/**`
- `/workspace/tests/**`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/plan.md`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/steps/step1.md`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/steps/step2.md`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/steps/step3.md`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/steps/step4.md`

## Locked contracts

Wide file: exactly 21 columns in this order.

`tweet_id`, `record_id`, `url`, `username`, `author_handle`, `text`, `created_at`, `like_count`, `retweet_count`, `reply_count`, `quote_count`, `keyword`, `sync_timestamp`, `source_record_id`, `news_or_opinion_category`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tier`

Row count: campaign YAML `row_count`. Distinct `source_record_id`: that same count. Sort: `source_record_id ASC`. No nulls in the seven label columns.

Wide manifest links all seven feature manifests plus the preprocessed csv SHA-256 from `data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/s3_preprocessed_inventory.json`.

Forbidden wide columns: `toxicity_prob`, `toxicity_tier`, any `is_toxic_tiered` field, `label_timestamp`, `run_id`, `author_id`.

Left table key:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/posts.csv`

Read that object as csv. Do not require `posts.parquet`.

Curation: `TwitterStorageManager("curated", dataset_id)` writes `curated/<timestamp>/mirrorview.parquet` plus `metadata.json`. Filename stem is `mirrorview` from the YAML.

Re-running the consolidator against campaign id `twitter_2026_09_06_192847_llm_features_v1` must still expect 6374 rows, because that YAML still says `row_count: 6374`. Do not leave a module constant that forces 6374 for every Twitter campaign.

## Ordered implementation work

1. Load expected row count from `load_twitter_campaign_config`. Fail if CLI dataset id or preprocessed run disagrees with the YAML.
2. Verify seven manifests before writing wide output.
3. Join, upload wide parquet and manifest.
4. Apply MirrorView rules. Write curated run.
5. Write `reports/wide_run_report.md` with curated row count and the stance by toxicity crosstab for rows that survive the filters.
6. Run the runtime checks below.

## Exact commands and expected output

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run {preprocessed_run} \
  --campaign-id {campaign_id} \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/{campaign_id}/wide/features.parquet
```

Expected stdout includes each accepted manifest digest, `wide_rows={row_count}`, `wide_columns=21`, `sort_key=source_record_id ASC`, the wide manifest URI, `curated_rows=...`, and `curated_crosstab_political_stance_by_llm_toxicity_tier=` JSON.

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/{campaign_id}/wide/features.parquet /tmp/twitter_2026_09_07_wide.parquet
PYTHONPATH=. uv run python - <<'PY'
import pyarrow.parquet as pq
t = pq.read_table("/tmp/twitter_2026_09_07_wide.parquet")
want = [
    "tweet_id","record_id","url","username","author_handle","text","created_at",
    "like_count","retweet_count","reply_count","quote_count","keyword","sync_timestamp",
    "source_record_id","news_or_opinion_category","is_political","is_likely_spam",
    "is_self_contained","is_structurally_complete","political_stance","llm_toxicity_tier",
]
assert t.column_names == want, t.column_names
print("wide ok", t.num_rows, len(t.column_names))
PY
```

Expected: `wide ok {row_count} 21`.

The pull request body and `wide_run_report.md` must include the curated crosstab of `political_stance` × `llm_toxicity_tier` for curated rows.

Do not add pytest.

## Pass / fail

The step passes when `wide/features.parquet` has `{row_count}` rows, 21 columns, and no missing feature values; the wide manifest links seven feature manifests and the new csv hash; MirrorView curation writes `curated/<timestamp>/mirrorview.parquet` through `TwitterStorageManager`; and the committed report includes curated row count plus the stance by toxicity crosstab.

The step fails when any item below is true.

- expected row count is still the module constant 6374 for the new campaign
- left table loaded from parquet or from a converted copy of `posts.csv`
- wide column order differs from the contract
- Bluesky `EXPECTED_WIDE_ROW_COUNT` is changed
- join uses `tweet_id` instead of `source_record_id`
- curated files land under `wide/curated/` or through `BlueskyStorageManager`
- filter YAML semantics changed
- pytest was added

## PR artifact and commit rules

- One independently mergeable PR stacked on Step 4.
- Logical commits: consolidator row-count source, live run report, changelog.
- PR title suggestion: `Join seven Twitter LLM features and write the MirrorView curated export`.
