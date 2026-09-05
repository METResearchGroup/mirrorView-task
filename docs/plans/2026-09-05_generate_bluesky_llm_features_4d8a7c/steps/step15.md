# Step 15: Consolidate seven Bluesky LLM features into one wide Parquet artifact

## Goal

Join the seven verified S3-backed LLM feature outputs to all twelve pinned preprocessed post columns by `source_record_id`. Write one deterministic wide Parquet file with exactly 200,000 unique rows and no missing feature values, plus a SHA-256 manifest and one permanent consolidation report. Exclude all Perspective API columns.

This step is one future pull request. Unlike Steps 8–14, this PR may change consolidation code. It does not run LLM labeling and does not add temporary smoke artifacts.

## Caller / unit of work

**Main caller:** `data_platform/curate/consolidate_bluesky_llm_campaign.py` (new CLI introduced in this step).

**Task:** read pinned preprocessed Parquet and seven final campaign feature Parquet files from S3, build the wide table, validate row completeness, upload the wide artifact and manifest, and commit the permanent report.

**Out of scope:** Re-running any feature campaign, changing feature prompts or engines, curation rule application, automated tests, temporary smoke artifacts, or edits to completed feature run reports.

## Dependencies

Do not start this PR until all of the following are merged:

| Dependency | Requirement |
|------------|-------------|
| Steps 3–7 | S3 backend, campaign layout, manifests, and progress conventions |
| Step 8 PR + merged `is_news_or_opinion_REPORT.md` | Final feature Parquet verified at 200000 rows |
| Step 9 PR + merged `is_political_REPORT.md` | Final feature Parquet verified at 200000 rows |
| Step 10 PR + merged `is_likely_spam_REPORT.md` | Final feature Parquet verified at 200000 rows |
| Step 11 PR + merged `is_self_contained_REPORT.md` | Final feature Parquet verified at 200000 rows |
| Step 12 PR + merged `is_structurally_complete_REPORT.md` | Final feature Parquet verified at 200000 rows |
| Step 13 PR + merged `political_stance_REPORT.md` | Final feature Parquet verified at 200000 rows |
| Step 14 PR + merged `llm_toxicity_tiered_REPORT.md` | Final feature Parquet verified at 200000 rows; no Perspective run |

Each merged feature report must list the final S3 URI and manifest digest used as inputs here.

## Pinned identities

| Field | Value |
|-------|-------|
| Dataset ID | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Campaign prefix | `bluesky_2026_09_03_235130_llm_features_v1` |
| Join key | `source_record_id` |
| Expected row count | `200000` |
| Deterministic sort | `ORDER BY source_record_id ASC` |

Campaign root:

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/`

Preprocessed input:

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet`

Feature inputs (final Parquet only):

| Feature | S3 final object |
|---------|-----------------|
| `is_news_or_opinion` | `.../is_news_or_opinion/final/is_news_or_opinion.parquet` |
| `is_political` | `.../is_political/final/is_political.parquet` |
| `is_likely_spam` | `.../is_likely_spam/final/is_likely_spam.parquet` |
| `is_self_contained` | `.../is_self_contained/final/is_self_contained.parquet` |
| `is_structurally_complete` | `.../is_structurally_complete/final/is_structurally_complete.parquet` |
| `political_stance` | `.../political_stance/final/political_stance.parquet` |
| `llm_toxicity_tiered` | `.../llm_toxicity_tiered/final/llm_toxicity_tiered.parquet` |

Wide outputs:

| Object | Path |
|--------|------|
| Wide Parquet | `.../wide/bluesky_llm_features_wide.parquet` |
| SHA-256 manifest | `.../wide/manifest.sha256.json` |

Repository permanent report:

`/workspace/docs/reports/bluesky_2026_09_03_235130_llm_features_v1/WIDE_CONSOLIDATION_REPORT.md`

## Wide-table schema

The wide file must contain exactly these nineteen columns in this order:

### Twelve preprocessed columns (exact names, no extras)

From `PreprocessedBlueskyPostModel` / pinned preprocessed Parquet:

1. `uri`
2. `record_id`
3. `url`
4. `author_handle`
5. `text`
6. `created_at`
7. `like_count`
8. `repost_count`
9. `reply_count`
10. `quote_count`
11. `sync_timestamp`
12. `source_record_id`

### Seven LLM feature columns

| Wide column | Source feature file | Source column | Accepted values |
|-------------|--------------------|--------------|-----------------|
| `news_or_opinion_category` | `is_news_or_opinion` | `category` | `news`, `opinion`, `neither` |
| `is_political` | `is_political` | `is_political` | boolean |
| `is_likely_spam` | `is_likely_spam` | `is_likely_spam` | boolean |
| `is_self_contained` | `is_self_contained` | `is_self_contained` | boolean |
| `is_structurally_complete` | `is_structurally_complete` | `is_structurally_complete` | boolean |
| `political_stance` | `political_stance` | `political_stance` | `left`, `right`, `neutral`, `unclear` |
| `llm_toxicity_tier` | `llm_toxicity_tiered` | `toxicity_tier` | `low`, `medium`, `high` |

