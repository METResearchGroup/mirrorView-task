# Step 8: Generate `is_news_or_opinion` for 200,000 Bluesky posts

## Goal

Run the approved ten-post smoke flow and the full 200,000-post OpenAI Batch generation for the `is_news_or_opinion` feature only. Publish immutable S3 shards, the final Parquet file, hash manifest, progress history, validation results, and one permanent run report. Do not change product code in this pull request. Do not commit label Parquet or CSV files to Git.

This step is one future pull request and one GitHub feature issue. The issue stays open until the feature run is complete and validated.

## Dependencies on Steps 3–7

Do not start this step until Steps 3–7 have merged to `main`.

**Step 3 (S3 default backend).** Production feature generation reads preprocessed input and writes feature output through S3, not local `data_platform/data/` or Git LFS. Export AWS credentials before any S3-touching command:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

**Step 4 (OpenAI Batch hardening and resume).** The engine persists in-flight OpenAI Batch job identity before polling, keeps successful records from partly failed jobs, retries only transient failures, and resumes without creating duplicate provider jobs. A failed or interrupted run reuses the same feature run directory and the same `--checkpoint` value.

**Step 5 (Parquet shards and manifests).** Each durable batch writes one immutable 2,000-row Parquet shard under the feature S3 prefix, plus error records and a hash manifest. One blocking OpenAI Batch job stays active per feature. The run ends with one consolidated final Parquet file for `is_news_or_opinion`.

**Step 6 (ten-post smoke and campaign approval gate).** Use the deterministic ten-post sample shipped in Step 6 for every feature. Record average and maximum token usage, current model pricing, estimated full-run cost, S3 presence checks, and one deliberate interruption plus resume. Post the smoke cost estimate to this feature issue. Wait until the parent campaign issue records the sum of all seven feature estimates and receives one explicit approval before starting the 200,000-post run.

**Step 7 (progress watcher).** After each durable shard, the runner writes a structured progress record. A restartable watcher subagent reads those records and updates one rolling GitHub issue comment at every 10,000 completed records for this feature.

## Pinned identity contract

Use exactly these values for the full campaign. A different dataset, preprocessed run, campaign id, model, or prompt requires a new campaign and must not reuse this prefix.

| Field | Pinned value |
|-------|----------------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | `200000` (`metadata.json` `row_counts.output`) |
| Preprocessed input S3 prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/` |
| Campaign id / feature run family | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `is_news_or_opinion` |
| Feature S3 campaign prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/` |
| Model id | `gpt-5.4-nano` (`lib.constants.DEFAULT_LLM_MODEL`) |
| Engine | OpenAI Batch (`engine_type="openai"`) |
| Batch size | `2000` |
| Temperature | `0.0` |
| System prompt source | `data_platform/generate_features/is_news_or_opinion/generate_feature.py` → `SYSTEM_PROMPT` |
| LLM output schema | `LlmIsNewsOrOpinionModel` in the same file |
| Stored label schema | `IsNewsOrOpinionModel`: `source_record_id`, `label_timestamp`, `category` |
| Prompt identity in metadata | `metadata.json` `features.is_news_or_opinion.model_id` = `gpt-5.4-nano` and `prompt_hash` = SHA-256 hex of `SYSTEM_PROMPT` |

Record the exact `prompt_hash` from the smoke run metadata in the permanent run report. If `model_id` or `prompt_hash` drifts from the smoke run, stop and open a new campaign instead of resuming.

## Caller command

Run only this feature with batch size 2000. Do not pass any other `--features` value.

**New feature run (smoke phase uses the Step 6 ten-post path; full run uses this command):**

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --features is_news_or_opinion \
  --batch-size 2000
```

**Resume an interrupted run (same issue, same feature run directory name):**

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --features is_news_or_opinion \
  --batch-size 2000 \
  --checkpoint <feature_run_timestamp>
```

Replace `<feature_run_timestamp>` with the folder name under the campaign prefix (for example `2026_09_05-14:30:00`). Never start a second concurrent OpenAI Batch job for this feature while an unfinished run exists.

## Two-phase pull request flow

### Phase A — smoke, estimate, and review artifacts

