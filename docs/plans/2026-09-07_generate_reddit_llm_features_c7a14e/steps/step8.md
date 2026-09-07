# Step 8: Generate is_structurally_complete for 400,000 Reddit comments

## Goal

Structural completeness is the third Bedrock boolean feature and shares the same throttle ceiling as spam and self-containedness, so the operator never runs more than three Bedrock agents at eight threads and records any OpenAI content-filter retries before Step 11 joins labels. The pull request carries documentation and run artifacts only and does not change product code or commit label Parquet to Git.

## Dependencies

Do not start the 400,000-comment production run until Steps 1, 2, and 3 have merged to `main` and the parent campaign issue has explicit owner sign-off. Phase A smoke may run after Step 3 merges. Post the smoke cost estimate to this feature issue even when production is still waiting on parent approval. See `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/campaign_contract.md`.

| Step | Requirement |
|------|-------------|
| Step 1 | S3 production backend and pinned Reddit dataset layout |
| Step 2 | Campaign contract, `generate_reddit_features.py` campaign flags, and Bedrock retry wiring where needed |
| Step 3 | `smoke_reddit_campaign.py` and `feature_progress_watcher.py` with `--platform reddit` |

## Main caller and pull request scope

**Main caller (campaign mode; same command resumes automatically):**

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --preprocessed-run 2026_09_03-23:39:28 \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --features is_structurally_complete \
  --batch-size 2000
```

**Smoke caller (Phase A only; available after Step 3):**

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/smoke_reddit_campaign.py \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --preprocessed-run 2026_09_03-23:39:28 \
  --feature is_structurally_complete \
  --output-dir docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete
```

**Pull request scope:** documentation and run artifacts only. No product code changes.

### Bedrock engine rules

- Primary engine: Bedrock Converse with model `us.amazon.nova-micro-v1:0`.
- Concurrency: 8 threads and 1 process for the full run.
- When Bedrock returns a content filter block, record the row in `errors.jsonl` with reason `bedrock_content_filter`.
- Before writing `final.parquet`, the same campaign command must retry those ids through OpenAI Batch in one pass.
- `manifest.json` must record `engine_type` `bedrock` and an `openai_content_filter_retry` block with retry counts.
- Rows labeled by OpenAI after a Bedrock content filter count toward `row_count`, not `failed_row_count`.

## Pinned identity contract

| Field | Pinned value |
|-------|----------------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | `400000` |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Feature name | `is_structurally_complete` |
| Run id | `reddit_2026_09_03_233928_llm_features_v1:is_structurally_complete` |
| Feature S3 prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/` |
| Engine | `bedrock` |
| Model id | `us.amazon.nova-micro-v1:0` |
| Batch size | `2000` |
| Batch object count | `200` (`part-00000` through `part-00199`) |
| Label field | `is_structurally_complete` |
| Pydantic model | `IsStructurallyCompleteModel` |
| Accepted label values | boolean `true` or `false` |
| Prompt source | `data_platform/generate_features/is_structurally_complete/generate_feature.py` → `SYSTEM_PROMPT` |

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/campaign_contract.md` | Layout, smoke flow, and validation rules |
| `/workspace/data_platform/generate_features/generate_reddit_features.py` | Campaign CLI |
| `/workspace/data_platform/generate_features/smoke_reddit_campaign.py` | Ten-comment smoke (Step 3) |
| `/workspace/data_platform/generate_features/feature_progress_watcher.py` | Progress watcher (Step 3) |
| `/workspace/data_platform/generate_features/is_structurally_complete/generate_feature.py` | Prompt and schema |
| `/workspace/AGENTS.md` | `PYTHONPATH=.`, AWS credentials, no automated tests |

## Files allowed to change

Documentation artifacts only.

**Temporary smoke artifacts (Phase A; deleted before merge):**

- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_cost_report.json`
- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_resume_evidence.json`
- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete/is_structurally_complete_s3_checks.txt`

**Permanent run report (Phase B; kept after merge):**

- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/is_structurally_complete_run_report.md`

## Files forbidden to change

- Any file under `/workspace/data_platform/`, `/workspace/lib/`, `/workspace/ml_tooling/`, `/workspace/tests/`, `/workspace/pyproject.toml`, `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/plan.md`
- Any other step file under `steps/`
- S3 prefixes for the other six features:
 - `.../reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/is_political/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/is_likely_spam/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/is_self_contained/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/political_stance/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/llm_toxicity_tiered/`
- Any committed Parquet, CSV, or JSON label files anywhere in the repository

Do not add or run automated tests.

## Locked contracts

See `campaign_contract.md`. S3 objects for this feature:

| Object | Path |
|--------|------|
| Smoke input | `.../is_structurally_complete/smoke/input.parquet` |
| Smoke output | `.../is_structurally_complete/smoke/output.parquet` |
| Smoke cost report | `.../is_structurally_complete/smoke/cost_report.json` |
| Smoke resume evidence | `.../is_structurally_complete/smoke/resume_evidence.json` |
| Batches | `.../is_structurally_complete/batches/part-NNNNN.parquet` |
| Final | `.../is_structurally_complete/final.parquet` |
| Manifest | `.../is_structurally_complete/manifest.json` |
| Progress | `.../is_structurally_complete/progress.jsonl` |
| Errors | `.../is_structurally_complete/errors.jsonl` (when needed) |
| Watcher | `.../is_structurally_complete/watcher.json` |

Row schema columns in `final.parquet`: `source_record_id`, `run_id`, `batch_id`, `request_id`, `attempt_count`, `label_timestamp`, `is_structurally_complete`.

After parent approval, `part-00000.parquet` must contain ten unchanged smoke labels plus 1,990 new labels (2,000 rows total). The next 199 production jobs each write `part-00001` through `part-00199` with 2,000 rows each. Total: exactly 200 immutable batch objects and 400,000 rows. Preserve original smoke `batch_id` and `request_id` in the ten rows in `part-00000`. The `manifest.json` batch entry for `part_index=0` may list both the smoke provider `batch_id` and the first production provider `batch_id`.

Pass and fail gate: `final.parquet` holds every labeled row. `manifest.json` `final_parquet.row_count` plus `final_parquet.failed_row_count` must equal 400,000. Every `source_record_id` in `final.parquet` must be unique. Permanent failures after all retries belong in `failed_row_count` and `errors.jsonl`, not in `final.parquet`.

## Two-phase pull request flow

### Phase A: smoke, estimate, and review artifacts

1. Confirm Steps 1, 2, and 3 are on `main`.
2. Run `smoke_reddit_campaign.py` once for `is_structurally_complete` only. The smoke caller performs one deliberate interruption and resume and writes untagged S3 evidence under `is_structurally_complete/smoke/` including `resume_evidence.json`. Do not repeat the interruption procedure in this step.
3. Commit temporary Git smoke artifacts under `reports/smoke/is_structurally_complete/` (include a local copy of `resume_evidence.json`).
4. Post estimated full-run cost to this feature's GitHub issue through authenticated GitHub integration.
5. Stop. Do not start the 400,000-comment run until the parent campaign issue has one aggregate estimate and explicit human approval.

### Phase B: full run after parent approval

1. Confirm the parent campaign issue has explicit owner sign-off.
2. Run the campaign CLI command above (same command resumes automatically).
3. Run the Step 3 watcher at every 10,000 durable rows and post the rolling comment through authenticated GitHub integration.
4. Validate S3 artifacts, `manifest.json` row counts, and `final.parquet`.
5. Write `reports/is_structurally_complete_run_report.md`.
6. Delete temporary smoke artifacts from Git. S3 smoke evidence remains.
7. Commit and push only the permanent run report.

## Ordered work

