# Step 15: Consolidate seven Bluesky LLM features into one wide Parquet artifact

## Goal

Join the seven verified S3-backed LLM feature outputs to all twelve pinned preprocessed post columns by `source_record_id`. Write one deterministic wide Parquet file with exactly 200,000 unique rows and no missing feature values, plus a SHA-256 manifest and one permanent consolidation report. Exclude all Perspective API columns.

This step is one future pull request. Unlike Steps 8 through 14, this PR may change consolidation code. It does not run LLM labeling and does not add temporary smoke artifacts.

## Dependencies

Do not start until all of the following are merged. See `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md`.

| Dependency | Requirement |
|------------|-------------|
| Step 8 + `reports/is_news_or_opinion_run_report.md` | Final `is_news_or_opinion/final.parquet` verified at 200000 rows |
| Step 9 + `reports/is_political_run_report.md` | Final `is_political/final.parquet` verified at 200000 rows |
| Step 10 + `reports/is_likely_spam_run_report.md` | Final `is_likely_spam/final.parquet` verified at 200000 rows |
| Step 11 + `reports/is_self_contained_run_report.md` | Final `is_self_contained/final.parquet` verified at 200000 rows |
| Step 12 + `reports/is_structurally_complete_run_report.md` | Final `is_structurally_complete/final.parquet` verified at 200000 rows |
| Step 13 + `reports/political_stance_run_report.md` | Final `political_stance/final.parquet` verified at 200000 rows |
| Step 14 + `reports/llm_toxicity_tiered_run_report.md` | Final `llm_toxicity_tiered/final.parquet` verified; no Perspective run |

Each merged feature report must list the final S3 URI and manifest digest used as inputs here.

## Main caller and implementation slice

**Main caller:** `data_platform/curate/consolidate_bluesky_llm_campaign.py` (new CLI introduced in this step).

**Task:** read pinned preprocessed Parquet and seven `final.parquet` files from S3, build the wide table, validate row completeness, upload `wide/features.parquet` and `wide/manifest.json`, and commit `reports/wide_run_report.md`.

**Out of scope:** Re-running any feature campaign, changing feature prompts or engines, curation rule application, automated tests, temporary smoke artifacts, or edits to completed feature run reports.

## Pinned identities

| Field | Value |
|-------|-------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Join key | `source_record_id` |
| Expected row count | `200000` |
| Deterministic sort | `ORDER BY source_record_id ASC` |

Feature root:

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/`

Preprocessed input:

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet`

Feature inputs (`final.parquet` only):

| Feature | S3 object |
|---------|-----------|
| `is_news_or_opinion` | `.../is_news_or_opinion/final.parquet` |
| `is_political` | `.../is_political/final.parquet` |
| `is_likely_spam` | `.../is_likely_spam/final.parquet` |
| `is_self_contained` | `.../is_self_contained/final.parquet` |
| `is_structurally_complete` | `.../is_structurally_complete/final.parquet` |
| `political_stance` | `.../political_stance/final.parquet` |
| `llm_toxicity_tiered` | `.../llm_toxicity_tiered/final.parquet` |

Wide outputs:

| Object | Path |
|--------|------|
| Wide parquet | `.../wide/features.parquet` |
| Wide manifest | `.../wide/manifest.json` |

Repository permanent report:

`/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/wide_run_report.md`

## Wide-table schema

The wide file must contain exactly nineteen columns in this order.

### Twelve preprocessed columns

`uri`, `record_id`, `url`, `author_handle`, `text`, `created_at`, `like_count`, `repost_count`, `reply_count`, `quote_count`, `sync_timestamp`, `source_record_id`

### Seven aliased label columns

| Wide column | Source feature | Source column | Accepted values |
|-------------|----------------|---------------|-----------------|
| `news_or_opinion_category` | `is_news_or_opinion` | `category` | `news`, `opinion`, `neither` |
| `is_political` | `is_political` | `is_political` | boolean |
| `is_likely_spam` | `is_likely_spam` | `is_likely_spam` | boolean |
| `is_self_contained` | `is_self_contained` | `is_self_contained` | boolean |
| `is_structurally_complete` | `is_structurally_complete` | `is_structurally_complete` | boolean |
| `political_stance` | `political_stance` | `political_stance` | `left`, `right`, `neutral`, `unclear` |
| `llm_toxicity_tier` | `llm_toxicity_tiered` | `toxicity_tier` | `low`, `medium`, `high` |

Forbidden wide columns: `toxicity_prob`, `toxicity_tier`, any `is_toxic_tiered` field, `label_timestamp`, `run_id`, or duplicate feature-id columns.