1. Confirm Steps 3–7 are on `main`.
2. Run the Step 6 ten-post smoke for `is_news_or_opinion` only.
3. Perform the deliberate interruption and resume required by Step 6 on the same feature run.
4. Write temporary smoke artifacts under the plan reports folder (see Allowed files).
5. Commit and push those temporary smoke artifacts to the feature branch. Do not commit labels.
6. Post the estimated full-run cost (derived from smoke token usage and current `gpt-5.4-nano` Batch pricing) to this feature issue.
7. Stop. Do not start the 200,000-post run until the parent campaign issue shows one approval covering all seven feature estimates.

### Phase B — full run after parent approval

1. Confirm the parent campaign issue has explicit approval for the combined estimate.
2. Start or resume the full run with the caller command above.
3. Start the Step 7 progress watcher for this feature. It must update the rolling GitHub comment at every 10,000 durable rows.
4. When the run completes, validate S3 artifacts and row counts (see Acceptance checks).
5. Write the permanent run report at `reports/is_news_or_opinion_run_report.md` with actual cost, throughput, retries, error rate, and label counts.
6. Delete every temporary smoke artifact from the plan reports folder.
7. Commit and push only the permanent run report. Push the final S3 objects (already written during the run). Open or update the pull request for merge.

If the full run fails or is interrupted, keep the same GitHub issue and the same `--checkpoint` value. Resume; do not open a parallel run or a new campaign prefix.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Epic scope and done criteria |
| `/workspace/data_platform/generate_features/generate_bluesky_features.py` | Bluesky feature CLI entrypoint |
| `/workspace/data_platform/generate_features/platform_cli.py` | `--features`, `--batch-size`, `--checkpoint` |
| `/workspace/data_platform/generate_features/is_news_or_opinion/generate_feature.py` | `SYSTEM_PROMPT`, accepted label schema |
| `/workspace/data_platform/generate_features/registry.py` | Feature registry entry for `is_news_or_opinion` |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | OpenAI Batch engine and default model |
| `/workspace/data_platform/generate_features/metadata.py` | `model_id`, `prompt_hash`, resume identity checks |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/metadata.json` | Pinned input row count and run id |
| `/workspace/AGENTS.md` | `PYTHONPATH=.`, AWS credential export, no automated tests |

After Steps 3–7 merge, also read the Step 6 smoke helper, Step 7 progress watcher entrypoint, and any S3 layout docs those steps add.

## Files allowed to change

Only documentation artifacts for this feature run. No product code, no label data in Git.

**Temporary smoke artifacts (committed during Phase A, deleted before merge):**

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/is_news_or_opinion_smoke_cost.json`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/is_news_or_opinion_smoke_resume_evidence.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/is_news_or_opinion_smoke_s3_checks.txt`

**Permanent run report (committed during Phase B, kept after merge):**

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/is_news_or_opinion_run_report.md`

## Files forbidden to change

- Any file under `/workspace/data_platform/`, `/workspace/lib/`, `/workspace/ml_tooling/`, `/workspace/tests/`, `/workspace/pyproject.toml`, `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- Any other step file under `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/`
- Any path under the S3 prefixes for the other six features:
  - `.../bluesky_2026_09_03_235130_llm_features_v1/is_political/`
  - `.../bluesky_2026_09_03_235130_llm_features_v1/is_likely_spam/`
  - `.../bluesky_2026_09_03_235130_llm_features_v1/is_self_contained/`
  - `.../bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/`
  - `.../bluesky_2026_09_03_235130_llm_features_v1/political_stance/`
  - `.../bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/`
- Any committed Parquet, CSV, or JSON label files anywhere in the repository

Do not add or run automated tests.

## S3 artifacts

All objects live under:

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/`

Expected layout after Step 5 (exact subfolder names follow the Step 5 implementation):

| Artifact | Purpose |
|----------|---------|
| `shards/` | Immutable 2,000-row Parquet shards |
| `final/is_news_or_opinion.parquet` | Consolidated feature output |
| `manifest/` | SHA-256 hash manifest over shards and final file |
| `progress/` | Structured progress records (one per durable shard) |
| `errors/` | Error records for rows that failed after retries |
| `metadata.json` | Run metadata including `model_id`, `prompt_hash`, labeled counts, OpenAI job ids |

Intermediate shards may carry the intermediate-artifact lifecycle tag from Step 16. Final Parquet, manifest, progress records, and reports are retained.

