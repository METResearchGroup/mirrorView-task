# Step 3: Post the cost estimate and hand off to Phase B

## Goal

Give the parent issue the number it needs for the aggregate estimate, push the branch for review, and record what Phase B must do once the parent issue has sign-off.

## Files to inspect (read-only)

- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_cost_report.json`
- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/llm_toxicity_tiered/llm_toxicity_tiered_resume_evidence.json`

## Files allowed to change

None.

## Commands

### Post the estimate on issue #194

Read `model`, `avg_input_tokens_per_request`, `max_input_tokens_per_request`, `avg_output_tokens_per_request`, `max_output_tokens_per_request`, `smoke_cost_usd`, `estimated_full_run_usd_avg`, and `estimated_full_run_usd_max` from the cost report, and `batch_id` plus `submit_calls_after_resume` from the resume evidence. Then post one short markdown comment.

```bash
gh issue comment 194 --repo METResearchGroup/mirrorView-task --body "<markdown>"
```

Expected: the command prints the comment URL. If the command fails because the token cannot comment, do not retry. Put the same text in the PR body under the heading "Cost estimate (to be posted on #194)" and say in the report that it was not posted.

### Push the branch

```bash
git push -u origin cursor/epic-180-194-generate-llm-toxicity-tiered-d983
```

The PR is opened by the epic manager with base `cursor/epic-180-193-generate-political-stance-d983`. The body must include `Fixes #194` and `Part of #180`, must say that this PR is Phase A only, that the 200,000-post run has not started and waits for explicit sign-off on #180, and that the temporary smoke artifacts will be deleted and replaced by the permanent run report in Phase B before merge.

## Must pass

- Issue #194 shows the estimate comment, or the PR body carries the same text and the report says it was not posted.
- The branch is pushed and the diff against the parent branch contains only the new plan folder and the three temporary smoke artifacts.

## Phase B hand-off

Phase B starts only after the parent issue #180 has explicit sign-off. It follows `step14.md` "Phase B: full run after parent approval" in the same PR and branch. The operator does the following, in order.

- Run the campaign CLI command from `step14.md` with `--features llm_toxicity_tiered` and `--batch-size 2000`. The same command resumes automatically.
- Run the Step 7 watcher at every 10,000 durable rows and post the rolling comment on issue #194.
- Run the validation commands from `step14.md` against `final.parquet`, `manifest.json`, and `progress.jsonl`, including the check that every `toxicity_tier` value is `low`, `medium`, or `high`, that `toxicity_prob` is absent, and that nothing exists under `is_toxic_tiered/`.
- Write `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/llm_toxicity_tiered_run_report.md`, including the explicit statement that `is_toxic_tiered` was not run.
- Delete the three temporary smoke artifacts from Git and push. The S3 smoke evidence stays.

The first production provider job labels 1,990 posts, and `part-00000.parquet` holds those rows plus the ten unchanged smoke rows with their original `batch_id` and `request_id`.
