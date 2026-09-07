# Step 1: Confirm Step 1 tooling is on the stack

## Scope

- **Caller:** none. The step is a read-only gate before live smokes.
- **Task:** Confirm the Step 1 smoke caller, campaign YAML, cost aggregate `--full-run-row-count`, and watcher `--platform` / `--dataset-id` flags exist on branch `cursor/epic-232-234-smoke-generate-seven-llm-features-8500`, stacked on `cursor/epic-232-233-twitter-campaign-config-smoke-8500` (pull request 238).
- **Out of scope:** Editing product Python, running smoke, labeling 6,374 rows, pytest.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py`
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`
- `/workspace/data_platform/generate_features/campaign_cost_report.py`
- `/workspace/data_platform/generate_features/feature_progress_watcher.py`
- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`

## Files allowed to change

None.

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/plan.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step3.md`

## Work

Confirm `git branch --show-current` prints `cursor/epic-232-234-smoke-generate-seven-llm-features-8500`. Do not check out `main`. Do not create a new branch.

Confirm these facts:

1. `smoke_twitter_campaign.py` exists and interrupt-and-resume, including `resume_evidence.json`, runs only for `is_news_or_opinion`.
2. Campaign YAML `campaign_id` is `twitter_2026_09_06_192847_llm_features_v1`, `row_count` is `6374`, `batch_size` is `2000`, `model_id` is `gpt-5.4-nano`, and the feature list matches the serial order in this plan.
3. `campaign_cost_report.py` accepts `--full-run-row-count`.
4. `feature_progress_watcher.py` accepts `--platform` and `--dataset-id`, requires `--once`, and prints `github_write_skipped=true`.
5. Primary S3 feature prefixes under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/` have no leftover `batches/part-*.parquet` objects.

## Pass

- Branch name matches.
- The four product files above exist on this stack.
- YAML identities match the campaign contract.
- Primary prefixes have no production batch objects.

## Fail

- Any of those files is missing.
- YAML identities differ from the campaign contract.
- A `batches/part-*.parquet` object already exists for this campaign.
- The working tree is on `main` or on a newly created branch.
