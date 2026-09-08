# Step 3: Aggregate cost, post comments, verify S3, and open the draft pull request

## Scope

- **Caller:** `data_platform/generate_features/campaign_cost_report.py` `main`.
- **Task:** Write the parent aggregate, comment costs on GitHub, verify S3 smoke-only prefixes, and open the stacked pull request as a draft.
- **Out of scope:** Labeling 6,408 rows, writing `*_run_report.md`, deleting Git smoke copies, marking the pull request ready, pytest, product Python, editing the parent issue body.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/campaign_cost_report.py`
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/{feature}/{feature}_cost_report.json` for all seven features
- `/workspace/.cursor/skills/write-pr-description/SKILL.md`
- `/workspace/.cursor/skills/write-pr-description/types/feature/guide.md`
- `/workspace/.cursor/skills/write-pr-description/types/feature/template.md`

## Files allowed to change

- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/parent_cost_aggregate.json`
- `/workspace/CHANGELOG.md` only if a one-line Phase A note is added (optional)

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- Parent issue 251 body

## Work

### Aggregate

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export PYTHONPATH=.

PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id twitter_2026_09_08_014808_llm_features_v1 \
  --smoke-reports-dir docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke \
  --output docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/parent_cost_aggregate.json \
  --full-run-row-count 6408
```

Expected:

```text
features_included=7
full_run_row_count=6408
parent_cost_aggregate.json written
```

Copy the log to `/opt/cursor/artifacts/`.

### GitHub comments

Post each per-feature `estimated_full_run_usd_avg` and `estimated_full_run_usd_max` as a comment on issue 255. Post the `parent_cost_aggregate.json` contents as a comment on issue 251, including `full_run_row_count` 6408, the average, the max, and that production waits on owner sign-off. Do not edit the parent issue body. Do not use a closing keyword on 251.

If `gh issue comment` is denied, retry with `export GH_TOKEN="$METRESEARCHGROUP_GITHUB_PAT_TOKEN"`. If that still fails, put the exact comment texts in the pull request body and return them to the epic manager.

The watcher CLI must never post these comments.

### S3 verify

For each feature:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_news_or_opinion/ --recursive
```

Expected after Phase A: smoke objects only. No `batches/part-*.parquet`. `resume_evidence.json` only under `is_news_or_opinion/smoke/`.

Copy each listing to `/opt/cursor/artifacts/`.

### Draft pull request

Stay on `cursor/epic-251-255-smoke-generate-seven-llm-8500`. Do not run `gh pr create`. Open with `gh stack submit --auto` without `--open` so the new pull request stays draft.

Then `gh pr edit` so the body includes `Fixes #255` and `Part of #251`. Never a closing keyword on 251.

Suggested title: `Smoke and generate seven LLM features for the new Twitter posts`.

The body must say this pull request is Phase A only until owner sign-off, and Phase B is blocked until that comment. Write the body as a feature pull request using write-pr-description.

If `gh stack submit` write is denied, `git push -u origin cursor/epic-251-255-smoke-generate-seven-llm-8500` and open a draft pull request with base `cursor/epic-251-254-campaign-yaml-loader-s3-8500`.

## Pass

- Aggregate JSON exists with seven features and `full_run_row_count` 6408.
- Issue comments exist, or the exact texts are in the pull request body.
- S3 listings show smoke only.
- The stack pull request is draft. Body has `Fixes #255` and `Part of #251`.
- The body states Phase A only until owner sign-off.

## Fail

- Phase B production starts.
- Parent issue body is edited.
- A closing keyword is used on 251.
- The pull request is marked ready.
- Watcher posts to GitHub.
- Pytest is added or run.
