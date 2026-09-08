# Step 1: Require dataset id and preprocessed run on migrate and verify

## Scope

- **Caller:** `data_platform/scripts/migrate_twitter_preprocessed_to_s3.py` `main`, then `data_platform/scripts/verify_twitter_preprocessed_s3.py` `main`.
- **Task:** Add required `--dataset-id` and `--preprocessed-run`. Derive inventory and csv paths from those flags. Do not default to the 2026-09-05 dataset.
- **Out of scope:** Uploading in this step, campaign YAML, loader change, labeling, pytest, smoke.

## Files to inspect (read-only)

- `/workspace/data_platform/scripts/migrate_twitter_preprocessed_to_s3.py`
- `/workspace/data_platform/scripts/verify_twitter_preprocessed_s3.py`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/s3_preprocessed_inventory.json` (shape to copy later. Do not edit.)

## Files allowed to change

- `/workspace/data_platform/scripts/migrate_twitter_preprocessed_to_s3.py`
- `/workspace/data_platform/scripts/verify_twitter_preprocessed_s3.py`

## Files forbidden to change

- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`
- `/workspace/data_platform/generate_features/twitter_campaign_config.py`
- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py`
- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/curate/consolidate.py`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- Any file under `/workspace/tests/`
- Any file outside the allowed list for this pull request

## Locked contracts

Required flags: `--dataset-id` and `--preprocessed-run`. No default dataset id. No default preprocessed run. Running without flags must be non-zero.

Scoped upload path:

```text
data_platform/data/twitter/{dataset_id}/preprocessed/{preprocessed_run}/posts.csv
```

Inventory path:

```text
data_platform/data/twitter/{dataset_id}/s3_preprocessed_inventory.json
```

Expected object count stays 1. Hash is SHA-256 of bytes. Never use S3 ETag. Abort if the scoped file begins with `version https://git-lfs.github.com/spec/v1`.

Do not upload raw csv, metadata, Bluesky, or Reddit.

## Given / when / then (Phase 4, no new pytest)

```text
given the migrate script with no command flags
when PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py
then exit code is non-zero

given the verify script with no command flags
when PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py
then exit code is non-zero
```

## Exact commands and expected output

```bash
PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py
echo migrate_exit=$?
PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py
echo verify_exit=$?
```

Expected: both exit codes are non-zero. Stderr names the missing `--dataset-id` and `--preprocessed-run` flags.

Do not add pytest.

## Pass / fail

The step passes when both scripts require the two flags and exit non-zero without them, and paths are derived from those flags.

The step fails when any item below is true.

- either script still pins `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` or `2026_09_06-19:28:47` as a default
- missing flags exit 0
- pytest was added
