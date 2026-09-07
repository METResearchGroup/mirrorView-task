# Step 4: Generate is_news_or_opinion for 400,000 Reddit comments

## Goal

Run the approved ten-comment smoke flow and the full 400,000-comment production run for the `is_news_or_opinion` feature only. Publish immutable S3 batches, `final.parquet`, `manifest.json`, `progress.jsonl`, validation results, and one permanent run report. Do not change product code in this pull request. Do not commit label Parquet or CSV files to Git.

The work maps to one future pull request and one GitHub feature issue. The issue stays open until the feature run is complete and validated.

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
  --features is_news_or_opinion \
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
  --feature is_news_or_opinion \
  --output-dir docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_news_or_opinion
```

**Pull request scope:** documentation and run artifacts only. No product code changes.

## Pinned identity contract

| Field | Pinned value |
|-------|----------------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | `400000` |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Feature name | `is_news_or_opinion` |
| Run id | `reddit_2026_09_03_233928_llm_features_v1:is_news_or_opinion` |
| Feature S3 prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/` |
| Engine | `openai` |
| Model id | `gpt-5.4-nano` |
| Batch size | `2000` |
| Batch object count | `200` (`part-00000` through `part-00199`) |
| Label field | `category` |
| Pydantic model | `IsNewsOrOpinionModel` |
| Accepted label values | `news`, `opinion`, `neither` |
| Prompt source | `data_platform/generate_features/is_news_or_opinion/generate_feature.py` → `SYSTEM_PROMPT` |

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/campaign_contract.md` | Layout, smoke flow, and validation rules |
| `/workspace/data_platform/generate_features/generate_reddit_features.py` | Campaign CLI |
| `/workspace/data_platform/generate_features/smoke_reddit_campaign.py` | Ten-comment smoke (Step 3) |
| `/workspace/data_platform/generate_features/feature_progress_watcher.py` | Progress watcher (Step 3) |
| `/workspace/data_platform/generate_features/is_news_or_opinion/generate_feature.py` | Prompt and schema |
| `/workspace/AGENTS.md` | `PYTHONPATH=.`, AWS credentials, no automated tests |

## Files allowed to change

Documentation artifacts only.

**Temporary smoke artifacts (Phase A; deleted before merge):**

- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_news_or_opinion/is_news_or_opinion_cost_report.json`
- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_news_or_opinion/is_news_or_opinion_resume_evidence.json`
- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_news_or_opinion/is_news_or_opinion_s3_checks.txt`

**Permanent run report (Phase B; kept after merge):**

- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/is_news_or_opinion_run_report.md`

## Files forbidden to change

- Any file under `/workspace/data_platform/`, `/workspace/lib/`, `/workspace/ml_tooling/`, `/workspace/tests/`, `/workspace/pyproject.toml`, `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/plan.md`
- Any other step file under `steps/`
- S3 prefixes for the other six features:
 - `.../reddit_2026_09_03_233928_llm_features_v1/is_political/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/is_likely_spam/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/is_self_contained/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/political_stance/`
 - `.../reddit_2026_09_03_233928_llm_features_v1/llm_toxicity_tiered/`
- Any committed Parquet, CSV, or JSON label files anywhere in the repository

Do not add or run automated tests.

## Locked contracts

See `campaign_contract.md`. S3 objects for this feature:

| Object | Path |
|--------|------|
| Smoke input | `.../is_news_or_opinion/smoke/input.parquet` |
| Smoke output | `.../is_news_or_opinion/smoke/output.parquet` |
| Smoke cost report | `.../is_news_or_opinion/smoke/cost_report.json` |
| Smoke resume evidence | `.../is_news_or_opinion/smoke/resume_evidence.json` |
| Batches | `.../is_news_or_opinion/batches/part-NNNNN.parquet` |
| Final | `.../is_news_or_opinion/final.parquet` |
| Manifest | `.../is_news_or_opinion/manifest.json` |
| Progress | `.../is_news_or_opinion/progress.jsonl` |
| Errors | `.../is_news_or_opinion/errors.jsonl` (when needed) |
| Watcher | `.../is_news_or_opinion/watcher.json` |

Row schema columns in `final.parquet`: `source_record_id`, `run_id`, `batch_id`, `request_id`, `attempt_count`, `label_timestamp`, `category`.

After parent approval, `part-00000.parquet` must contain ten unchanged smoke labels plus 1,990 new labels (2,000 rows total). The next 199 production jobs each write `part-00001` through `part-00199` with 2,000 rows each. Total: exactly 200 immutable batch objects and 400,000 rows. Preserve original smoke `batch_id` and `request_id` in the ten rows in `part-00000`. The `manifest.json` batch entry for `part_index=0` may list both the smoke provider `batch_id` and the first production provider `batch_id`.

Pass and fail gate: `final.parquet` holds every labeled row. `manifest.json` `final_parquet.row_count` plus `final_parquet.failed_row_count` must equal 400,000. Every `source_record_id` in `final.parquet` must be unique. Permanent failures after all retries belong in `failed_row_count` and `errors.jsonl`, not in `final.parquet`.

## Two-phase pull request flow

### Phase A: smoke, estimate, and review artifacts

1. Confirm Steps 1, 2, and 3 are on `main`.
2. Run `smoke_reddit_campaign.py` once for `is_news_or_opinion` only. The smoke caller performs one deliberate interruption and resume and writes untagged S3 evidence under `is_news_or_opinion/smoke/` including `resume_evidence.json`. Do not repeat the interruption procedure in this step.
3. Commit temporary Git smoke artifacts under `reports/smoke/is_news_or_opinion/` (include a local copy of `resume_evidence.json`).
4. Post estimated full-run cost to this feature's GitHub issue through authenticated GitHub integration.
5. Stop. Do not start the 400,000-comment run until the parent campaign issue has one aggregate estimate and explicit human approval.

### Phase B: full run after parent approval

1. Confirm the parent campaign issue has explicit owner sign-off.
2. Run the campaign CLI command above (same command resumes automatically).
3. Run the Step 3 watcher at every 10,000 durable rows and post the rolling comment through authenticated GitHub integration.
4. Validate S3 artifacts, `manifest.json` row counts, and `final.parquet`.
5. Write `reports/is_news_or_opinion_run_report.md`.
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

aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/ --recursive
```

Expected: after Phase B, objects include `batches/part-00000.parquet` through `batches/part-00199.parquet`, `final.parquet`, `manifest.json`, and `progress.jsonl`.

### Download final parquet for validation

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/final.parquet /tmp/is_news_or_opinion_final.parquet
```

### Validate row count, schema, manifest counts, and accepted values

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python - <<'PY'
import json
import subprocess

import pandas as pd

FEATURE = "is_news_or_opinion"
RUN_ID = "reddit_2026_09_03_233928_llm_features_v1:is_news_or_opinion"
MANIFEST_URI = "s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/manifest.json"
FINAL_PATH = "/tmp/is_news_or_opinion_final.parquet"
ROW_COLS = [
    "source_record_id",
    "run_id",
    "batch_id",
    "request_id",
    "attempt_count",
    "label_timestamp",
    "category"
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
ACCEPTED = {"news", "opinion", "neither"}
bad = set(df["category"].unique()) - ACCEPTED
assert not bad, bad
assert df["category"].notna().all()
counts = {"row_count": row_count, "failed_row_count": failed_row_count}
print("ok", df["category"].value_counts().to_dict(), counts)
PY
```

Expected: `ok` plus label value counts, `row_count`, and `failed_row_count`, with exit code 0.

### Verify manifest SHA-256

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/manifest.json -
```

Expected: JSON with `final_parquet.sha256` matching downloaded `final.parquet` bytes (SHA-256 only, not ETag).

### Run progress watcher once

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --once \
  --platform reddit \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --feature is_news_or_opinion
```

Expected stdout includes `boundary_crossed=true`, a `boundary=` line at the latest 10,000-row multiple, `watcher_json_updated=true`, and `github_write_skipped=true`.

