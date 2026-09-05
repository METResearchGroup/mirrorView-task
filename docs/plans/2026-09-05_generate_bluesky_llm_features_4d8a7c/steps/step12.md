# Step 12: Generate is_structurally_complete for 200,000 Bluesky posts

## Goal

Run the approved ten-post smoke flow and the full 200,000-post OpenAI Batch generation for the `is_structurally_complete` feature only. Publish immutable S3 batches, `final.parquet`, `manifest.json`, `progress.jsonl`, validation results, and one permanent run report. Do not change product code in this pull request. Do not commit label Parquet or CSV files to Git.

This step is one future pull request and one GitHub feature issue. The issue stays open until the feature run is complete and validated.

## Dependencies

Do not start until Steps 3, 6, and 7 have merged to `main`. Steps 2, 4, and 5 are required transitively through Step 6 and Step 7. See `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md`.

| Step | Requirement |
|------|-------------|
| Step 3 | S3 is the production backend |
| Step 6 | `smoke_bluesky_campaign.py` and cost aggregation command (single invocation includes deliberate interruption and resume) |
| Step 7 | `progress.jsonl`, `watcher.json`, and watcher CLI |

## Main caller and implementation slice

**Main caller (campaign mode; same command resumes automatically):**

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --features is_structurally_complete \
  --batch-size 2000
```

**Smoke caller (Phase A only; available after Step 6):**

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_bluesky_campaign.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_structurally_complete \
  --output-dir docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_structurally_complete
```

**Implementation slice for this PR:** documentation and run artifacts only. No product code changes.

## Pinned identity contract

| Field | Pinned value |
|-------|----------------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | `200000` |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `is_structurally_complete` |
| Run id | `bluesky_2026_09_03_235130_llm_features_v1:is_structurally_complete` |
| Feature S3 prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/` |
| Model id | `gpt-5.4-nano` |
| Batch size | `2000` |
| Label field | `is_structurally_complete` |
| Pydantic model | `IsStructurallyCompleteModel` |
| Accepted label values | boolean `true` or `false` |
| Prompt source | `data_platform/generate_features/is_structurally_complete/generate_feature.py` → `SYSTEM_PROMPT` |

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Canonical layout and smoke flow |
| `/workspace/data_platform/generate_features/generate_bluesky_features.py` | Campaign CLI |
| `/workspace/data_platform/generate_features/smoke_bluesky_campaign.py` | Ten-post smoke (Step 6) |
| `/workspace/data_platform/generate_features/feature_progress_watcher.py` | Progress watcher (Step 7) |
| `/workspace/data_platform/generate_features/is_structurally_complete/generate_feature.py` | Prompt and schema |
| `/workspace/AGENTS.md` | `PYTHONPATH=.`, AWS credentials, no automated tests |

## Files allowed to change

Documentation artifacts only.

**Temporary smoke artifacts (Phase A; deleted before merge):**

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_structurally_complete/is_structurally_complete_cost_report.json`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_structurally_complete/is_structurally_complete_resume_evidence.json`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_structurally_complete/is_structurally_complete_s3_checks.txt`

**Permanent run report (Phase B; kept after merge):**

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/is_structurally_complete_run_report.md`

## Files forbidden to change

- Any file under `/workspace/data_platform/`, `/workspace/lib/`, `/workspace/ml_tooling/`, `/workspace/tests/`, `/workspace/pyproject.toml`, `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- Any other step file under `steps/`
- Any path under the S3 prefixes for the other six features:
 - `.../bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/`
 - `.../bluesky_2026_09_03_235130_llm_features_v1/is_political/`
 - `.../bluesky_2026_09_03_235130_llm_features_v1/is_likely_spam/`
 - `.../bluesky_2026_09_03_235130_llm_features_v1/is_self_contained/`
 - `.../bluesky_2026_09_03_235130_llm_features_v1/political_stance/`
 - `.../bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/`
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

Q44 columns in `final.parquet`: `source_record_id`, `run_id`, `batch_id`, `request_id`, `attempt_count`, `label_timestamp`, `is_structurally_complete`.

After parent approval, `part-00000.parquet` must contain ten unchanged smoke labels plus 1,990 new labels (2,000 rows total). The next 99 provider jobs each write `part-00001` through `part-00099` with 2,000 rows each. Total: exactly 100 canonical batch objects and 200,000 rows. Preserve original smoke `batch_id` and `request_id` in the ten rows in `part-00000`. `manifest.json` batch entry for `part_index=0` may list both the smoke provider `batch_id` and the first production provider `batch_id`.

