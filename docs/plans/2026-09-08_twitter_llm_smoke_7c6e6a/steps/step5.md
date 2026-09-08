# Step 5: Write run reports, delete Git smoke copies, and mark the pull request ready

## Scope

- **Caller:** none. The step writes documentation from the Phase B S3 results.
- **Task:** Write seven permanent run reports, delete the temporary Git smoke copies, and mark the stack pull request ready.
- **Out of scope:** Starting this step in the Phase A round. Product Python. Pytest. Editing parent issue 251 body.

Phase B waits for Step 4. Do not run this step in the Phase A round.

## Files to inspect (read-only)

- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/is_news_or_opinion_run_report.md` (shape to copy)
- S3 `manifest.json`, `progress.jsonl`, and cost fields for each Twitter feature

## Files allowed to change

- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/is_news_or_opinion_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/is_political_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/is_likely_spam_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/is_self_contained_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/is_structurally_complete_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/political_stance_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/llm_toxicity_tiered_run_report.md` (new, keep)
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/**` (delete the temporary Git copies)
- `/workspace/CHANGELOG.md`

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`

## Work

Each run report must include S3 URIs, manifest SHA-256, model id `gpt-5.4-nano`, prompt hash, estimated and actual USD, part counts, unique id count 6408, and a note that Git smoke copies were removed.

Delete the temporary Git copies under `docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/`. Do not delete S3 smoke objects.

Stay on `cursor/epic-251-255-smoke-generate-seven-llm-8500`. Commit, push, and mark the stack pull request ready. Do not force push. Do not amend. Do not merge.

## Pass

- Seven run reports are committed.
- Temporary Git smoke copies are gone.
- S3 smoke objects remain.
- The stack pull request is ready for review.

## Fail

- Run reports or Git-copy deletion start in the Phase A round.
- Run reports are written before production `final.parquet` exists.
- Product Python changes.
- Pytest is added or run.