1. Phase A smoke and cost estimate.
2. Pause for parent aggregate and human approval.
3. Phase B full run with watcher.
4. Runtime validation.
5. Permanent report and Git cleanup.

## Exact commands and expected output

### List feature prefix

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/ --recursive
```

Expected: after Phase B, objects include `batches/part-00000.parquet` through `batches/part-00199.parquet`, `final.parquet`, `manifest.json`, and `progress.jsonl`.

### Download final parquet for validation

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/final.parquet /tmp/is_structurally_complete_final.parquet
```

### Validate row count, schema, manifest counts, and accepted values

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python - <<'PY'
import json
import subprocess

import pandas as pd

FEATURE = "is_structurally_complete"
RUN_ID = "reddit_2026_09_03_233928_llm_features_v1:is_structurally_complete"
MANIFEST_URI = "s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/manifest.json"
FINAL_PATH = "/tmp/is_structurally_complete_final.parquet"
ROW_COLS = [
    "source_record_id",
    "run_id",
    "batch_id",
    "request_id",
    "attempt_count",
    "label_timestamp",
    "is_structurally_complete"
]

manifest_json = subprocess.run(
    ["aws", "s3", "cp", MANIFEST_URI, "-"],
    check=True,
    capture_output=True,
    text=True,
).stdout
manifest = json.loads(manifest_json)
final_block = manifest["final_parquet"]
row_count = final_block["row_count"]
failed_row_count = final_block["failed_row_count"]
assert row_count + failed_row_count == 400000
assert final_block["sha256"]

df = pd.read_parquet(FINAL_PATH)
assert list(df.columns) == ROW_COLS, df.columns.tolist()
assert len(df) == row_count
assert df["source_record_id"].is_unique
assert df["run_id"].nunique() == 1
assert df["run_id"].iloc[0] == RUN_ID
assert df["is_structurally_complete"].notna().all()
assert df["is_structurally_complete"].dtype == bool or set(df["is_structurally_complete"].unique()) <= {True, False}
counts = {"row_count": row_count, "failed_row_count": failed_row_count}
print("ok", df["is_structurally_complete"].value_counts().to_dict(), counts)
PY
```

Expected: `ok` plus label value counts, `row_count`, and `failed_row_count`, with exit code 0.

### Verify manifest SHA-256

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/manifest.json -
```

Expected: JSON with `final_parquet.sha256` matching downloaded `final.parquet` bytes (SHA-256 only, not ETag).

### Verify manifest engine metadata

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/manifest.json -
```

Expected JSON includes `"engine_type": "bedrock"` and an `openai_content_filter_retry` object with a retry count.

### Run progress watcher once

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --once \
  --platform reddit \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --feature is_structurally_complete
```

Expected stdout includes `boundary_crossed=true`, a `boundary=` line at the latest 10,000-row multiple, `watcher_json_updated=true`, and `github_write_skipped=true`.

