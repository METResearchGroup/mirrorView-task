# Step 14: Generate `llm_toxicity_tiered` for 200,000 Bluesky posts

## Goal

Run the approved S3-backed LLM campaign flow for the LLM toxicity feature `llm_toxicity_tiered` on the pinned 200,000-post Bluesky preprocessed dataset. Keep this output distinct from the Perspective API feature `is_toxic_tiered`. Publish the final feature Parquet file, SHA-256 manifest, progress history, runtime validation results, and one permanent run report under campaign prefix `bluesky_2026_09_03_235130_llm_features_v1`.

This step is one future pull request. It is a run-only PR: no product code changes.

## Caller / unit of work

**Main caller:** `data_platform/generate_features/run_bluesky_llm_campaign.py` (delivered by Steps 4–7).

**Task:** label every pinned input row once with `toxicity_tier` through the `llm_toxicity_tiered` registry entry, using OpenAI Batch at batch size 2000, then verify completeness and publish audit artifacts.

**Out of scope:** Changing feature prompts, registry entries, OpenAI engine code, S3 storage helpers, consolidation logic, curation, running Perspective `is_toxic_tiered`, automated tests, or any file outside the allowed list below.

## Dependencies

Merge and verify these plan steps before opening this PR:

| Step | Requirement |
|------|-------------|
| Step 3 | S3 is the production pipeline backend; pinned preprocessed Parquet is readable from S3 |
| Step 4 | OpenAI Batch jobs persist provider job IDs and resume without duplicate jobs |
| Step 5 | Immutable 2,000-row Parquet shards, final feature Parquet, hash manifest, deterministic order |
| Step 6 | Deterministic ten-post smoke sample, cost estimate artifact, deliberate interrupt/resume check, parent campaign approval gate |
| Step 7 | Durable progress records and rolling GitHub issue comment updates every 10,000 durable rows |

Steps 8–11 are not blockers for starting this feature, but this step follows the same run contract as those steps.

## Pinned identities

Lock every command and artifact to these values. A different dataset, preprocess run, or campaign ID requires a new campaign.

| Field | Value |
|-------|-------|
| Dataset ID | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed input object | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet` |
| Expected input row count | `200000` |
| Campaign prefix | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `llm_toxicity_tiered` (exactly one feature per command) |
| Batch size | `2000` |
| Model ID | `gpt-5.4-nano` (`DEFAULT_LLM_MODEL`) |
| Prompt source | `data_platform/generate_features/llm_toxicity_tiered/generate_feature.py` `SYSTEM_PROMPT` |
| Join key in feature files | `source_record_id` |
| Records id column in preprocessed input | `uri` |
| Forbidden feature | `is_toxic_tiered` must never run in this campaign |

Feature S3 prefix (isolated from other features):

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/`

There must be no S3 objects under `.../is_toxic_tiered/` for this campaign.

## Feature contract

Read-only reference: `data_platform/generate_features/llm_toxicity_tiered/generate_feature.py` and `FEATURE_REGISTRY["llm_toxicity_tiered"]`.

Output schema per labeled row:

| Column | Type | Accepted values |
|--------|------|-----------------|
| `source_record_id` | string | Must match pinned preprocessed `uri` / `source_record_id` |
| `label_timestamp` | string | UTC timestamp from `lib.timestamp_utils.get_current_timestamp` |
| `toxicity_tier` | string | Exactly one of `low`, `medium`, `high` |

