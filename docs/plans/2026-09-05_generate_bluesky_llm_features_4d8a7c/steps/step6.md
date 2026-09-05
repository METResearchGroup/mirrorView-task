# Step 6: Add smoke tooling and cost aggregation

## Goal

Add reusable smoke tooling for the deterministic ten-post sample shared by all seven LLM features. Record current model pricing, average and maximum token usage per feature, estimated full-run cost, and S3 artifact checks. Include one deliberate interruption-and-resume proof inside the smoke caller. Provide an aggregation command that sums all seven per-feature estimates. This step delivers tooling only and does not run full 200k labeling or add a file-based approval gate.

## Dependencies

- **Step 5 merged:** canonical S3 layout, Q44 provenance columns, `active_openai_batch.json`, immutable batches, `manifest.json`, and logical-append `progress.jsonl`.
- See `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` for smoke flow and report paths.

Step 6 may proceed in parallel with Step 7 after Step 5 merges. Both Step 6 and Step 7 must complete before Steps 8 through 14.

## Main caller and implementation slice

**Main caller after this PR merges:**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/smoke_bluesky_campaign.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion
```

**One implementation slice for this PR:** implement `smoke_bluesky_campaign.py` with deterministic ten-post selection, per-feature cost report JSON, S3 verification, interrupt-and-resume proof, and `campaign_cost_report.py` with an `--aggregate` mode. Do not add `APPROVED.txt`, do not refuse production runs from repository code, and do not post to GitHub from repository code.

**Out of scope for this PR:** generating all 200,000 rows per feature (that is Steps 8 through 14), watcher GitHub comments (Step 7), Step 16 lifecycle infrastructure, wide seven-feature join (Step 15), and any code that posts to GitHub automatically.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Smoke flow, report paths, forbidden approval files |
| `/workspace/data_platform/generate_features/smoke_openai_engine.py` | Existing smoke metrics pattern |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | Campaign paths after Step 5 |
| `/workspace/data_platform/generate_features/s3_feature_batches.py` | Batch write and resume after Step 5 |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | Batch usage fields |
| `/workspace/data_platform/generate_features/registry.py` | Seven LLM features |
| `/workspace/data_platform/generate_features/generate_bluesky_features.py` | Production CLI entry |
| `/workspace/lib/constants.py` | `DEFAULT_LLM_MODEL` |
| `/workspace/lib/load_env_vars.py` | API key loading |

## Files allowed to change

- `/workspace/data_platform/generate_features/smoke_bluesky_campaign.py` (new)
- `/workspace/data_platform/generate_features/campaign_cost_report.py` (new; pricing math and aggregate report builder)
- `/workspace/data_platform/generate_features/deterministic_smoke_sample.py` (new; shared ten-post selector)
- `/workspace/data_platform/generate_features/s3_feature_campaign.py` (extend only if needed for smoke artifact paths)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step6.md` (this file only if correcting the spec during implementation)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md`, `step5.md`, `step7.md`
- `/workspace/tests/**`
- Feature prompt modules
- `/workspace/webapp/**`
- `/workspace/experiments/**`
- Any repository code that launches Cursor agents, opens GitHub issues, or posts GitHub comments automatically
- Any `APPROVED.txt` or file-based approval gate

## Locked contracts

See `campaign_contract.md`. This step owns tooling only.

### Shared deterministic ten-post sample

All seven features must label the same ten `source_record_id` values. Selection rule:

1. Load rows from preprocessed run `2026_09_03-23:51:30` for dataset `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73`.
2. Keep rows with non-empty `text`.
3. Sort by ascending `source_record_id`.
4. Take the first ten rows.

Write the selected ids to `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/deterministic_ten_post_ids.json` during the PR.

### Pricing and token estimates

Use current published Batch pricing for `gpt-5.4-nano` at smoke run time. Record in each feature cost report:

- pricing source URL
- input USD per million tokens
- output USD per million tokens
- average input tokens per request
- average output tokens per request
- maximum input tokens among the ten requests
- maximum output tokens among the ten requests
- estimated full-run cost for 200,000 posts using both average and max token assumptions

### Per-feature smoke evidence path

Each feature smoke writes under:

`docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/{feature}/`

Expected files per feature (committed during Steps 8 through 14 Phase A; temporary Git copies deleted before merge):

- `{feature}_cost_report.json`
- `{feature}_resume_evidence.json`
- `{feature}_s3_checks.txt`

S3 smoke evidence under the canonical feature prefix remains after Git cleanup in Steps 8 through 14 Phase A. Step 6 does not write canonical `{feature}/smoke/`.

### Parent aggregate command

After all seven per-feature cost reports exist:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --smoke-reports-dir docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke \
  --output docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/parent_cost_aggregate.json
```

Human approval is recorded on the parent GitHub issue only. No repository file gates full generation.

### S3 smoke evidence (canonical layout; Steps 8 through 14 only)

Step 6 tooling proof must not write canonical `{feature}/smoke/`. Step 8 owns the first official canonical smoke for each feature.

When Steps 8 through 14 run `smoke_bluesky_campaign.py` in Phase A, each feature writes exactly these untagged objects under the canonical `{feature}/smoke/` prefix:

| Object | Path |
|--------|------|
| Input sample | `.../{feature}/smoke/input.parquet` |
| Output labels | `.../{feature}/smoke/output.parquet` |
| Cost report | `.../{feature}/smoke/cost_report.json` |
| Resume evidence | `.../{feature}/smoke/resume_evidence.json` |

Smoke never writes `batches/part-*.parquet` or any other canonical production batch object.

### Deliberate interruption and resume (inside smoke caller only)

`smoke_bluesky_campaign.py` performs one deliberate interrupt after provider submit and before finalize, then resumes without creating a second provider batch for the same in-flight job. It writes `resume_evidence.json` to S3 and a Git copy under `reports/smoke/{feature}/`. Feature run steps must not repeat this procedure.

### Production batch schedule (Steps 8 through 14, after parent approval)

After parent approval, the first production provider job labels 1,990 new posts. Its successful rows are combined with the ten unchanged smoke output rows into immutable `batches/part-00000.parquet` (2,000 rows total). The next 99 provider jobs each label 2,000 posts and each write one canonical batch object (`part-00001` through `part-00099`). Total: 100 batch objects and 200,000 rows.

Preserve original smoke `batch_id` and `request_id` in the ten rows folded into `part-00000`.

### S3 checks during smoke

Each feature smoke verifies (against the smoke prefix in use):

- `smoke/input.parquet`, `smoke/output.parquet`, `smoke/cost_report.json`, and `smoke/resume_evidence.json` exist and are untagged
- `smoke/output.parquet` has exactly ten Q44 rows
- no objects exist under `batches/` yet
- interrupt-and-resume proof recorded in `smoke/resume_evidence.json`

Step 6 tooling proof runs these checks under the disposable prefix only.

## Ordered implementation work

1. Implement deterministic ten-post selector and commit `deterministic_ten_post_ids.json` under `reports/smoke/`.
2. Implement `smoke_bluesky_campaign.py` that labels those ten posts, writes untagged S3 smoke artifacts under `{feature}/smoke/` when no smoke-prefix override is set, and performs interrupt-and-resume inside the same invocation.
3. Record token usage from `engine.last_batch.usage`; compute average, max, and full-run cost estimates.
4. Implement `campaign_cost_report.py --aggregate` to sum seven feature reports.
5. Run live tooling proof for one feature under the disposable prefix only. Commit smoke tooling only. Do not run all seven features, full 200k, or write canonical `{feature}/smoke/` in this PR.

## Exact live smoke and basic check commands with expected output

### Offline deterministic sample check

```bash
cd /workspace

PYTHONPATH=. uv run python -c "
from data_platform.generate_features.deterministic_smoke_sample import load_deterministic_ten_post_ids
ids = load_deterministic_ten_post_ids(
    'bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73',
    '2026_09_03-23:51:30',
)
assert len(ids) == 10
assert ids == sorted(ids)
print('deterministic_ten_post_ids OK')
print('first_id=' + ids[0])
"
```

Expected stdout:

```text
deterministic_ten_post_ids OK
first_id=at://...
```

### Live single-feature tooling proof (requires `OPENAI_API_KEY`; available after this step's implementation)

Use the disposable smoke prefix only. Step 8 owns the first official canonical `{feature}/smoke/` write. Do not write under the pinned campaign feature `batches/` prefix.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

DISPOSABLE_PREFIX=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/

PYTHONPATH=. uv run python data_platform/generate_features/smoke_bluesky_campaign.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --output-dir docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_news_or_opinion
```

Expected stdout:

```text
smoke_prefix=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/
smoke_rows=10
avg_input_tokens=<number>
max_input_tokens=<number>
avg_output_tokens=<number>
max_output_tokens=<number>
estimated_full_run_usd_avg=<number>
estimated_full_run_usd_max=<number>
s3_smoke_output_ok=true
s3_smoke_resume_evidence_ok=true
no_batches_prefix_objects=true
canonical_smoke_prefix_touched=false
cost_report=docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_news_or_opinion/is_news_or_opinion_cost_report.json
```

### Disposable prefix cleanup (required before merge)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/ --recursive
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/ --recursive
```

Expected: `aws s3 rm` reports deleted objects (or no objects found). `aws s3 ls` prints no lines, confirming the disposable prefix is empty.

Verify canonical `is_news_or_opinion/smoke/` was not written during Step 6 tooling proof:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/smoke/ 2>&1 || true
```

Expected: `An error occurred (NoSuchKey)` or empty listing. No objects under canonical `is_news_or_opinion/smoke/` until Step 8 Phase A.

### Aggregate command shape (used by Steps 8 through 14 after all seven smokes)

```bash
cd /workspace

PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --smoke-reports-dir docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke \
  --output docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/parent_cost_aggregate.json
```

Expected stdout:

```text
features_included=7
total_estimated_full_run_usd_avg=<number>
total_estimated_full_run_usd_max=<number>
parent_cost_aggregate.json written
```

## Acceptance criteria

- `smoke_bluesky_campaign.py` and `campaign_cost_report.py --aggregate` exist and run.
- Deterministic ten-post selector returns the same ids for every feature.
- Smoke tooling writes cost, resume, and S3 check artifacts to the `reports/smoke/{feature}/` layout.
- Step 6 tooling proof writes untagged objects only under `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/`; no canonical `{feature}/smoke/` or `batches/` objects.
- Disposable S3 prefix is empty after `aws s3 rm ... --recursive` before merge.
- Canonical `is_news_or_opinion/smoke/` remains absent after Step 6 tooling proof.
- No `APPROVED.txt` or repository approval gate is added.
- No automated tests were added or run.
- No repository code posts GitHub comments or launches Cursor agents.

## Failure conditions

- Different ten-post ids across features.
- Missing max token fields in cost report schema.
- Aggregate command cannot read seven per-feature reports.
- Repository code refuses or permits full generation based on a file marker.
- Repository code posts to GitHub automatically.
- Smoke writes canonical `batches/part-*.parquet` during smoke.
- Step 6 tooling proof writes any object under canonical `{feature}/smoke/`.
- Disposable prefix `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/` is not empty before merge.
- Any edit under `/workspace/tests/**`.

## PR artifact and commit rules

- Commit smoke tooling modules and `deterministic_ten_post_ids.json` only.
- Do not commit all seven feature smoke outputs in this PR (those belong to Steps 8 through 14 Phase A).
- Before merge: run `aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step6_campaign_smoke/ --recursive`, verify the disposable prefix is empty, and confirm canonical `is_news_or_opinion/smoke/` is still absent.
- PR title: `Add smoke tooling and cost aggregation for Bluesky LLM campaign`
- PR body must state: tooling only, no approval file, no full runs, disposable smoke prefix used for proof, canonical smoke deferred to Step 8.