Forbidden wide columns: `toxicity_prob`, `toxicity_tier` as a standalone wide name, any `is_toxic_tiered` field, `label_timestamp`, or duplicate feature-id columns.

Join rule: inner join preprocessed posts to each feature file on `CAST(source_record_id AS VARCHAR)`. Deduplicate feature rows by latest `label_timestamp` per `source_record_id` before joining, matching the dedupe semantics in `data_platform/curate/consolidate.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Step 15 scope |
| `/workspace/data_platform/curate/consolidate.py` | Existing DuckDB join and `FEATURE_WIDE_COLUMNS` pattern |
| `/workspace/data_platform/curate/runner.py` | Metadata and hash patterns |
| `/workspace/data_platform/models/sync.py` | Twelve preprocessed column names |
| `/workspace/data_platform/generate_features/registry.py` | Raw feature output schemas |
| `/workspace/docs/reports/bluesky_2026_09_03_235130_llm_features_v1/*_REPORT.md` | Input URIs and manifest digests from Steps 8–14 |
| `/workspace/AGENTS.md` | AWS credential export, `PYTHONPATH=.` |

## Files allowed to change

- `/workspace/data_platform/curate/consolidate.py` (add campaign-wide column map including `llm_toxicity_tiered -> llm_toxicity_tier`; keep `is_toxic_tiered` out of the Bluesky campaign map)
- `/workspace/data_platform/curate/consolidate_bluesky_llm_campaign.py` (new CLI: read S3 campaign inputs, write wide Parquet + manifest, print validation summary)
- `/workspace/docs/reports/bluesky_2026_09_03_235130_llm_features_v1/WIDE_CONSOLIDATION_REPORT.md` (permanent report only)
- S3 objects under `.../wide/`

Optional README note in `/workspace/data_platform/README.md` only if needed to document the new CLI; keep the diff minimal.

Do not edit the plan package during implementation.

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/data_platform/generate_features/**`
- `/workspace/docs/reports/bluesky_2026_09_03_235130_llm_features_v1/*_REPORT.md` except adding cross-links inside the new wide report
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- Feature S3 prefixes under the seven feature folders (read-only inputs)
- Any temporary smoke paths under `docs/reports/.../smoke/`

## Consolidation behavior

1. Verify each of the seven feature manifests matches its final Parquet SHA-256 and row count 200000 before joining.
2. Load only the pinned preprocessed run, not every preprocess directory on the dataset.
3. Build the wide dataframe with exactly the nineteen columns listed above.
4. Sort rows by `source_record_id` ascending before writing Parquet.
5. Write `bluesky_llm_features_wide.parquet` to the wide S3 prefix.
6. Write `manifest.sha256.json` covering the wide Parquet bytes and listing constituent input object hashes copied from the seven feature manifests plus the preprocessed input hash.
7. Fail the CLI with non-zero exit if any validation check below fails.

No LLM calls. No batch jobs. No temporary artifacts committed to the repo beyond the permanent report.

## Exact commands

From the repo root:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
uv sync
```

### Build and upload wide artifact

```bash
PYTHONPATH=. uv run python data_platform/curate/consolidate_bluesky_llm_campaign.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --output-s3-uri s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/wide/bluesky_llm_features_wide.parquet
```

Expected stdout includes:

- Seven input manifest digests accepted
- `wide_rows=200000`
- `wide_columns=19`
- `manifest=s3://.../wide/manifest.sha256.json`
- `sort_key=source_record_id ASC`

### Runtime validation (required; not automated tests)

Row and column contract:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python - <<'PY'
import duckdb

wide = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/wide/bluesky_llm_features_wide.parquet"
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
  SUM(CASE WHEN source_record_id IS NULL THEN 1 ELSE 0 END) AS null_id,
  SUM(CASE WHEN news_or_opinion_category IS NULL THEN 1 ELSE 0 END) AS null_news,
  SUM(CASE WHEN is_political IS NULL THEN 1 ELSE 0 END) AS null_pol,
  SUM(CASE WHEN is_likely_spam IS NULL THEN 1 ELSE 0 END) AS null_spam,
  SUM(CASE WHEN is_self_contained IS NULL THEN 1 ELSE 0 END) AS null_self,
  SUM(CASE WHEN is_structurally_complete IS NULL THEN 1 ELSE 0 END) AS null_struct,
  SUM(CASE WHEN political_stance IS NULL THEN 1 ELSE 0 END) AS null_stance,
  SUM(CASE WHEN llm_toxicity_tier IS NULL THEN 1 ELSE 0 END) AS null_tox
FROM read_parquet('{wide}')
""").fetchone()
print(stats)
assert stats == (200000, 200000, 0, 0, 0, 0, 0, 0, 0, 0)

missing = con.execute(f"""
SELECT COUNT(*)
FROM read_parquet('{posts}') p
LEFT JOIN read_parquet('{wide}') w USING (source_record_id)
WHERE w.source_record_id IS NULL
""").fetchone()[0]
extra = con.execute(f"""
SELECT COUNT(*)
FROM read_parquet('{wide}') w
LEFT JOIN read_parquet('{posts}') p USING (source_record_id)
WHERE p.source_record_id IS NULL
""").fetchone()[0]
print("missing", missing, "extra", extra)
assert missing == 0 and extra == 0
PY
```

Deterministic order check:

```bash
PYTHONPATH=. uv run python - <<'PY'
import duckdb
wide = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/wide/bluesky_llm_features_wide.parquet"
con = duckdb.connect()
ordered = con.execute(f"""
SELECT source_record_id
FROM read_parquet('{wide}')
""").fetchdf()["source_record_id"].tolist()
sorted_ids = sorted(ordered)
assert ordered == sorted_ids
assert len(ordered) == len(set(ordered))
print("deterministic_order_ok", len(ordered))
PY
```

Accepted-value checks:

```bash
PYTHONPATH=. uv run python - <<'PY'
import duckdb
wide = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/wide/bluesky_llm_features_wide.parquet"
con = duckdb.connect()
assert con.execute(f"SELECT COUNT(*) FROM read_parquet('{wide}') WHERE news_or_opinion_category NOT IN ('news','opinion','neither')").fetchone()[0] == 0
assert con.execute(f"SELECT COUNT(*) FROM read_parquet('{wide}') WHERE political_stance NOT IN ('left','right','neutral','unclear')").fetchone()[0] == 0
assert con.execute(f"SELECT COUNT(*) FROM read_parquet('{wide}') WHERE llm_toxicity_tier NOT IN ('low','medium','high')").fetchone()[0] == 0
for col in ["is_political", "is_likely_spam", "is_self_contained", "is_structurally_complete"]:
    assert con.execute(f"SELECT COUNT(*) FROM read_parquet('{wide}') WHERE {col} IS NULL").fetchone()[0] == 0
print("accepted_values_ok")
PY
```

Forbidden-column check:

```bash
PYTHONPATH=. uv run python - <<'PY'
import duckdb
wide = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/wide/bluesky_llm_features_wide.parquet"
cols = {r[0] for r in duckdb.connect().execute(f"DESCRIBE SELECT * FROM read_parquet('{wide}')").fetchall()}
for forbidden in ["toxicity_prob", "toxicity_tier", "label_timestamp"]:
    assert forbidden not in cols
print("forbidden_columns_absent")
PY
```

Manifest check:

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/wide/manifest.sha256.json -
```

Expected: JSON with `wide_parquet` SHA-256, byte size, row count 200000, column list, deterministic sort key, and nested hashes for preprocessed input plus all seven feature finals.

Perspective absence check:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/is_toxic_tiered/ 2>&1 || true
```

Expected: no objects. Any Perspective campaign prefix fails this step.

## Required outputs

### S3 (permanent)

| Object | Purpose |
|--------|---------|
| `.../wide/bluesky_llm_features_wide.parquet` | Final nineteen-column wide artifact |
| `.../wide/manifest.sha256.json` | SHA-256 manifest for wide file and recorded inputs |

### Repository (permanent only)

| Path | Purpose |
|------|---------|
| `docs/reports/bluesky_2026_09_03_235130_llm_features_v1/WIDE_CONSOLIDATION_REPORT.md` | Input URIs, manifest digests, validation command output, column list, row count, value distributions, explicit statement that Perspective columns are excluded |

No temporary smoke artifacts belong in this PR.

## Acceptance and failure

| Check | Pass | Fail |
|-------|------|------|
| Feature dependencies | All seven feature PRs merged with permanent reports | Any missing or unverified feature final |
| Join key | Inner join on `source_record_id` only | Join on `uri` without aligning `source_record_id`, or outer join leaving null features |
| Row count | Exactly 200000 unique rows, zero nulls in any of the nineteen columns | Any other count, duplicate IDs, or null feature values |
| Preprocessed columns | All twelve exact preprocessed columns present | Missing, renamed, or extra post columns |
| Feature columns | Seven LLM columns with exact wide names listed above | Missing column, Perspective column, or raw `toxicity_tier` wide name |
| Deterministic order | Rows sorted by `source_record_id` ascending in written Parquet | Unsorted or unstable order |
| Manifest | `manifest.sha256.json` matches wide bytes and lists input hashes | Missing or mismatched digest |
| S3 wide path | Written under campaign `.../wide/` prefix | Local-only output or wrong bucket/key |
| Report | Only permanent wide consolidation report committed | Temporary smoke artifacts added |
| Tests | Runtime checks only | New automated tests in this PR |
| Labeling | No LLM or OpenAI Batch calls | Any feature generation rerun |

## Done when

1. Wide Parquet and manifest exist at the pinned S3 wide paths.
2. Runtime validation confirms 200000 unique rows, nineteen exact columns, no null feature values, deterministic `source_record_id` order, and accepted value sets.
3. No Perspective columns or campaign artifacts are present.
4. `WIDE_CONSOLIDATION_REPORT.md` is committed with input hashes, output hash, and validation evidence.
5. Consolidation code changes are merged and documented sufficiently for a repeat run on the same campaign prefix to be reproducible.
