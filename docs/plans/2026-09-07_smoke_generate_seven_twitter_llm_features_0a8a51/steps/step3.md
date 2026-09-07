# Step 3: Aggregate cost, post comments, verify S3, and open the draft pull request

## Scope

- **Caller:** `data_platform/generate_features/campaign_cost_report.py` `main`, then `data_platform/generate_features/feature_progress_watcher.py` `main`.
- **Task:** Write the parent aggregate, comment costs on GitHub, verify S3 smoke-only prefixes, run watcher `--once` on one feature, add a changelog line, and open the stacked pull request as a draft.
- **Out of scope:** Labeling 6,374 rows, writing `*_run_report.md`, deleting Git smoke copies, marking the pull request ready, pytest, product Python, editing the parent issue body.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/campaign_cost_report.py`
- `/workspace/data_platform/generate_features/feature_progress_watcher.py`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/{feature}/{feature}_cost_report.json` for all seven features
- `/workspace/.cursor/skills/write-pr-description/SKILL.md`
- `/workspace/.cursor/skills/write-pr-description/types/feature/guide.md`
- `/workspace/.cursor/skills/write-pr-description/types/feature/template.md`
- `/workspace/.cursor/skills/write-changelog/SKILL.md`

## Files allowed to change

- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/parent_cost_aggregate.json`
- `/workspace/CHANGELOG.md`

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/plan.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step3.md`
- Parent issue 232 body

## Work

### Aggregate

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --smoke-reports-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke \
  --output docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/parent_cost_aggregate.json \
  --full-run-row-count 6374
```

Expected:

```text
features_included=7
full_run_row_count=6374
parent_cost_aggregate.json written
```

Copy the log to `/opt/cursor/artifacts/`.

### GitHub comments

Post each per-feature `estimated_full_run_usd_avg` and `estimated_full_run_usd_max` as a comment on issue 234. Post the `parent_cost_aggregate.json` contents as a comment on issue 232. Do not edit the parent issue body. Do not use a closing keyword on 232.

If `gh issue comment` is denied, put the exact comment texts in the pull request body and return them to the epic manager.

The watcher CLI must never post these comments.

### S3 verify

For each feature:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/ --recursive
```

Expected after Phase A: smoke objects only. No `batches/part-*.parquet`. `resume_evidence.json` only under `is_news_or_opinion/smoke/`.

Copy each listing to `/opt/cursor/artifacts/`.

### Watcher

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --feature is_news_or_opinion \
  --platform twitter \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --once
```

Expected: printed markdown. `github_write_skipped=true`. The 10,000-row milestone is absent.

Copy the log to `/opt/cursor/artifacts/`.

### Draft pull request

Stay on `cursor/epic-232-234-smoke-generate-seven-llm-features-8500`. Do not run `gh pr create`. Open with `gh stack submit --auto` without `--open` so the new pull request stays draft.

Then `gh pr edit` so the body includes `Fixes #234` and `Part of #232`. Never a closing keyword on 232.

Suggested title: `Label 6374 Twitter posts with seven OpenAI LLM features`.

The body must say Phase A is complete and Phase B is blocked on parent owner sign-off. Write the body as a feature pull request using write-pr-description.

If `gh stack submit` write is denied, `git push -u origin cursor/epic-232-234-smoke-generate-seven-llm-features-8500` and open a draft pull request with base `cursor/epic-232-233-twitter-campaign-config-smoke-8500`.

### Changelog

After the pull request number exists (draft is fine), add one `CHANGELOG.md` entry dated 2026-09-07 using write-changelog. Confirm the branch name, commit, and push. No force push. No amend.

## Pass

- Aggregate JSON exists with seven features and `full_run_row_count` 6374.
- Issue comments exist, or the exact texts are in the pull request body.
- S3 listings show smoke only.
- Watcher printed markdown and skipped GitHub write.
- The stack pull request is draft. Body has `Fixes #234` and `Part of #232`.
- Changelog names the pull request.

## Fail

- Phase B production starts.
- Parent issue body is edited.
- A closing keyword is used on 232.
- The pull request is marked ready.
- Watcher posts to GitHub.
- Pytest is added or run.
