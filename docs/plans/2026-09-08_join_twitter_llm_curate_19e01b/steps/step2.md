# Step 2: Run the live join and write the report

## Scope

- **Caller:** the same consolidator `main` from Step 1, then the parquet assertion snippet below.
- **Task:** Run the live consolidation against the locked campaign, confirm stdout and the downloaded wide parquet, copy logs to `/opt/cursor/artifacts/`, and write the wide run report with curated row count and the stance by toxicity table.
- **Out of scope:** pytest, editing the consolidator after a green run except for docstring fixes required by `write-docstring`, editing forbidden product files.

## Files to inspect (read-only)

- `/workspace/data_platform/curate/consolidate_twitter_llm_campaign.py`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/wide_run_report.md`

## Files allowed to change

- `/workspace/docs/plans/2026-09-08_join_twitter_llm_curate_19e01b/reports/wide_run_report.md` (new)

## Files forbidden to change

- `/workspace/data_platform/curate/consolidate.py`
- `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/generate_features/**`
- `/workspace/tests/**`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`

## Live commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/curate/consolidate_twitter_llm_campaign.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run 2026_09_08-01:48:08 \
  --campaign-id twitter_2026_09_08_014808_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/wide/features.parquet
```

Expected stdout includes each accepted manifest digest, `wide_rows=6408`, `wide_columns=21`, `sort_key=source_record_id ASC`, the wide manifest URI, `curated_rows=`, the curated parquet URI, and the stance by toxicity JSON table.

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/wide/features.parquet /tmp/twitter_2026_09_08_wide.parquet
PYTHONPATH=. uv run python - <<'PY'
import pyarrow.parquet as pq
t = pq.read_table("/tmp/twitter_2026_09_08_wide.parquet")
want = [
    "tweet_id","record_id","url","username","author_handle","text","created_at",
    "like_count","retweet_count","reply_count","quote_count","keyword","sync_timestamp",
    "source_record_id","news_or_opinion_category","is_political","is_likely_spam",
    "is_self_contained","is_structurally_complete","political_stance","llm_toxicity_tier",
]
assert t.column_names == want, t.column_names
assert t.num_rows == 6408
print("wide ok", t.num_rows, len(t.column_names))
PY
```

Expected: `wide ok 6408 21`.

Also list the curated prefix:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/curated/
```

Copy consolidator stdout, wide validation, curated S3 listing, and the crosstab to `/opt/cursor/artifacts/`.

## Report

Write `/workspace/docs/plans/2026-09-08_join_twitter_llm_curate_19e01b/reports/wide_run_report.md` in the same shape as `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/wide_run_report.md`. It must include:

- Pinned dataset id, preprocessed run, campaign id, 6408, 21 columns
- Preprocessed csv SHA-256
- Seven feature manifest and final.parquet SHA-256 values
- Wide parquet and wide manifest URIs and SHA-256 values
- Curated row count
- Curated parquet and metadata URIs and SHA-256 values
- Filter pass counts from YAML order
- Crosstab of valid curated rows: `political_stance` rows `left` and `right` by `llm_toxicity_tier` columns `low`, `medium`, `high`, plus totals

The crosstab is required. Do not omit it.

## Pass

- Live consolidator stdout matches the contract.
- Downloaded wide parquet has 6408 rows and 21 named columns in order.
- Report is committed with curated row count and the full stance by toxicity table.
- Artifact logs exist under `/opt/cursor/artifacts/`.

## Fail

- Wide column order differs from the contract.
- Report omits the crosstab or the curated row count.
- Curated objects are missing from S3.
- pytest is added or run.