### Read progress for watcher milestones

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/progress.jsonl /tmp/is_news_or_opinion_progress.jsonl
```

Confirm watcher comment updates at 10,000, 20,000, …, 400,000 durable rows.

## Acceptance criteria

1. `manifest.json` reports `row_count` plus `failed_row_count` equal to 400,000.
2. `final.parquet` holds `row_count` unique `source_record_id` values with the expected columns and `run_id`.
3. Accepted values for `category` match the pinned contract.
4. `manifest.json`, `progress.jsonl`, and `final.parquet` are present under the feature prefix.
5. Permanent run report records smoke estimate, actual cost, throughput, retries, error rate, and label counts.
6. Watcher updated the GitHub comment at every 10,000 durable rows.
7. Resume reused the same `run_id` with no duplicate OpenAI Batch job.
8. S3 smoke evidence under `is_news_or_opinion/smoke/` includes `resume_evidence.json` from the single smoke run.
9. Temporary Git smoke files removed before merge. S3 smoke evidence remains.
10. Only `reports/is_news_or_opinion_run_report.md` remains from this step in Git.

## Failure conditions

- Full 400k run starts before parent campaign issue approval.
- Smoke run twice for the same feature or different ten-comment ids than other features.
- Smoke writes any object under `batches/` (smoke never writes production batch objects).
- `part-00000.parquet` after full run does not contain ten unchanged smoke labels plus 1,990 new labels.
- Missing expected columns or wrong `run_id`.
- `row_count` plus `failed_row_count` not equal to 400,000.
- Any `category` value outside `news`, `opinion`, `neither`.
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

`reports/is_news_or_opinion_run_report.md` must include:

- Pinned identity table (dataset, preprocessed run, campaign id, run id, engine, model, prompt path, prompt hash)
- S3 URIs for `final.parquet`, `manifest.json`, and `progress.jsonl`
- Smoke estimated full-run cost and assumptions
- Actual cost, tokens, throughput, retry count, error rate
- Label counts for `news`, `opinion`, and `neither`
- `row_count`, `failed_row_count`, and validation command pass or fail summary
- OpenAI Batch job id(s) from manifest or progress lines

## GitHub issue body

Generate `is_news_or_opinion` labels for 400,000 pinned Reddit comments through OpenAI Batch with model `gpt-5.4-nano`. Run Phase A smoke once with `smoke_reddit_campaign.py`, post the full-run cost estimate to the issue, and wait for parent issue owner sign-off before Phase B. Phase B writes 200 immutable batch objects, `final.parquet`, `manifest.json`, progress records, and the permanent run report on S3. The pull request carries documentation and run artifacts only and does not change product code.

Plan step: `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/steps/step4.md`

Done when:

- Smoke cost estimate is posted to the issue.
- Parent issue has explicit owner sign-off before the 400,000-comment run starts.
- S3 holds 200 batch objects and validated `final.parquet` with 400000 unique `source_record_id` values and accepted `category` labels.
- `reports/is_news_or_opinion_run_report.md` is committed and temporary Git smoke copies are removed before merge.

## Pull request description

Fixes #<child>

Part of #<parent>

## Problem

The Reddit LLM campaign needs `is_news_or_opinion` labels for all 400,000 pinned comments before the wide join in Step 11 can run. Operators also need a reviewed paper trail without label Parquet in Git.

## Solution

Phase A commits smoke cost and resume evidence under `reports/smoke/is_news_or_opinion/`. Phase B commits only `reports/is_news_or_opinion_run_report.md` after the full run validates on S3.

## Purpose

Product code for campaign mode landed in Steps 1 through 3. The run-report pull request records smoke estimates, actual cost, throughput, and validation results for one feature end to end.

## How to run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/smoke_reddit_campaign.py \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --preprocessed-run 2026_09_03-23:39:28 \
  --feature is_news_or_opinion \
  --output-dir docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_news_or_opinion
```

After parent approval, run the main caller from this step file and the validation block. Expect `row_count` plus `failed_row_count` to equal 400,000.
