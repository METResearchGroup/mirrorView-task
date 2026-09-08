# Step 1: Confirm Step 3 tooling is on the stack

## Scope

- **Caller:** none. The step is a read-only gate before live smokes.
- **Task:** Confirm the smoke caller, campaign YAML, cost aggregate `--full-run-row-count`, and S3 csv exist on branch `cursor/epic-251-255-smoke-generate-seven-llm-8500`, stacked on `cursor/epic-251-254-campaign-yaml-loader-s3-8500` (pull request 263).
- **Out of scope:** Editing product Python, running smoke, labeling 6,408 rows, pytest.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py`
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml`
- `/workspace/data_platform/generate_features/campaign_cost_report.py`
- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/2026_09_08-01:48:08/posts.csv`

## Files allowed to change

None.

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`

## Work

Confirm `git branch --show-current` prints `cursor/epic-251-255-smoke-generate-seven-llm-8500`. Do not check out `main`. Do not create a new branch.

Confirm these facts:

1. `smoke_twitter_campaign.py` exists and interrupt-and-resume, including `resume_evidence.json`, runs only for `is_news_or_opinion`.
2. Campaign YAML `campaign_id` is `twitter_2026_09_08_014808_llm_features_v1`, `row_count` is `6408`, `batch_size` is `2000`, `model_id` is `gpt-5.4-nano`, `dataset_id` is `twitter_5901767a-e609-46fc-9a17-742516b548f2`, `preprocessed_run` is `2026_09_08-01:48:08`, and the feature list matches the serial order in this plan.
3. `campaign_cost_report.py` accepts `--full-run-row-count`.
4. Local `posts.csv` is real csv bytes, not a Git LFS pointer.
5. Primary S3 feature prefixes under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/` have no leftover `batches/part-*.parquet` objects.

## Pass

- Branch name matches.
- The product files above exist on this stack.
- YAML identities match the locked identities in `plan.md`.
- Primary prefixes have no production batch objects.

## Fail

- Any of those files is missing.
- YAML identities differ from the locked identities, including `row_count` 6374.
- A `batches/part-*.parquet` object already exists for this campaign.
- The working tree is on `main` or on a newly created branch.
