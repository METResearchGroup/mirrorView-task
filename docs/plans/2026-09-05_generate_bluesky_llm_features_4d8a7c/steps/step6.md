# Step 6: Add ten-post smoke cost reports and a campaign approval gate

## Goal

Add a deterministic ten-post smoke path shared by all seven LLM features. Record current model pricing, average and maximum token usage per feature, estimated full-run cost, S3 artifact checks, and one deliberate interruption-and-resume proof. Aggregate all seven estimates on the parent campaign issue and block full generation until one explicit human approval is recorded. After approval, the first production shard for each feature must combine the ten smoke outputs with 1,990 new outputs.

## Real dependencies

- Step 4 merged: OpenAI Batch resume and partial success behavior.
- Step 5 merged: S3 shard layout, Q44 provenance columns, immutable shards, manifest and progress files.
- Steps 1 through 3 merged: S3 production backend and pinned dataset availability.
- Parent plan constants and seven-feature registry.

## Main caller and one implementation slice

**Main caller after this PR merges:**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/bluesky_llm_campaign_smoke.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion \
  --mode smoke-and-cost
```

**One implementation slice for this PR:** implement deterministic ten-post selection, per-feature cost report JSON, S3 verification, interrupt-and-resume proof, parent aggregate report generation, and an approval gate file that full generation refuses to bypass.

**Out of scope for this PR:** generating all 200,000 rows per feature, watcher GitHub comments every 10,000 rows, Step 16 lifecycle infrastructure, wide seven-feature join, and any code that posts to GitHub automatically.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Parent plan Step 6 scope |
| `/workspace/data_platform/generate_features/smoke_openai_engine.py` | Existing smoke metrics pattern |
| `/workspace/data_platform/generate_features/OPENAI_BATCH_SMOKE_RESULTS.md` | Published pricing and token baselines |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | Campaign paths after Step 5 |
| `/workspace/data_platform/generate_features/s3_feature_shards.py` | Shard write and resume after Step 5 |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | Batch usage fields |
| `/workspace/data_platform/generate_features/registry.py` | Seven LLM features |
| `/workspace/data_platform/generate_features/platform_cli.py` | Production CLI entry |
| `/workspace/data_platform/generate_features/generate_bluesky_features.py` | Bluesky wrapper |
| `/workspace/lib/constants.py` | `DEFAULT_LLM_MODEL` |
| `/workspace/lib/load_env_vars.py` | API key loading |

## Files allowed to change

- `/workspace/data_platform/generate_features/bluesky_llm_campaign_smoke.py` (new; smoke, cost, S3 checks, interrupt/resume)
- `/workspace/data_platform/generate_features/campaign_cost_report.py` (new; pricing math and aggregate report builder)
- `/workspace/data_platform/generate_features/campaign_approval_gate.py` (new; approval token file contract)
- `/workspace/data_platform/generate_features/s3_feature_campaign.py` (extend only if needed for smoke artifact paths)
- `/workspace/data_platform/generate_features/platform_cli.py` (refuse full campaign run without approval file)
- `/workspace/data_platform/generate_features/deterministic_smoke_sample.py` (new; shared ten-post selector)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_smoke/` (new; committed smoke outputs and cost JSON during PR review)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step6.md` (this file only if correcting the spec during implementation)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step5.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step7.md`
- `/workspace/tests/**`
- Feature prompt modules under `/workspace/data_platform/generate_features/is_*`, `political_stance`, and `llm_toxicity_tiered`
- `/workspace/webapp/**`
- `/workspace/experiments/**`
- Any repository code that launches Cursor agents, opens GitHub issues, or posts GitHub comments automatically

## Locked contracts

### Shared deterministic ten-post sample

All seven features must label the same ten `source_record_id` values from the pinned preprocessed run. Selection rule:

1. Load rows from preprocessed run `2026_09_03-23:51:30` for dataset `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73`.
2. Keep rows with non-empty `text`.
3. Sort by ascending `source_record_id`.
4. Take the first ten rows.

Write the selected ids to `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_smoke/deterministic_ten_post_ids.json` during the PR. Every feature smoke run must read that file rather than re-derive ad hoc ids.

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

### Parent aggregate and one explicit approval

Each feature smoke writes `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_smoke/{feature}_cost_report.json`.

A parent aggregate file `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_smoke/parent_cost_aggregate.json` sums all seven features and must exist before full generation can start.

Full generation requires an approval token file:

```text
docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_smoke/APPROVED.txt
```

Content must include the exact string `approved_by=<human>` and `approved_at=<UTC ISO timestamp>`. The production CLI refuses to run without this file. No repository code may create or mutate `APPROVED.txt`; only a human operator adds it after reviewing the parent aggregate on the parent campaign issue.

### Deliberate interruption and resume

Each feature smoke must perform one deliberate interrupt after provider submit and before shard finalize, then resume without creating a second provider batch for the same in-flight job. Record evidence in `{feature}_resume_evidence.json`.