Join rule: inner join preprocessed posts to each feature file on `CAST(source_record_id AS VARCHAR)`. Deduplicate feature rows by latest `label_timestamp` per `source_record_id` before joining.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Wide schema and input paths |
| `/workspace/data_platform/curate/consolidate.py` | Existing DuckDB join pattern |
| `/workspace/data_platform/curate/runner.py` | Metadata and hash patterns |
| `/workspace/data_platform/models/sync.py` | Twelve preprocessed column names |
| `/workspace/data_platform/generate_features/registry.py` | Raw feature output schemas |
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/*_run_report.md` | Input URIs and manifest digests from Steps 8 through 14 |
| `/workspace/AGENTS.md` | AWS credential export, `PYTHONPATH=.` |

## Files allowed to change

- `/workspace/data_platform/curate/consolidate.py` (add campaign-wide column map including `llm_toxicity_tiered` → `llm_toxicity_tier`)
- `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py` (new CLI)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/wide_run_report.md` (permanent report only)
- S3 objects under `.../wide/`

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/data_platform/generate_features/**`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/*_run_report.md` except cross-links inside the wide report
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- Feature S3 prefixes (read-only inputs)
- Any temporary smoke paths under `reports/smoke/`

## Locked contracts

See `campaign_contract.md`. `wide/manifest.json` must link all seven per-feature `manifest.json` provenance manifests plus preprocessed input hash. Use SHA-256 only; never ETag.

## Ordered implementation work

1. Verify each of the seven feature manifests matches its `final.parquet` SHA-256 and row count 200000.
2. Load only pinned preprocessed run `2026_09_03-23:51:30`.
3. Build wide dataframe with exactly nineteen columns.
4. Sort by `source_record_id` ascending before writing Parquet.
5. Write `wide/features.parquet` and `wide/manifest.json`.
6. Write `reports/wide_run_report.md`.
7. Run runtime validation commands below.

## Exact commands and expected output

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
uv sync
```

### Build and upload wide artifact (available after this step's implementation)

```bash
PYTHONPATH=. uv run python data_platform/curate/consolidate_bluesky_llm_campaign.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/features.parquet
```

Expected stdout includes:

- Seven input manifest digests accepted
- `wide_rows=200000`
- `wide_columns=19`
- `manifest=s3://.../wide/manifest.json`
- `sort_key=source_record_id ASC`

### Runtime validation

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python - <<'PY'
import duckdb

wide = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/features.parquet"
posts = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet"

expected_cols = [
    "uri", "record_id", "url", "author_handle", "text", "created_at",
    "like_count", "repost_count", "reply_count", "quote_count",
    "sync_timestamp", "source_record_id",
    "news_or_opinion_category", "is_political", "is_likely_spam",
    "is_self_contained", "is_structurally_complete", "political_stance",
    "llm_toxicity_tier",
]
con = duckdb.connect()
cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{wide}')").fetchall()]
assert cols == expected_cols, cols

stats = con.execute(f"""
SELECT
  COUNT(*) AS n,
  COUNT(DISTINCT source_record_id) AS uniq,
  SUM(CASE WHEN llm_toxicity_tier IS NULL THEN 1 ELSE 0 END) AS null_tox
FROM read_parquet('{wide}')
""").fetchone()
print(stats)
assert stats[0] == 200000 and stats[1] == 200000 and stats[2] == 0

missing = con.execute(f"""
SELECT COUNT(*)
FROM read_parquet('{posts}') p
LEFT JOIN read_parquet('{wide}') w USING (source_record_id)
WHERE w.source_record_id IS NULL
""").fetchone()[0]
assert missing == 0
print("validation ok")
PY
```

Expected: `validation ok` and exit code 0.

### Manifest check

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/wide/manifest.json -
```

Expected: JSON with wide parquet SHA-256, row count 200000, column list, and links to all seven feature manifests.

## Acceptance criteria

- Wide Parquet and manifest exist at `wide/features.parquet` and `wide/manifest.json`.
- Exactly 200000 unique rows, nineteen exact columns, no null feature values.
- Rows sorted by `source_record_id` ascending.
- No Perspective columns or artifacts.
- `reports/wide_run_report.md` committed with input hashes, output hash, and validation evidence.
- No automated tests added or run.

## Failure conditions

- Any missing or unverified feature `final.parquet` input.
- Join on `uri` without aligning `source_record_id`, or outer join leaving null features.
- Row count other than 200000 or duplicate `source_record_id` values.
- Missing, renamed, or extra columns in the wide output.
- Raw `toxicity_tier` wide column instead of `llm_toxicity_tier`.
- Manifest missing links to all seven feature provenance manifests.
- Using `campaigns/` prefix, `bluesky_llm_features_wide.parquet`, or `manifest.sha256.json`.
- Accepting ETag instead of SHA-256 for manifest verification.
- Temporary smoke artifacts added to this PR.
- Any LLM or OpenAI Batch call in this PR.
- Any automated test added or run.

## PR artifact and commit rules

- Commit consolidation code and `reports/wide_run_report.md` only.
- PR title: `Consolidate seven Bluesky LLM features into wide Parquet artifact`
- Do not edit `plan.md` or other step specs.