## Two-phase pull request flow

### Phase A: smoke, estimate, and review artifacts

1. Confirm Steps 3, 6, and 7 are on `main`.
2. Run `smoke_bluesky_campaign.py` once for `is_structurally_complete` only. The smoke caller performs one deliberate interruption and resume and writes untagged S3 evidence under `is_structurally_complete/smoke/` including `resume_evidence.json`. Do not repeat the interruption procedure in this step.
3. Commit temporary Git smoke artifacts under `reports/smoke/is_structurally_complete/` (include a local copy of `resume_evidence.json`).
4. Post estimated full-run cost to this feature's GitHub issue through authenticated GitHub integration.
5. Stop. Do not start the 200,000-post run until the parent campaign issue has one aggregate estimate and explicit human approval.

### Phase B: full run after parent approval

1. Confirm parent campaign issue has explicit approval.
2. Run the campaign CLI command above (same command resumes automatically).
3. Run the Step 7 watcher at every 10,000 durable rows; post rolling comment through authenticated GitHub integration.
4. Validate S3 artifacts and row counts.
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

aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/ --recursive
```

### Download final parquet for validation

```bash
aws s3 cp \
  s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/final.parquet \
  /tmp/is_structurally_complete_final.parquet
```

### Validate row count, Q44 schema, and accepted values

```bash
PYTHONPATH=. uv run python - <<'PY'
import pandas as pd

Q44_COLS = [
    "source_record_id", "run_id", "batch_id", "request_id",
    "attempt_count", "label_timestamp", "is_structurally_complete",
]

df = pd.read_parquet("/tmp/is_structurally_complete_final.parquet")
assert list(df.columns) == Q44_COLS, df.columns.tolist()
assert len(df) == 200_000, len(df)
assert df["source_record_id"].is_unique
assert df["run_id"].nunique() == 1
assert df["run_id"].iloc[0] == "bluesky_2026_09_03_235130_llm_features_v1:is_structurally_complete"
assert df["is_structurally_complete"].notna().all()
assert df["is_structurally_complete"].dtype == bool or set(df["is_structurally_complete"].unique()) <= {True, False}
print("ok", df["is_structurally_complete"].value_counts().to_dict())
PY
```

Expected: `ok` plus value counts and exit code 0.

### Verify manifest SHA-256

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/manifest.json -
```

Expected: JSON with `final_parquet.sha256` matching downloaded bytes (SHA-256 only, not ETag).

### Read progress for watcher

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/progress.jsonl /tmp/is_structurally_complete_progress.jsonl
```

Confirm watcher comment updates at 10,000, 20,000, …, 200,000 durable rows.

## Acceptance criteria

1. Exactly 200,000 unique `source_record_id` values with zero missing outputs.
2. Q44 columns present with correct `run_id` and accepted `is_structurally_complete` values.
3. `manifest.json`, `progress.jsonl`, and `final.parquet` present under the feature prefix.
4. Permanent run report records smoke estimate, actual cost, throughput, retries, error rate, and label counts.
5. Watcher updated the GitHub comment at every 10,000 durable rows.
6. Resume reused the same `run_id` with no duplicate OpenAI Batch job.
7. S3 smoke evidence under `is_structurally_complete/smoke/` includes `resume_evidence.json` from the single smoke invocation.
8. Temporary Git smoke files removed before merge. S3 smoke evidence remains.
9. Only `reports/is_structurally_complete_run_report.md` remains from this step in Git.

## Failure conditions

- Full 200k run starts before parent campaign issue approval.
- Smoke run twice for the same feature or different ten-post ids than other features.
- Smoke writes any object under `batches/` (smoke never writes canonical batch objects).
- `part-00000.parquet` after full run does not contain ten unchanged smoke labels plus 1,990 new labels.
- Missing Q44 columns or wrong `run_id`.
- Any non-boolean `is_structurally_complete` value.
- Using `--checkpoint`, `--resume`, `run_bluesky_llm_campaign.py`, or `APPROVED.txt`.
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

- Pinned identity table (dataset, preprocessed run, campaign id, run id, model, prompt path, prompt hash)
- S3 URIs for `final.parquet`, `manifest.json`, and `progress.jsonl`
- Smoke estimated full-run cost and assumptions
- Actual cost, tokens, throughput, retry count, error rate
- Label counts for `is_structurally_complete=true` and `is_structurally_complete=false`
- Validation command pass/fail summary
- OpenAI Batch job id(s) from manifest or progress lines