## Basic commands and checks

**List campaign prefix:**

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/ --recursive
```

**Download final Parquet for validation:**

```bash
aws s3 cp \
  s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/final/is_news_or_opinion.parquet \
  /tmp/is_news_or_opinion.parquet
```

**Validate row count, uniqueness, schema, and accepted values:**

```bash
python - <<'PY'
import pandas as pd

ACCEPTED = {"news", "opinion", "neither"}
REQUIRED_COLS = ["source_record_id", "label_timestamp", "category"]

df = pd.read_parquet("/tmp/is_news_or_opinion.parquet")
assert list(df.columns) == REQUIRED_COLS, df.columns.tolist()
assert len(df) == 200_000, len(df)
assert df["source_record_id"].is_unique, "duplicate source_record_id"
assert df["category"].notna().all(), "missing category"
bad = set(df["category"].unique()) - ACCEPTED
assert not bad, bad
print("ok", df["category"].value_counts().to_dict())
PY
```

**Compare labeled ids to preprocessed input:**

```bash
python - <<'PY'
import pandas as pd

pre = pd.read_parquet(
    "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet"
)
feat = pd.read_parquet("/tmp/is_news_or_opinion.parquet")
input_ids = set(pre["source_record_id"])
output_ids = set(feat["source_record_id"])
assert input_ids == output_ids, (len(input_ids), len(output_ids), len(input_ids - output_ids))
print("ok ids match")
PY
```

When production reads preprocessed input from S3 (Step 3), download `posts.parquet` from the preprocessed S3 prefix instead of the local path.

**Verify manifest hashes** using the Step 5 manifest verifier against `manifest/` and `final/is_news_or_opinion.parquet`.

**Read progress for the watcher:**

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/progress/ --recursive /tmp/is_news_or_opinion_progress/
```

Confirm a new progress record exists after each 2,000-row shard and that the watcher comment updates at 10,000, 20,000, …, 200,000 durable rows.

## Exact accepted values

Each output row must validate as `IsNewsOrOpinionModel`:

| Column | Type | Accepted values |
|--------|------|-----------------|
| `source_record_id` | string | One per preprocessed post; exactly 200,000 unique values |
| `label_timestamp` | string | UTC timestamp from `lib.timestamp_utils.get_current_timestamp` |
| `category` | string | Exactly one of: `news`, `opinion`, `neither` |

No nulls. No extra columns. No duplicate `source_record_id`.

## Acceptance criteria

1. **Coverage:** Exactly 200,000 rows. Exactly 200,000 unique `source_record_id` values. Zero missing outputs relative to the pinned preprocessed run.
2. **Schema:** Columns match `IsNewsOrOpinionModel`. All `category` values are in the accepted set.
3. **Identity:** `metadata.json` records `model_id` = `gpt-5.4-nano` and the `prompt_hash` of the pinned `SYSTEM_PROMPT`.
4. **S3:** Final Parquet, manifest, progress history, and error records (if any) are present under the feature campaign prefix.
5. **Cost and operations:** The permanent run report records estimated cost (from smoke), actual cost (from OpenAI usage), throughput (posts per second and tokens per second), retry count, error rate, and label counts per category.
6. **Progress:** Watcher updated the GitHub comment at every 10,000 durable rows.
7. **Resume:** If the run was interrupted, resume used the same issue, same `--checkpoint`, and no duplicate OpenAI Batch job.
8. **Repository hygiene:** No label files committed. Temporary smoke artifacts removed before merge. Only `reports/is_news_or_opinion_run_report.md` remains from this step in Git.

## Permanent run report contents

`reports/is_news_or_opinion_run_report.md` must include:

- Pinned identity table (dataset, preprocessed run, campaign id, model, prompt file path, `prompt_hash`)
- S3 URIs for final Parquet, manifest, and progress folder
- Smoke estimated full-run cost (USD) and assumptions
- Actual cost (USD), input/output/total tokens
- Throughput (posts per second, tokens per second)
- Retry count and error rate (failed rows / 200,000)
- Label counts: `news`, `opinion`, `neither`
- Validation command outputs (pass/fail summary)
- Feature run timestamp and `--checkpoint` value used
- OpenAI Batch job id(s) from metadata