Wide-table rename for Step 15: export column `llm_toxicity_tier` sourced from raw `toxicity_tier`. Do not write `toxicity_prob`. Do not join Perspective columns.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Epic scope; LLM toxicity must stay distinct from Perspective |
| `/workspace/data_platform/generate_features/run_bluesky_llm_campaign.py` | Campaign CLI from Steps 4–7 |
| `/workspace/data_platform/generate_features/llm_toxicity_tiered/generate_feature.py` | Prompt and output schema |
| `/workspace/data_platform/generate_features/is_toxic_tiered/generate_feature.py` | Perspective feature to avoid |
| `/workspace/data_platform/generate_features/registry.py` | `llm_toxicity_tiered` vs `is_toxic_tiered` |
| `/workspace/data_platform/generate_features/metadata.py` | Pinned model and prompt hash behavior on resume |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | OpenAI Batch resume semantics |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/metadata.json` | Expected `row_counts.output == 200000` |
| `/workspace/AGENTS.md` | `PYTHONPATH=.`, AWS credential export in Cloud Agent |

## Files allowed to change

Run artifacts only:

- `/workspace/docs/reports/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered_REPORT.md` (permanent; keep after merge)
- `/workspace/docs/reports/bluesky_2026_09_03_235130_llm_features_v1/smoke/llm_toxicity_tiered_*` (temporary smoke and resume evidence; commit for review, delete before merge)
- S3 objects under the feature prefix above

Do not edit the plan package during implementation.

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/data_platform/generate_features/**` except reading
- `/workspace/data_platform/utils/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/models/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- Any other repository file

Explicit prohibition: never invoke `--feature is_toxic_tiered`, never write Perspective outputs, and never create `.../campaigns/bluesky_2026_09_03_235130_llm_features_v1/is_toxic_tiered/`.

## Workflow

### Phase A — Ten-post smoke, cost estimate, interrupt/resume proof

1. Export AWS credentials per `AGENTS.md`.
2. Run smoke with exactly one feature flag: `llm_toxicity_tiered`.
3. Commit temporary smoke artifacts listed below so reviewers can inspect cost and resume evidence.
4. Post the smoke cost estimate to this feature’s GitHub issue.
5. Perform the deliberate interruption and resume check required by Step 6 on the same campaign prefix.
6. Wait for parent campaign approval on the aggregate cost estimate before Phase B.

### Phase B — Full 200,000-row generation

1. Run the same command with full-run flags only after parent approval.
2. Keep one blocking OpenAI Batch job active for this feature.
3. After each durable 2,000-row shard lands in S3, ensure Step 7 progress records update.
4. At every 10,000 durable labeled rows, update the rolling GitHub issue comment via the watcher subagent pattern from Step 7.
5. On failure, resume the failed run with the same campaign prefix and `--resume`; do not start a parallel provider job.

### Phase C — Validation, permanent report, PR cleanup

1. Run runtime validation commands below.
2. Confirm no Perspective artifacts exist for this campaign prefix.
3. Write the permanent run report including label counts for `low`, `medium`, and `high`.
4. Remove temporary smoke artifacts from the branch before merge.
5. Leave S3 final Parquet, manifest, progress history, and permanent report in place.

## Exact commands

From the repo root. Export AWS credentials first:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

Install deps if needed:

```bash
uv sync
```

### Smoke (ten posts, one feature only)

```bash
PYTHONPATH=. uv run python data_platform/generate_features/run_bluesky_llm_campaign.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature llm_toxicity_tiered \
  --batch-size 2000 \
  --phase smoke
```

Expected:

- Stdout reports exactly ten labeled rows with `toxicity_tier` values.
- Smoke cost JSON is written under `docs/reports/bluesky_2026_09_03_235130_llm_features_v1/smoke/llm_toxicity_tiered_cost.json`.
- Smoke outputs land under `.../llm_toxicity_tiered/smoke/` on S3.
- Deliberate interrupt/resume evidence is captured in `docs/reports/bluesky_2026_09_03_235130_llm_features_v1/smoke/llm_toxicity_tiered_resume_evidence.md`.

### Full run (after parent approval)

```bash
PYTHONPATH=. uv run python data_platform/generate_features/run_bluesky_llm_campaign.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature llm_toxicity_tiered \
  --batch-size 2000 \
  --phase full
```

Expected:

- One OpenAI Batch job chain completes with 100 durable shards of 2,000 rows each.
- Progress records advance in steps of 2,000 until `labeled == 200000`.
- Rolling issue comment updates occur at 10000, 20000, …, 200000 durable rows.

### Failed-run resume

```bash
PYTHONPATH=. uv run python data_platform/generate_features/run_bluesky_llm_campaign.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature llm_toxicity_tiered \
  --batch-size 2000 \
  --phase full \
  --resume
```

Expected:

- The CLI reloads the persisted OpenAI Batch job ID and existing shards.
- No duplicate provider job is created for rows already durably written.
- Model ID and prompt hash in campaign metadata remain unchanged.

### Runtime validation (required; not automated tests)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python - <<'PY'
import duckdb

final = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/final/llm_toxicity_tiered.parquet"
posts = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet"

con = duckdb.connect()
row = con.execute(f"""
WITH inp AS (
  SELECT CAST(source_record_id AS VARCHAR) AS source_record_id
  FROM read_parquet('{posts}')
),
feat AS (
  SELECT CAST(source_record_id AS VARCHAR) AS source_record_id,
         toxicity_tier
  FROM read_parquet('{final}')
)
SELECT
  (SELECT COUNT(*) FROM inp) AS input_rows,
  (SELECT COUNT(*) FROM feat) AS feature_rows,
  (SELECT COUNT(DISTINCT source_record_id) FROM feat) AS unique_ids,
  (SELECT COUNT(*) FROM feat WHERE toxicity_tier IS NULL) AS null_labels,
  (SELECT COUNT(*) FROM inp i LEFT JOIN feat f USING (source_record_id) WHERE f.source_record_id IS NULL) AS missing_labels,
  (SELECT COUNT(*) FROM feat f LEFT JOIN inp i USING (source_record_id) WHERE i.source_record_id IS NULL) AS extra_labels
""").fetchone()
print(row)
assert row == (200000, 200000, 200000, 0, 0, 0)
PY
```

