# Step 1: Add Twitter campaign config, copy posts.csv to S3, and wire smoke tooling

## Goal

Campaign workers need the pinned Twitter csv on S3, a campaign YAML, Twitter campaign CLI, a ten-post smoke caller, cost math scaled to 6,374 rows, and watcher flags that resolve Twitter `FeaturePaths`. This pull request ships that product code. It does not label all 6,374 posts.

## Dependencies

None. Later steps use these identities:

| Field | Value |
|-------|-------|
| Platform | `twitter` |
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Pinned preprocessed run | `2026_09_06-19:28:47` |
| Preprocessed row count | `6374` |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Batch size | `2000` |

Requires Git LFS, AWS credentials with `s3:PutObject`, `s3:GetObject`, and `s3:HeadObject` on `mirrorview-experimental-artifacts`, and `LAB_AWS_ACCESS_KEY_ID` / `LAB_AWS_ACCESS_KEY_SECRET` exported as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

## Main caller and implementation scope

**Upload caller:** `data_platform/scripts/migrate_twitter_preprocessed_to_s3.py` `main`.

**Verifier:** `data_platform/scripts/verify_twitter_preprocessed_s3.py` `main`.

**Campaign caller after this PR merges:**

```bash
PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --features is_news_or_opinion \
  --batch-size 2000
```

**Smoke caller after this PR merges:**

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --feature is_news_or_opinion \
  --smoke-prefix s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/twitter_step1_campaign_smoke/ \
  --output-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/_step1_disposable
```

**One implementation scope:** upload the one pinned `posts.csv`, write inventory JSON, add the campaign YAML and a loader that accepts only this campaign id, wire `generate_twitter_features.py` campaign flags and Python API like `generate_bluesky_features.py`, add `smoke_twitter_campaign.py` sharing helpers with `smoke_bluesky_campaign.py`, extend the ten-row sample loader to accept `TWITTER_SPEC`, extend `campaign_cost_report.py` with `--full-run-row-count` so Twitter can pass `6374` without changing the Bluesky default of `200000`, and add watcher `--platform` and `--dataset-id` that call `FeaturePaths.for_campaign`. Replace `FeaturePaths.canonical` calls in the watcher with `FeaturePaths.for_campaign`. Default omitted watcher flags to today's Bluesky platform and dataset id.

**Out of scope:** labeling all 6,374 rows, posting to GitHub from repository code, wide join, curation, lifecycle rules, converting csv to parquet, dropping Git LFS, changing `FEATURE_REGISTRY`, and the official seven-feature smoke on the primary campaign prefix (Step 2).

Optional live proof uses only the disposable S3 prefix above. Delete that prefix before merge. Do not write primary `batches/part-*.parquet` objects.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json` | Format `csv` must stay |
| `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/metadata.json` | Row count 6374 |
| `/workspace/.gitattributes` | Twitter csv LFS rule |
| `/workspace/data_platform/scripts/migrate_bluesky_lfs_to_s3.py` | Upload and hash pattern |
| `/workspace/data_platform/generate_features/generate_bluesky_features.py` | Campaign Python API to copy |
| `/workspace/data_platform/generate_features/generate_twitter_features.py` | Missing `campaign_id` today |
| `/workspace/data_platform/generate_features/platform_cli.py` | Shared campaign CLI already passes `spec.platform` |
| `/workspace/data_platform/generate_features/smoke_bluesky_campaign.py` | Smoke, interrupt resume, S3 checks |
| `/workspace/data_platform/generate_features/deterministic_smoke_sample.py` | Hard-coded Bluesky spec today |
| `/workspace/data_platform/generate_features/campaign_cost_report.py` | `FULL_RUN_POST_COUNT = 200000` |
| `/workspace/data_platform/generate_features/feature_progress_watcher.py` | Calls missing `FeaturePaths.canonical` |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `FeaturePaths.for_campaign` |
| `/workspace/data_platform/generate_features/generate_features.py` | `_smoke_rows_by_id` fold into `part-00000` |
| `/workspace/AGENTS.md` | `PYTHONPATH=.` and AWS export |

## Files allowed to change

