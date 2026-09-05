# Step 5: Write resumable 2,000-row Parquet feature batches

## Goal

Write immutable S3-backed feature artifacts for the Bluesky LLM campaign: 2,000-row Parquet batch objects, one consolidated `final.parquet`, a SHA-256 `manifest.json`, append-only `progress.jsonl`, and error records. Preserve deterministic record order across resume and consolidation. Keep one blocking OpenAI Batch job per feature and reuse the hardened resume behavior from Step 4.

## Dependencies

- **Step 2 merged:** S3 object store with conditional put support.
- **Step 4 merged:** `active_openai_batch.json` state contract, partial success retention, four-attempt transient retry, exact input id completeness.
- See `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` for the full layout and Q44 schema.

This step may start after Steps 2 and 4 merge. It does not require Steps 1 or 3.

## Main caller and implementation slice

**Main caller after this PR merges:**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --features is_news_or_opinion \
  --batch-size 2000
```

**One implementation slice for this PR:** add campaign mode flags (`--campaign-id`, `--preprocessed-run`) to `generate_bluesky_features.py`, persist `active_openai_batch.json` in S3, write immutable batch objects under `batches/part-NNNNN.parquet`, implement logical append for `progress.jsonl` and `errors.jsonl`, conditionally replace `manifest.json`, and never mutate an existing batch object.

**Out of scope for this PR:** ten-post smoke cost tooling (Step 6), watcher GitHub comments (Step 7), Step 16 lifecycle rule infrastructure, and joining seven features into one wide artifact.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Canonical S3 layout and Q44 schema |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | Batch completion hook point after Step 4 |
| `/workspace/data_platform/generate_features/generate_features.py` | Orchestrator and completion checks |
| `/workspace/data_platform/generate_features/generate_bluesky_features.py` | Bluesky CLI wrapper |
| `/workspace/data_platform/generate_features/platform_cli.py` | CLI flags |
| `/workspace/data_platform/generate_features/registry.py` | Seven LLM features |
| `/workspace/data_platform/utils/storage.py` | Post-Step-2 S3 storage abstraction; Step 3 default-backend flip is not required for this step |
| `/workspace/lib/aws/s3.py` | Low-level S3 upload and list helpers |
| `/workspace/data_platform/generate_features/is_news_or_opinion/generate_feature.py` | Example output schema |

## Files allowed to change

- `/workspace/data_platform/generate_features/s3_feature_campaign.py` (new; campaign paths, manifest, progress, batch write)
- `/workspace/data_platform/generate_features/s3_feature_batches.py` (new; immutable batch writer and final consolidation)
- `/workspace/data_platform/generate_features/generate_features.py` (wire batch writer after each durable batch)
- `/workspace/data_platform/generate_features/generate_bluesky_features.py` (pass through `--campaign-id` and `--preprocessed-run`)
- `/workspace/data_platform/generate_features/platform_cli.py` (add `--campaign-id` and `--preprocessed-run`; enforce `--batch-size 2000` and exactly one `--features` value for campaign runs)
- `/workspace/data_platform/generate_features/models.py` (campaign config fields if needed)
- `/workspace/data_platform/generate_features/smoke_write_s3_batch.py` (new temporary smoke helper)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step5.md` (this file only if correcting the spec during implementation)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md`, `step6.md`, `step7.md`
- `/workspace/tests/**`
- Feature prompt modules
- `/workspace/webapp/**`
- `/workspace/experiments/**`
- Any repository code that launches Cursor agents or other autonomous agent runners

## Locked contracts

See `campaign_contract.md`. Exact values for this step:

### Feature root

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/`

### Per-feature layout

For `{feature}` = `is_news_or_opinion` (smoke example):

```text
s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/
  active_openai_batch.json
  batches/part-00000.parquet
  batches/part-00001.parquet
  ...
  batches/part-00099.parquet
  final.parquet
  manifest.json
  progress.jsonl
  errors.jsonl
```

Batch object keys are immutable. Never overwrite an existing `part-NNNNN.parquet` key. A full feature run writes exactly 100 batch objects totaling 200,000 rows.

### Production batch schedule

| Canonical part | Provider job size | Row composition |
|----------------|-------------------|-----------------|
| `part-00000` | 1,990 new posts | Ten unchanged smoke output rows (original smoke `batch_id` and `request_id` preserved) plus 1,990 new labeled rows |
| `part-00001` through `part-00099` | 2,000 new posts each | All new labeled rows |

`manifest.json` batch entry for `part_index=0` may list both the smoke provider `batch_id` and the first production provider `batch_id`.

### active_openai_batch.json in S3

Persist Step 4 state at `{feature}/active_openai_batch.json`. Use conditional atomic whole-object replace with S3 `If-Match` ETag for concurrency control. Delete only after successful rows are in an immutable batch object and recorded in `manifest.json`.

### Logical append for progress.jsonl and errors.jsonl

One feature writer:

1. Reads existing object bytes (empty if missing).
2. Appends complete newline-terminated JSON records.
3. Conditionally replaces the whole object using `If-Match` with the prior object ETag.

On conditional put failure, retry from the latest object. Immutable batch objects plus `manifest.json` are the source of truth; resume may reconstruct missing observability events.

`manifest.json` uses the same conditional atomic replace pattern. SHA-256 remains the content integrity check. Never use ETag as a content hash.

### Deterministic run id

Every row carries `run_id` = `bluesky_2026_09_03_235130_llm_features_v1:{feature}`.

### Q44 row columns

Every label row in `batches/part-*.parquet` and `final.parquet` must include:

| Column | Value |
|--------|-------|
| `source_record_id` | pinned input id |
| `run_id` | `bluesky_2026_09_03_235130_llm_features_v1:{feature}` |
| `batch_id` | OpenAI Batch provider id |
| `request_id` | provider request id for the row |
| `attempt_count` | integer 1 through 4 |
| `label_timestamp` | UTC from `lib.timestamp_utils.get_current_timestamp` |
| `{label_field}` | feature-specific raw label column |

Validate the Pydantic model on the label-field subset and provenance columns separately.

### manifest.json

`manifest.json` holds campaign-level immutable metadata only:

- `campaign_id`, `dataset_id`, `preprocessed_run`, `feature`, `model_id`, `prompt_hash`
- `batch_size`, `expected_row_count`, `run_id`, `created_at`
- `batches`: ordered list of `{part_index, key, row_count, sha256, provider_batch_ids}` (part 0 may list two provider batch ids)
- `final_parquet`: `{key, row_count, sha256}` once built

Hash fields are SHA-256 hex digests of file bytes. Never use ETag as a content hash.

### Lifecycle tag on batch objects only

When uploading under `batches/`, set S3 object tag `intermediate-artifact=true`. Do not set that tag on `final.parquet`, `manifest.json`, `progress.jsonl`, or `errors.jsonl`.

### Deterministic order

Input ids are processed in stable ascending `source_record_id` order from preprocessed run `2026_09_03-23:51:30`. Batch row order follows that global order within each 2000-row chunk.

### Campaign mode resume

Re-running the same campaign command with the same `--campaign-id`, `--preprocessed-run`, and single `--features` value automatically resumes from canonical prefix state. Do not add `--resume` or `--checkpoint`.

### Blocking engine

Reuse Step 4 behavior. Batch writing happens only after a provider batch completes and rows pass schema validation.

## Ordered implementation work

1. Add campaign path helpers in `s3_feature_campaign.py` for prefix construction.
2. Implement `active_openai_batch.json` read, conditional write, and delete in S3.
3. Implement immutable batch upload with SHA-256 digest, manifest batch list update, and logical `progress.jsonl` append in `s3_feature_batches.py`.
4. Attach Q44 provenance columns on every row before Parquet write.
5. Wire the batch writer into the batch completion path; refuse campaign runs unless `--batch-size 2000` and exactly one feature.
6. Implement `final.parquet` consolidation and manifest final block when 100 batches and 200,000 rows are present.
7. Add `errors.jsonl` logical append for exhausted per-record failures.
8. Add temporary smoke helper that writes one disposable batch under the non-canonical prefix `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/` only. Never write under the pinned campaign feature `batches/` prefix during this step.
9. Run live smoke commands. Commit temporary smoke evidence. Delete disposable S3 objects, verify the disposable prefix is empty, then delete helper and Git evidence before merge.

## Exact live smoke and basic check commands with expected output

### Offline path helper check

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
from data_platform.generate_features.s3_feature_campaign import feature_prefix, run_id_for_feature
p = feature_prefix('bluesky_2026_09_03_235130_llm_features_v1', 'is_news_or_opinion')
assert p.endswith('features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/')
rid = run_id_for_feature('bluesky_2026_09_03_235130_llm_features_v1', 'is_news_or_opinion')
assert rid == 'bluesky_2026_09_03_235130_llm_features_v1:is_news_or_opinion'
print('feature_prefix OK')
print('run_id OK')
"
```

Expected stdout:

```text
feature_prefix OK
run_id OK
```

### Live one-batch write check (requires `OPENAI_API_KEY` and AWS credentials; available after this step's implementation)

Use the disposable smoke prefix only. Do not write under the pinned campaign feature `batches/` prefix; Step 6 tooling proof and Steps 8 through 14 canonical smoke must not find pre-existing canonical batch objects from this step.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

DISPOSABLE_PREFIX=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/

PYTHONPATH=. uv run python data_platform/generate_features/smoke_write_s3_batch.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --row-count 10
```

Expected stdout:

```text
smoke_prefix=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/
batch_key=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/is_news_or_opinion/batches/part-00000.parquet
batch_sha256=<64-char-hex>
manifest_updated=true
progress_appended=true
intermediate_tag=true
canonical_batches_prefix_touched=false
```

### Resume-without-rewrite check

Run the same command a second time without deleting disposable S3 objects.

Expected stdout:

```text
batch_rewrite_refused=true
next_part_index=1
canonical_batches_prefix_touched=false
```

### Disposable prefix cleanup (required before merge)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/ --recursive
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/ --recursive
```

Expected: `aws s3 rm` reports deleted objects (or no objects found). `aws s3 ls` prints no lines, confirming the disposable prefix is empty.

Verify the canonical campaign feature `batches/` prefix was not touched during smoke:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/batches/ 2>&1 || true
```

Expected: `An error occurred (NoSuchKey)` or empty listing. No `part-*.parquet` objects under the canonical feature `batches/` prefix.

## Acceptance criteria

- Each completed batch writes at most one new immutable object under `batches/`.
- Every row carries the full Q44 column set.
- `manifest.json` contains SHA-256 digests only and matches uploaded bytes.
- `progress.jsonl` appends one line per durable batch write.
- Batch objects carry `intermediate-artifact=true`; final and audit files do not.
- Resume continues batch numbering and input order without rewriting prior batches.
- `final.parquet` is written once with exactly 200,000 unique ids across 100 batch objects when the feature completes.
- `active_openai_batch.json` persists and clears per Step 4 contract.
- Logical append and conditional replace work for `progress.jsonl`, `errors.jsonl`, and `manifest.json`.
- Campaign mode automatically resumes on restart with the same `run_id`.
- Live batch-writer smoke writes only under `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/` and never under the pinned campaign feature `batches/` prefix.
- Disposable S3 prefix is empty after `aws s3 rm ... --recursive` before merge.
- Temporary smoke helper and Git evidence are committed for review and removed before merge.
- No automated tests were added or run.

## Failure conditions

- Overwriting an existing `part-NNNNN.parquet` key.
- Missing Q44 provenance columns on any written row.
- Using non-SHA-256 manifest hashes or accepting ETag as a content hash.
- Applying `intermediate-artifact=true` to `final.parquet`, `manifest.json`, or `progress.jsonl`.
- Multiple active OpenAI Batch jobs for one feature run.
- Using `shards/`, `campaigns/`, `final/` subdirectory, or per-run timestamp subfolders.
- Step 5 live smoke writes any object under the pinned campaign feature `batches/` prefix.
- Disposable prefix `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/` is not empty before merge.
- Any edit under `/workspace/tests/**`.
- Any code path that launches Cursor agents or other autonomous agent runners.

## PR artifact and commit rules

- Keep this PR focused on batch writing and consolidation; do not fold Step 6 smoke tooling or Step 7 watcher into it.
- Commit temporary `smoke_write_s3_batch.py` and `BATCH_SMOKE_EVIDENCE.md` during review.
- Before merge: run `aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/ --recursive`, verify the disposable prefix is empty, then delete the temporary helper and Git evidence file.
- PR title: `Write resumable 2,000-row Parquet feature batches to S3`
- PR body must list the disposable smoke prefix, the batch SHA-256 observed, confirmation that the canonical campaign feature `batches/` prefix was not touched, and confirmation that the disposable prefix was emptied before merge.