### Read progress for watcher milestones

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/progress.jsonl /tmp/is_structurally_complete_progress.jsonl
```

Confirm watcher comment updates at 10,000, 20,000, …, 400,000 durable rows.

## Acceptance criteria

1. `manifest.json` reports `row_count` plus `failed_row_count` equal to 400,000.
2. `final.parquet` holds `row_count` unique `source_record_id` values with the expected columns and `run_id`.
3. Accepted values for `is_structurally_complete` match the pinned contract.
4. `manifest.json`, `progress.jsonl`, and `final.parquet` are present under the feature prefix.
5. Permanent run report records smoke estimate, actual cost, throughput, retries, error rate, and label counts.
6. Watcher updated the GitHub comment at every 10,000 durable rows.
7. S3 smoke evidence under `is_structurally_complete/smoke/` includes `resume_evidence.json` from the single smoke run.
9. Temporary Git smoke files removed before merge. S3 smoke evidence remains.
10. Only `reports/is_structurally_complete_run_report.md` remains from this step in Git.

## Failure conditions

- Full 400k run starts before parent campaign issue approval.
- Smoke run twice for the same feature or different ten-comment ids than other features.
- Smoke writes any object under `batches/` (smoke never writes production batch objects).
- `part-00000.parquet` after full run does not contain ten unchanged smoke labels plus 1,990 new labels.
- Missing expected columns or wrong `run_id`.
- `row_count` plus `failed_row_count` not equal to 400,000.
- Any non-boolean `is_structurally_complete` value.
- Missing `openai_content_filter_retry` block in `manifest.json`.
- Bedrock run not using 8 threads and 1 process.
- Using `--checkpoint`, `--resume`, `run_reddit_llm_campaign.py`, or `APPROVED.txt`.
- Objects under `campaigns/`, `shards/`, `final/` subdirectory, or per-run timestamp folders.
- Label files committed to Git.
- Temporary smoke artifacts left in Git after merge.
- Any product code change in this PR.
- Any automated test added or run.

## PR artifact and commit rules

- Phase A: commit temporary smoke artifacts for review.
- Phase B: commit only permanent run report; delete temporary smoke files before merge.
- Do not edit `plan.md` or other step specs.

## Permanent run report contents

`reports/is_structurally_complete_run_report.md` must include:

- Pinned identity table (dataset, preprocessed run, campaign id, run id, engine, model, prompt path, prompt hash)
- S3 URIs for `final.parquet`, `manifest.json`, and `progress.jsonl`
- Smoke estimated full-run cost and assumptions
- Actual cost, tokens, throughput, retry count, error rate
- Label counts for `is_structurally_complete=true` and `is_structurally_complete=false`
- `row_count`, `failed_row_count`, and validation command pass or fail summary
- Bedrock thread and process settings (8 threads, 1 process)
- `openai_content_filter_retry` count from manifest
- Count of rows first blocked by Bedrock content filters and later labeled by OpenAI Batch

## GitHub issue body

Generate `is_structurally_complete` labels for 400,000 pinned Reddit comments through Bedrock Converse with model `us.amazon.nova-micro-v1:0`. Bedrock content-filter failures record `bedrock_content_filter` in `errors.jsonl` and retry through OpenAI Batch inside the same feature command. Run Phase A smoke once with `smoke_reddit_campaign.py`, post the full-run cost estimate to the issue, and wait for parent issue owner sign-off before Phase B. Phase B writes 200 immutable batch objects, `final.parquet`, and the permanent run report on S3. The pull request carries documentation and run artifacts only and does not change product code.

Plan step: `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/steps/step8.md`

Done when:

- Smoke cost estimate is posted to the issue.
- Parent issue has explicit owner sign-off before the 400,000-comment run starts.
- S3 holds 200 batch objects and validated `final.parquet` with 400000 unique `source_record_id` values and boolean `is_structurally_complete` labels.
- `manifest.json` records `engine_type=bedrock` and any `openai_content_filter_retry` metadata.
- `reports/is_structurally_complete_run_report.md` is committed and temporary Git smoke copies are removed before merge.

## Pull request description

Fixes #<child>

Part of #<parent>

## Problem

Structural completeness is the last Bedrock boolean feature, and running more than three Bedrock agents at eight threads risks throttling that slows all three features.

## Solution

Phase A commits smoke cost and resume evidence under `reports/smoke/is_structurally_complete/`. Phase B commits only `reports/is_structurally_complete_run_report.md` after the full run validates on S3.

## Purpose

Steps 1 through 3 landed Bedrock campaign mode, so the run-report pull request records throttle-safe settings and validation for structural completeness only.

## How to run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/smoke_reddit_campaign.py \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --preprocessed-run 2026_09_03-23:39:28 \
  --feature is_structurally_complete \
  --output-dir docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_structurally_complete
```

After parent approval, run the main caller from this step file and the validation block. Expect `row_count` plus `failed_row_count` to equal 400,000.