- `/workspace/data_platform/scripts/migrate_twitter_preprocessed_to_s3.py` (new)
- `/workspace/data_platform/scripts/verify_twitter_preprocessed_s3.py` (new)
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/s3_preprocessed_inventory.json` (new)
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml` (new)
- `/workspace/data_platform/generate_features/twitter_campaign_config.py` (new loader)
- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py` (new)
- `/workspace/data_platform/generate_features/deterministic_smoke_sample.py`
- `/workspace/data_platform/generate_features/campaign_cost_report.py`
- `/workspace/data_platform/generate_features/feature_progress_watcher.py`
- `/workspace/CHANGELOG.md`

Temporary disposable smoke evidence under `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/_step1_disposable/` may be committed during review and must be deleted before merge.

Do not edit files under `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/` during implementation except this step file when correcting the spec.

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/**`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/**`
- `/workspace/data_platform/data/bluesky/**`
- `/workspace/data_platform/data/reddit/**`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- Any test file under `/workspace/tests/`
- Any file outside the allowed list

## Locked contracts

| Item | Value |
|------|-------|
| S3 bucket | `mirrorview-experimental-artifacts` |
| AWS region | `us-east-2` |
| Upload scope | `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv` only |
| Expected object count | `1` |
| Hash | SHA-256 lowercase hex of full object bytes. Never use S3 ETag as a content hash. |
| LFS retention | Do not remove or rewrite the csv pointer in git |
| Inventory path | `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/s3_preprocessed_inventory.json` |
| Pointer rejection | If the scoped file begins with `version https://git-lfs.github.com/spec/v1`, abort after `git lfs pull` |
| YAML campaign id | `twitter_2026_09_06_192847_llm_features_v1` only |
| Loader failure | Any other campaign id raises `ValueError` naming the bad id |

Inventory JSON shape:

`{"bucket":"mirrorview-experimental-artifacts","region":"us-east-2","dataset_id":"twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547","preprocessed_run":"2026_09_06-19:28:47","uploaded_at":"<UTC from lib.timestamp_utils.get_current_timestamp>","object_count":1,"objects":[{"repo_relative_path":"...","s3_key":"...","bytes":N,"sha256":"..."}]}`

Primary S3 object after upload:

`s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv`

## Ordered implementation work

1. Add migrate and verify scripts for the single frozen csv path. Pull LFS, reject pointer text, upload, hash, write inventory.
2. Add the campaign YAML and loader.
3. Add `campaign_id` and `preprocessed_run` to `generate_twitter_features()`.
4. Parameterize `load_deterministic_ten_posts` with a platform spec. Twitter smoke passes `TWITTER_SPEC`.
5. Add `smoke_twitter_campaign.py` with interrupt-and-resume support, S3 smoke objects, and `--smoke-prefix`.
6. Add `--full-run-row-count` to `campaign_cost_report.py` aggregate mode. Default remains `200000`.
7. Add watcher `--platform` and `--dataset-id`. Call `FeaturePaths.for_campaign`. Keep Bluesky defaults when flags are omitted.
8. Run live smoke commands below. Delete the disposable prefix and `_step1_disposable` Git copies before merge.

## Live smoke and basic check commands

From the repo root. Export AWS credentials first:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity
```

Expected: JSON with `"Arn"` containing the lab IAM user and exit code 0.

```bash
git lfs pull --include "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv"
```

Expected: exit code 0. The file is larger than 2,000 bytes and is not an LFS pointer:

```bash
python3 -c "
from pathlib import Path
p = Path('data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv')
head = p.read_bytes()[:40]
assert not head.startswith(b'version https://git-lfs.github.com/spec/v1'), head
assert p.stat().st_size > 2000, p.stat().st_size
print('csv smudged ok', p.stat().st_size)
"
```

Expected: `csv smudged ok` plus a byte size near 2,584,416.

```bash
PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py
PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py
```

Expected: migration reports `uploaded 1 object`. Verifier prints `OK: 1/1 objects present with matching sha256`.

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; c=load_twitter_campaign_config('twitter_2026_09_06_192847_llm_features_v1'); print(c['row_count'], c['engine_type'], len(c['features']))"
```

Expected: `6374 openai 7`.

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; load_twitter_campaign_config('bluesky_2026_09_03_235130_llm_features_v1')"
```

Expected: non-zero exit and `ValueError` naming the rejected campaign id.

```bash
DISPOSABLE_PREFIX=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/twitter_step1_campaign_smoke/
PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --feature is_news_or_opinion \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --output-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/_step1_disposable
```

Expected: `smoke_rows=10`, `full_run_row_count=6374`, `no_batches_prefix_objects=true`, `primary_smoke_prefix_touched=false`. Then delete the disposable prefix and the `_step1_disposable` Git directory.

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --feature is_news_or_opinion \
  --platform twitter \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --once
```

Expected: exit 0. Printed markdown only. No GitHub API write.

```bash
git lfs ls-files | grep "twitter_fba4ddb2" | grep "posts.csv"
```

Expected: the preprocessed `posts.csv` line remains.

## Acceptance criteria

- The scoped csv exists in S3 at the repo-relative key with matching SHA-256 in the inventory.
- Git still tracks the csv as LFS. `dataset.json` still says `format: csv`.
- YAML loader returns the seven features and rejects any other campaign id.
- `generate_twitter_features.py` accepts `--campaign-id` with `--preprocessed-run`.
- Disposable-prefix smoke writes ten rows and no production batch objects.
- Watcher resolves Twitter paths through `FeaturePaths.for_campaign`.
- No automated tests added or run.

## Failure conditions

- Verification accepts ETag instead of SHA-256.
- The csv uploads as an LFS pointer.
- S3 key starts with `data_platform/data_platform/`.
- Raw Twitter csv, Bluesky paths, or Reddit paths appear in the inventory.
- Git LFS pointer is removed.
- `FEATURE_REGISTRY` defaults change.
- Primary campaign `batches/` objects are written in this PR.
- Any pytest file is added or run.

## PR artifact and commit rules

- One independently mergeable PR for this step only.
- Bottom of the GitHub stack. Base `main`.
- Logical commits: migrate scripts, YAML and loader, campaign CLI, smoke and watcher, inventory after successful upload, changelog.
- Delete disposable smoke Git copies before merge.
- PR title suggestion: `Add Twitter LLM campaign config, S3 csv copy, and smoke tooling`.

## GitHub issue body

Upload the pinned Twitter preprocessed posts csv (6374 rows, run `2026_09_06-19:28:47`) to `mirrorview-experimental-artifacts`, add campaign YAML for `twitter_2026_09_06_192847_llm_features_v1`, wire Twitter campaign mode, and add smoke, cost, and watcher tooling. Keep Git LFS unchanged. Do not label all 6,374 posts in this pull request.

Plan step: `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md`

Done when:

- `posts.csv` is on S3 at the repo-relative key with matching SHA-256 in the inventory.
- Git still tracks the csv as LFS. No Bluesky or Reddit paths were uploaded.
- Campaign YAML loads for this campaign id only.
- Smoke and watcher commands in the step file pass on a disposable prefix.
- No production `batches/part-*.parquet` objects were written.

Ship as one PR. Do not bundle with sibling issues.

## Pull request description

# Add Twitter LLM campaign config, S3 csv copy, and smoke tooling

Fixes #<child>

Part of #<parent>

## Problem

Pull request 215 left 6,374 preprocessed Twitter posts in Git LFS csv. Campaign workers need those bytes on `mirrorview-experimental-artifacts`, a Twitter campaign id, and smoke tooling before anyone labels the full set.

## Solution

Upload only `posts.csv`. Add `mirrorview_2026-09-05_llm_features_v1.yaml` and a loader that accepts that campaign id only. Wire `generate_twitter_features.py` campaign flags. Add `smoke_twitter_campaign.py`, `--full-run-row-count` on the cost aggregator, and watcher `--platform` / `--dataset-id`.

## Purpose

Step 2 depends on S3-hosted input and smoke tooling. Changing `StorageManager`, converting the dataset to parquet, or labeling 6,374 rows is out of scope.

## How to run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
git lfs pull --include "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/2026_09_06-19:28:47/posts.csv"
PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py
PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py
```

Expected: `uploaded 1 object`, then `OK: 1/1 objects present with matching sha256`.