Accepted-value check:

```bash
PYTHONPATH=. uv run python - <<'PY'
import duckdb
path = "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/final/llm_toxicity_tiered.parquet"
allowed = ("low", "medium", "high")
con = duckdb.connect()
bad = con.execute(f"""
SELECT COUNT(*) FROM read_parquet('{path}')
WHERE toxicity_tier NOT IN {allowed}
""").fetchone()[0]
print("invalid_toxicity_rows", bad)
assert bad == 0
cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()]
assert "toxicity_prob" not in cols
counts = con.execute(f"""
SELECT toxicity_tier, COUNT(*) AS n
FROM read_parquet('{path}')
GROUP BY 1 ORDER BY 1
""").fetchdf()
print(counts.to_string(index=False))
PY
```

Perspective absence check:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/is_toxic_tiered/ 2>&1 || true
```

Expected: `An error occurred (NoSuchKey)` or empty listing. Any objects under that prefix fail this step.

Manifest check:

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/campaigns/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/final/manifest.sha256.json -
```

Expected: JSON listing SHA-256 for final Parquet and every durable shard, with row counts summing to 200000.

## Required outputs

### S3 (permanent)

| Object | Purpose |
|--------|---------|
| `.../llm_toxicity_tiered/shards/shard_*.parquet` | Durable 2,000-row intermediate shards |
| `.../llm_toxicity_tiered/final/llm_toxicity_tiered.parquet` | Final deduped feature file with raw column `toxicity_tier` |
| `.../llm_toxicity_tiered/final/manifest.sha256.json` | SHA-256 manifest |
| `.../llm_toxicity_tiered/progress/` | Structured progress history |
| `.../llm_toxicity_tiered/metadata.json` | Campaign metadata including OpenAI job ID, model ID, prompt hash, labeled count |

### Repository

| Path | Lifetime |
|------|----------|
| `docs/reports/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered_REPORT.md` | Permanent |
| `docs/reports/bluesky_2026_09_03_235130_llm_features_v1/smoke/llm_toxicity_tiered_cost.json` | Temporary; remove before merge |
| `docs/reports/bluesky_2026_09_03_235130_llm_features_v1/smoke/llm_toxicity_tiered_resume_evidence.md` | Temporary; remove before merge |

Permanent report must record: S3 URIs, input preprocessed hash, manifest digest, model ID, prompt hash, smoke and actual token counts, estimated and actual cost, throughput, retry counts, validation command results, counts for `low`, `medium`, and `high`, and an explicit statement that `is_toxic_tiered` was not run.

## Acceptance and failure

| Check | Pass | Fail |
|-------|------|------|
| Dependencies | Steps 3–7 merged | Campaign CLI or S3 backend missing |
| Single feature command | Every run uses only `--feature llm_toxicity_tiered` | Multiple `--feature` values, full registry run, or `--feature is_toxic_tiered` |
| Batch size | `--batch-size 2000` on smoke and full runs | Any other batch size |
| Parent approval | Full run starts only after parent issue approval | Full run before approval |
| Smoke artifacts | Temporary smoke files committed for review, then removed before merge | Smoke artifacts left in repo or never committed for review |
| Completeness | Exactly 200000 unique `source_record_id` values, zero null labels, zero missing/extra IDs | Any other row count or join mismatch |
| Accepted values | `toxicity_tier` in `{low, medium, high}` only | Any other label string or `toxicity_prob` column |
| Perspective isolation | No `is_toxic_tiered` run and no campaign-prefix objects under `is_toxic_tiered/` | Perspective outputs present |
| Resume | Failed run continues with `--resume` on same prefix without duplicate OpenAI job | New provider job for already-labeled rows |
| Progress | Rolling issue comment updates every 10000 durable rows | Missing updates |
| Tests | Runtime checks only | New or modified automated tests in this PR |
| Product code | No Python product code edits | Any change under `data_platform/generate_features/**` or related libraries |

## Done when

1. Smoke, interrupt/resume proof, and cost estimate are posted and parent campaign approval is recorded.
2. Final S3 Parquet, manifest, and progress history exist for `llm_toxicity_tiered` with raw column `toxicity_tier`.
3. Runtime validation passes with exactly 200000 unique, non-null toxicity tiers in `{low, medium, high}`.
4. No Perspective campaign artifacts exist.
5. Permanent run report is committed; temporary smoke artifacts are removed before merge.
6. Rolling GitHub issue updates cover 10000-row milestones through 200000.