### First production shard after approval

After approval, the first durable production shard for each feature must contain:

- the ten smoke rows, unchanged ids and labels
- 1,990 new rows from the next ids in deterministic order
- total row count 2000
- one immutable shard object and matching manifest and progress entries

Do not relabel the ten smoke posts during the 1,990-row completion step.

### S3 checks during smoke

Each feature smoke verifies:

- shard object exists at the campaign prefix
- manifest SHA-256 matches shard bytes
- progress line appended
- batch shard tag `intermediate-artifact=true`

## Ordered implementation work

1. Implement deterministic ten-post selector and commit `deterministic_ten_post_ids.json`.
2. Implement per-feature smoke runner that labels those ten posts through the hardened OpenAI Batch path and writes S3 smoke shard 0.
3. Record token usage from `engine.last_batch.usage`; compute average, max, and full-run cost estimates in `{feature}_cost_report.json`.
4. Add interrupt-and-resume proof and write `{feature}_resume_evidence.json`.
5. Build `parent_cost_aggregate.json` from seven feature reports; fail if any feature is missing.
6. Add approval gate check to production CLI; ensure full run stops without `APPROVED.txt`.
7. Implement post-approval first-shard combiner that merges ten smoke rows plus 1,990 new rows without duplicate ids.
8. Run live smoke commands for all seven features. Commit smoke artifacts for review. Delete temporary-only helpers before merge; keep deterministic ids and cost reports only if the parent plan expects them to remain documented artifacts.

## Exact live smoke/basic check commands with expected output

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

Expected stdout shape:

```text
deterministic_ten_post_ids OK
first_id=at://...
```

### Live single-feature smoke and cost report

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/bluesky_llm_campaign_smoke.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion \
  --mode smoke-and-cost
```

Expected stdout:

```text
smoke_rows=10
avg_input_tokens=<number>
max_input_tokens=<number>
avg_output_tokens=<number>
max_output_tokens=<number>
estimated_full_run_usd_avg=<number>
estimated_full_run_usd_max=<number>
s3_manifest_sha256_ok=true
resume_without_resubmit=true
cost_report=docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_smoke/is_news_or_opinion_cost_report.json
```

### Build parent aggregate for all seven features

Run the same command once per feature name:

`is_news_or_opinion`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, `llm_toxicity_tiered`

Then:

```bash
cd /workspace

PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --output docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_smoke/parent_cost_aggregate.json
```

Expected stdout:

```text
features_included=7
total_estimated_full_run_usd_avg=<number>
total_estimated_full_run_usd_max=<number>
parent_cost_aggregate.json written
```

### Approval gate refusal check (before human approval)

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --features is_news_or_opinion \
  --batch-size 2000 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1
```

Expected stderr or stdout before approval file exists:

```text
Campaign approval missing: docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_smoke/APPROVED.txt
```

Exit code must be non-zero.

### First production shard after manual approval

After a human adds `APPROVED.txt`, run:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/bluesky_llm_campaign_smoke.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion \
  --mode first-production-shard
```

Expected stdout:

```text
production_shard_rows=2000
smoke_rows_reused=10
new_rows=1990
duplicate_source_record_id_count=0
```

## Acceptance criteria

- All seven features smoke the same ten deterministic posts.
- Each feature cost report records current pricing, average and max token usage, and estimated full-run cost.
- Parent aggregate includes all seven features and totals both average and max cost estimates.
- Production CLI refuses to run until `APPROVED.txt` exists with explicit human approval fields.
- Interrupt-and-resume smoke completes without duplicate provider batch creation.
- First production shard after approval contains 10 reused smoke rows and 1,990 new rows with no duplicate ids.
- S3 manifest, progress, and intermediate tag checks pass during smoke.
- No automated tests were added or run.
- No repository code posts GitHub comments or launches Cursor agents.

## Failure conditions

- Different ten-post ids across features.
- Missing max token fields in any cost report.
- Parent aggregate built from fewer than seven features.
- Production run starts without explicit human `APPROVED.txt`.
- First production shard relabels smoke posts or exceeds 2000 rows.
- Resume smoke creates a second provider batch for the same job.
- Any edit under `/workspace/tests/**`.
- Any automatic GitHub comment or issue mutation from repository code.

## PR artifact/commit rules

- Branch name: `cursor/campaign-smoke-cost-gate-86b0`
- Commit deterministic ids, seven `{feature}_cost_report.json` files, `{feature}_resume_evidence.json`, and `parent_cost_aggregate.json` during review.
- Do not commit `APPROVED.txt`; that file is human-created after parent issue review.
- Delete any throwaway debug scripts before merge; keep the smoke CLI and cost report modules.
- PR title: `Add ten-post smoke cost reports and campaign approval gate`
- PR body must paste the parent aggregate totals and link to the seven per-feature reports.
