# Step 3: Add campaign YAML for the new collection, unlock the campaign loader, copy posts.csv to S3

## Goal

Campaign workers need the new preprocessed csv on S3, a campaign YAML for the Step 2 identities, and a loader that finds that YAML by `campaign_id` without breaking the 2026-09-05 campaign. This pull request ships that product code. It does not label the full preprocessed set.

## Dependencies

- **Step 2 merged** on the GitHub stack: preprocessed run timestamp, row count, Git LFS `posts.csv`.

Requires Git LFS, AWS credentials with `s3:PutObject`, `s3:GetObject`, and `s3:HeadObject` on `mirrorview-experimental-artifacts`, and `LAB_AWS_ACCESS_KEY_ID` / `LAB_AWS_ACCESS_KEY_SECRET` exported as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

## Caller / unit of work

**Upload caller:** `data_platform/scripts/migrate_twitter_preprocessed_to_s3.py` `main`.

**Verifier:** `data_platform/scripts/verify_twitter_preprocessed_s3.py` `main`.

**Campaign caller after this PR merges** (replace `{preprocessed_run}` and `{campaign_id}` from Step 2):

```bash
PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run {preprocessed_run} \
  --campaign-id {campaign_id} \
  --features is_news_or_opinion \
  --batch-size 2000
```

**Smoke caller after this PR merges:**

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id {campaign_id} \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run {preprocessed_run} \
  --feature is_news_or_opinion \
  --smoke-prefix s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/twitter_2026_09_07_step3_campaign_smoke/ \
  --output-dir docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/smoke/_step3_disposable
