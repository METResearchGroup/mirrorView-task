# Step 4: Wire smoke, cost row count, and watcher flags

## Scope

- **Caller:** `data_platform/generate_features/smoke_twitter_campaign.py` `main`, then `data_platform/generate_features/feature_progress_watcher.py` `main`.
- **Task:** Twitter ten-post smoke on a disposable S3 prefix, cost aggregate `--full-run-row-count`, and watcher `--platform` / `--dataset-id` that call `FeaturePaths.for_campaign`.
- **Out of scope:** Labeling 6,374 rows, official seven-feature smoke on the primary campaign prefix, posting to GitHub, pytest, editing `smoke_bluesky_campaign.py`.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/smoke_bluesky_campaign.py` (helpers to import: interrupt, resume, S3 writes, S3 checks)
- `/workspace/data_platform/generate_features/deterministic_smoke_sample.py` (hard-coded `BLUESKY_SPEC` today)
- `/workspace/data_platform/generate_features/campaign_cost_report.py` (`FULL_RUN_POST_COUNT = 200000`, `build_feature_cost_report(..., full_run_post_count=...)`)
- `/workspace/data_platform/generate_features/feature_progress_watcher.py` (calls missing `FeaturePaths.canonical`)
- `/workspace/data_platform/generate_features/s3_feature_campaign.py` (`FeaturePaths.for_campaign`, `DEFAULT_CAMPAIGN_PLATFORM`, `DEFAULT_CAMPAIGN_DATASET_ID`)
- `/workspace/data_platform/generate_features/generate_twitter_features.py` (`TWITTER_SPEC`)
- `/workspace/data_platform/generate_features/twitter_campaign_config.py` (`row_count` 6374)

## Files allowed to change

- `/workspace/data_platform/generate_features/deterministic_smoke_sample.py`
- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py` (new)
- `/workspace/data_platform/generate_features/campaign_cost_report.py`
- `/workspace/data_platform/generate_features/feature_progress_watcher.py`

Temporary Git copies under `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/_step1_disposable/` may exist during the live run and must be deleted before the PR is ready.

## Files forbidden to change

- `/workspace/data_platform/generate_features/smoke_bluesky_campaign.py`
- `/workspace/data_platform/generate_features/s3_feature_campaign.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/generate_features/generate_features.py`
- Any file under `/workspace/tests/`
- Any file outside the allowed list

## Work

### Ten-row sample

Add an optional platform spec argument to `load_deterministic_ten_posts`. Default remains `BLUESKY_SPEC` so existing Bluesky callers stay valid without editing `smoke_bluesky_campaign.py`. Twitter smoke passes `TWITTER_SPEC`.

Selection rule is unchanged: keep rows with non-empty `text`, sort by ascending `source_record_id`, take the first ten.

### Twitter smoke

Add `smoke_twitter_campaign.py`. Import interrupt, resume, object write, and S3 check helpers from `smoke_bluesky_campaign.py`. Do not copy those function bodies.

Rebuild smoke paths with `FeaturePaths.for_campaign(campaign_id, feature, platform="twitter", dataset_id=dataset_id)` instead of the missing `FeaturePaths.canonical`. Refuse a `--smoke-prefix` that overlaps that primary feature prefix.

Call `load_deterministic_ten_posts(..., spec=TWITTER_SPEC)`.

Call `build_feature_cost_report` with `full_run_post_count` equal to YAML `row_count` `6374`, not `FULL_RUN_POST_COUNT`.

Interrupt and resume only the OpenAI Batch job for the requested feature. Default live proof uses `is_news_or_opinion`.

Write untagged smoke objects under the disposable prefix. Never write `batches/part-*.parquet`.

Stdout must include:

```text
smoke_rows=10
full_run_row_count=6374
no_batches_prefix_objects=true
primary_smoke_prefix_touched=false
```

Use `primary_smoke_prefix_touched` rather than the Bluesky name `canonical_smoke_prefix_touched`.

Required flags: `--campaign-id`, `--dataset-id`, `--preprocessed-run`, `--feature`, `--smoke-prefix`, `--output-dir`.

Disposable prefix (only prefix allowed for this PR's live smoke):

`s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/twitter_step1_campaign_smoke/`

### Cost aggregate

Add `--full-run-row-count` to `campaign_cost_report.py` aggregate mode. Default remains `200000` (`FULL_RUN_POST_COUNT`). Include `full_run_row_count` in the aggregate JSON. Print `full_run_row_count=<n>`. Do not change the Bluesky default.

This PR does not run the seven-feature aggregate. Step 2 of the parent epic will pass `--full-run-row-count 6374`.

### Watcher

Add `--platform` and `--dataset-id`. When omitted, use `DEFAULT_CAMPAIGN_PLATFORM` and `DEFAULT_CAMPAIGN_DATASET_ID` from `s3_feature_campaign.py` so existing Bluesky commands still work.

Replace `FeaturePaths.canonical` with `FeaturePaths.for_campaign(campaign_id, feature, platform=platform, dataset_id=dataset_id)`.

Keep `--once` as the only mode. Never post to GitHub. Stdout stays the existing key=value lines plus an optional markdown fence when a 10,000-row boundary is reached. At 6,374 rows that boundary never fires. `github_write_skipped=true` must still print.

## Contracts (implement-from-spec Phase 3)

- `load_deterministic_ten_posts(dataset_id, preprocessed_run, spec=None)`
- `smoke_twitter_campaign.main` flags listed above
- `campaign_cost_report.main` gains `--full-run-row-count` default `FULL_RUN_POST_COUNT`
- `feature_progress_watcher.main` gains `--platform` and `--dataset-id` with Bluesky defaults
- `resolve_feature_paths` calls `FeaturePaths.for_campaign`

## Given / when / then (Phase 4, no pytest)

```text
given the pinned Twitter preprocessed csv already on S3 from step 1
and OPENAI_API_KEY set
and disposable prefix s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/twitter_step1_campaign_smoke/
when PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --feature is_news_or_opinion \
  --smoke-prefix s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/twitter_step1_campaign_smoke/ \
  --output-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/_step1_disposable
then stdout includes smoke_rows=10, full_run_row_count=6374, no_batches_prefix_objects=true, primary_smoke_prefix_touched=false
and no production batches/part-*.parquet object was written
and the command may take several minutes because it waits on OpenAI Batch

given watcher flags for this Twitter campaign
when PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --feature is_news_or_opinion \
  --platform twitter \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --once
then exit 0
and stdout includes github_write_skipped=true
and the process does not call the GitHub API

given the live smoke has been verified
when deleting the disposable S3 prefix and the _step1_disposable Git directory
then those objects and files are gone before the PR is marked ready
```

## Must pass

Export AWS credentials first. Wait for OpenAI Batch. Do not skip the smoke.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
DISPOSABLE_PREFIX=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/twitter_step1_campaign_smoke/
PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --feature is_news_or_opinion \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --output-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/_step1_disposable
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --feature is_news_or_opinion \
  --platform twitter \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --once
```

Copy smoke and watcher stdout to `/opt/cursor/artifacts/`.

Then delete the disposable prefix and `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/_step1_disposable`.

## Must fail

- Smoke that writes primary campaign `batches/` objects
- Watcher posting to GitHub
- Changing `FEATURE_REGISTRY` defaults
- Editing `smoke_bluesky_campaign.py`
- Adding or running pytest
- Leaving `_step1_disposable` files in the PR

## Done when

Disposable-prefix smoke labels ten posts for `is_news_or_opinion`, cost math uses 6374 rows, the watcher resolves Twitter paths through `FeaturePaths.for_campaign`, and disposable evidence is deleted.