```

**One implementation scope:** add `--dataset-id` and `--preprocessed-run` to migrate and verify so they no longer pin `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` / `2026_09_06-19:28:47`. Upload the new dataset's `posts.csv` only. Write inventory JSON under the new dataset. Add `mirrorview_2026-09-07_llm_features_v1.yaml`. Change `load_twitter_campaign_config` to scan `data_platform/generate_features/configs/twitter/*.yaml` for matching `campaign_id`. Keep the 2026-09-05 YAML loadable. Optional live proof uses only the disposable S3 prefix above.

**Out of scope:** labeling the full preprocessed set, posting to GitHub, wide join, curation, lifecycle rules, converting csv to parquet, dropping Git LFS, changing `FEATURE_REGISTRY`, changing `twitter/mirrorview.yaml`, the official seven-feature smoke on the primary campaign prefix (Step 4), adding pytest.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/campaign_contract.md` | Identities and YAML shape. |
| `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/metadata.json` | Run timestamp and row count. |
| `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml` | Shape to copy. Do not edit. |
| `/workspace/data_platform/generate_features/twitter_campaign_config.py` | Today accepts only `twitter_2026_09_06_192847_llm_features_v1`. |
| `/workspace/data_platform/scripts/migrate_twitter_preprocessed_to_s3.py` | Hardcoded old dataset id and run. |
| `/workspace/data_platform/scripts/verify_twitter_preprocessed_s3.py` | Imports those constants. |
| `/workspace/data_platform/generate_features/smoke_twitter_campaign.py` | Calls `load_twitter_campaign_config`. Interrupt-resume only for `is_news_or_opinion`. |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `FeaturePaths.for_campaign`. |
| `/workspace/AGENTS.md` | `PYTHONPATH=.` and AWS export. |

## Files allowed to change

- `/workspace/data_platform/scripts/migrate_twitter_preprocessed_to_s3.py`
- `/workspace/data_platform/scripts/verify_twitter_preprocessed_s3.py`
- `/workspace/data_platform/generate_features/twitter_campaign_config.py`
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml` (new)
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/s3_preprocessed_inventory.json` (new)
- `/workspace/CHANGELOG.md`

Temporary disposable smoke evidence under `docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/reports/smoke/_step3_disposable/` may be committed during review and must be deleted before merge.

Do not edit files under `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/`.

## Files forbidden to change

- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py`
- `/workspace/data_platform/generate_features/generate_twitter_features.py`
- `/workspace/data_platform/generate_features/campaign_cost_report.py`
- `/workspace/data_platform/generate_features/feature_progress_watcher.py`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/curate/consolidate.py`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**`
- `/workspace/data_platform/data/bluesky/**`
- `/workspace/data_platform/data/reddit/**`
- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- `/workspace/tests/**`
- Any file outside the allowed list

## Locked contracts

Migrate and verify take required `--dataset-id` and `--preprocessed-run`. They must not default to the 2026-09-05 dataset. Inventory path is derived:

`data_platform/data/twitter/{dataset_id}/s3_preprocessed_inventory.json`

Scoped upload path:

`data_platform/data/twitter/{dataset_id}/preprocessed/{preprocessed_run}/posts.csv`

Expected object count remains 1. Hash is SHA-256 of bytes. Never use S3 ETag. If the scoped file begins with `version https://git-lfs.github.com/spec/v1`, abort after `git lfs pull`.

Loader contract for `load_twitter_campaign_config(campaign_id)`:

1. Iterate YAML files under `data_platform/generate_features/configs/twitter/`.
2. Load each mapping. If `campaign_id` matches, return it.
3. If two files match, raise `ValueError` naming the id.
4. If none match, raise `ValueError` whose message includes `unsupported twitter campaign id: {campaign_id}`.

Remove the single-file `ACCEPTED_CAMPAIGN_ID` / `CAMPAIGN_YAML_PATH` lock.

After this change:

- `load_twitter_campaign_config("twitter_2026_09_06_192847_llm_features_v1")` still returns the 2026-09-05 YAML (`row_count` 6374).
- `load_twitter_campaign_config("{new_campaign_id}")` returns the 2026-09-07 YAML.
- `load_twitter_campaign_config("bluesky_2026_09_03_235130_llm_features_v1")` still raises and names that id.

New YAML fields: see `campaign_contract.md`. `row_count` and `preprocessed_run` come from Step 2, not 6374 / `2026_09_06-19:28:47`.

`smoke_twitter_campaign.py` already writes `resume_evidence.json` only for `is_news_or_opinion`. Do not change that.

## Ordered implementation work

1. Add required `--dataset-id` and `--preprocessed-run` to migrate and verify. Derive inventory and csv paths from those flags. Upload one object. Write inventory under the new dataset.
2. Add the 2026-09-07 campaign YAML using Step 2 identities.
3. Change `load_twitter_campaign_config` to directory lookup.
4. Run migrate and verify against the new dataset.
5. Prove both campaign ids load. Prove an unknown id fails.
6. Optional: one disposable `is_news_or_opinion` smoke under `_smoke/twitter_2026_09_07_step3_campaign_smoke/`. Delete that prefix and Git copies before merge. Do not write primary `batches/part-*.parquet`.

## Exact commands and expected output

From the repo root:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity
```

Expected: JSON with `"Arn"` containing the lab IAM user and exit 0.

```bash
git lfs pull --include "data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/posts.csv"
python3 -c "
from pathlib import Path
p = Path('data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/posts.csv')
head = p.read_bytes()[:40]
assert not head.startswith(b'version https://git-lfs.github.com/spec/v1'), head
assert p.stat().st_size > 2000, p.stat().st_size
print('csv smudged ok', p.stat().st_size)
"
```

Expected: `csv smudged ok` plus a byte size.

```bash
PYTHONPATH=. uv run python data_platform/scripts/migrate_twitter_preprocessed_to_s3.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run {preprocessed_run}
PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run {preprocessed_run}
```

Expected: migration reports `uploaded 1 object`. Verifier prints `OK: 1/1 objects present with matching sha256`.

Running migrate without flags must be non-zero. Running it against the old dataset id is allowed only as an extra check; this pull request's inventory file must be the new dataset's file.

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; c=load_twitter_campaign_config('{campaign_id}'); print(c['row_count'], c['engine_type'], len(c['features']), c['dataset_id'])"
```

Expected: `{row_count} openai 7 twitter_5901767a-e609-46fc-9a17-742516b548f2`.

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; c=load_twitter_campaign_config('twitter_2026_09_06_192847_llm_features_v1'); print(c['row_count'], c['dataset_id'])"
```

Expected: `6374 twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547`.

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; load_twitter_campaign_config('bluesky_2026_09_03_235130_llm_features_v1')"
```

Expected: non-zero exit and `ValueError` naming the rejected campaign id.

If the optional disposable smoke runs, expected stdout includes `s3_smoke_resume_evidence_ok` for `is_news_or_opinion`. Delete the disposable prefix before merge.

Do not add pytest.

## Pass / fail

The step passes when the new YAML loads by campaign id, the old campaign still loads, unknown ids fail with the id in the message, migrate and verify take dataset id and run flags, one new `posts.csv` object is on S3 with matching SHA-256, and Git LFS still holds the local copy.

The step fails when any item below is true.

- loader still accepts only `twitter_2026_09_06_192847_llm_features_v1`
- 2026-09-05 YAML was edited or no longer loads
- migrate still pins the old csv when invoked for the new dataset
- raw csv, Bluesky, or Reddit objects were uploaded
- SHA-256 was taken from ETag
- LFS pointer text was uploaded
- official seven-feature production labeling started
- pytest was added

## PR artifact and commit rules

- One independently mergeable PR stacked on Step 2.
- Logical commits: loader plus migrate/verify flags, new YAML, inventory, changelog.
- PR title suggestion: `Add campaign YAML for the new collection, unlock the campaign loader, copy posts.csv to S3`.
