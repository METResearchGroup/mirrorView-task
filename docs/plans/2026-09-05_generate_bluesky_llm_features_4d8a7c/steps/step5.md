# Step 5: Write resumable 2,000-row Parquet feature shards

## Goal

Write immutable S3-backed feature artifacts for the Bluesky LLM campaign: 2,000-row Parquet batch shards, one consolidated `final.parquet`, a SHA-256 `manifest.json`, append-only `progress.jsonl`, and error records. Preserve deterministic record order across resume and consolidation. Keep one blocking OpenAI Batch job per feature and reuse the hardened resume behavior from Step 4.

## Real dependencies

- Step 4 merged: persisted `input_file_id` and `batch_id`, partial success retention, four-attempt transient retry, exact input id completeness.
- Steps 1 through 3 merged: S3 production backend under `s3://mirrorview-experimental-artifacts/data_platform/data/`.
- Pinned campaign constants from the parent plan.

## Main caller and one implementation slice

**Main caller after this PR merges:**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --features is_news_or_opinion \
  --batch-size 2000 \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1
```

**One implementation slice for this PR:** add an S3 shard writer that, after each completed OpenAI Batch of up to 2000 records, writes one immutable Parquet object under `batches/`, appends one `progress.jsonl` line, updates `manifest.json` with SHA-256 only, and never mutates an existing shard object.

**Out of scope for this PR:** ten-post smoke cost gate, parent-issue cost aggregation, deliberate interrupt smoke beyond one shard write/resume proof, watcher GitHub comments, Step 16 lifecycle rule infrastructure, and joining seven features into one wide artifact.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Parent plan Step 5 scope |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | Batch completion hook point after Step 4 |
| `/workspace/data_platform/generate_features/engines/base.py` | Batch loop and write callback |
| `/workspace/data_platform/generate_features/generate_features.py` | Orchestrator and completion checks |
| `/workspace/data_platform/generate_features/metadata.py` | Existing local metadata; do not break resume |
| `/workspace/data_platform/generate_features/models.py` | Label row models and run config |
| `/workspace/data_platform/generate_features/registry.py` | Seven LLM features |
| `/workspace/data_platform/generate_features/platform_cli.py` | CLI flags for campaign id and batch size |
| `/workspace/data_platform/utils/storage.py` | Post-Step-3 storage abstraction |
| `/workspace/lib/aws/s3.py` | Low-level S3 upload and list helpers |
| `/workspace/data_platform/utils/platform_specific_columns.py` | `source_record_id` column contract |
| `/workspace/data_platform/generate_features/is_news_or_opinion/generate_feature.py` | Example output schema |

## Files allowed to change

- `/workspace/data_platform/generate_features/s3_feature_campaign.py` (new; campaign paths, manifest, progress, shard write)
- `/workspace/data_platform/generate_features/s3_feature_shards.py` (new; immutable shard writer and final consolidation)
- `/workspace/data_platform/generate_features/generate_features.py` (wire shard writer after each durable batch)
- `/workspace/data_platform/generate_features/platform_cli.py` (add `--campaign-id`; enforce `--batch-size 2000` for campaign runs)
- `/workspace/data_platform/generate_features/models.py` (campaign config fields if needed)
- `/workspace/data_platform/generate_features/smoke_write_s3_shard.py` (new temporary smoke helper)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step5.md` (this file only if correcting the spec during implementation)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step6.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step7.md`
- `/workspace/tests/**`
- Feature prompt modules under `/workspace/data_platform/generate_features/is_*`, `political_stance`, and `llm_toxicity_tiered`
- `/workspace/webapp/**`
- `/workspace/experiments/**`
- Any repository code that launches Cursor agents or other autonomous agent runners

## Locked contracts

### Campaign constants

- Campaign id: `bluesky_2026_09_03_235130_llm_features_v1`
- Dataset id: `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73`
- Preprocessed run: `2026_09_03-23:51:30`
- Bucket: `mirrorview-experimental-artifacts`
- Batch size: `2000`
- Total expected rows per feature: `200000`

### S3 layout

For each feature `{feature}` in the seven-feature campaign:

```text
s3://mirrorview-experimental-artifacts/data_platform/data/features/bluesky_2026_09_03_235130_llm_features_v1/{feature}/
  batches/shard_00000.parquet
  batches/shard_00001.parquet
  ...
  final.parquet
  manifest.json
  progress.jsonl
  errors.jsonl
```

Shard object keys are immutable. Never overwrite an existing shard key. The next shard index is derived from existing keys and progress state, not from in-memory counters alone.

### Per-row provenance from Q44

Every label row written to a shard or to `final.parquet` must include these columns in addition to the feature-specific label fields:

| Column | Value |
|--------|-------|
| `campaign_id` | `bluesky_2026_09_03_235130_llm_features_v1` |
| `dataset_id` | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| `source_preprocessed_run` | `2026_09_03-23:51:30` |
| `input_content_hash` | SHA-256 hex digest of the pinned 200,000-post input set |
| `model_id` | `gpt-5.4-nano` unless the feature spec overrides it |
| `prompt_hash` | SHA-256 hex digest of the feature system prompt |
| `label_timestamp` | UTC timestamp from `lib.timestamp_utils.get_current_timestamp` |
| `source_record_id` | pinned input id |
| `openai_batch_id` | provider batch id for the batch that produced the row |
| `batch_shard_index` | zero-based durable shard index |
| `batch_row_index` | zero-based row position inside the shard |

### Shared immutable metadata in `manifest.json`

`manifest.json` holds campaign-level immutable metadata only. It must include:

- `campaign_id`, `dataset_id`, `source_preprocessed_run`, `input_content_hash`
- `feature`, `model_id`, `prompt_hash`
- `batch_size`, `expected_row_count`
- `created_at`
- `shards`: ordered list of `{shard_index, key, row_count, sha256}`
- `final_parquet`: `{key, row_count, sha256}` once built

Do not store mutable counters that belong in `progress.jsonl`.

### SHA-256 manifests only

Hash fields in `manifest.json` are SHA-256 hex digests of file bytes. Do not use MD5, ETag alone, or size-only checks as acceptance gates.

### Lifecycle tag on batch shards only

When uploading a shard under `batches/`, set S3 object tag `intermediate-artifact=true`. Do not set that tag on `final.parquet`, `manifest.json`, `progress.jsonl`, or `errors.jsonl`.

### Deterministic order

Input ids are processed in stable ascending `source_record_id` order from the pinned preprocessed run. Shard row order follows that global order within each 2000-row chunk. Resume must continue from the next unseen id, not reorder prior shards.

### Final consolidation

When all 200,000 ids are present across shards, build `final.parquet` once by concatenating shards in `batch_shard_index` order, verify row count and uniqueness, write `final.parquet` with no `intermediate-artifact` tag, and record its SHA-256 in `manifest.json`.

### Blocking engine and one active batch

Reuse Step 4 behavior. Shard writing happens only after a provider batch completes and rows pass schema validation.

## Ordered implementation work

1. Add campaign path helpers in `s3_feature_campaign.py` for prefix construction and input hash computation over the pinned preprocessed run.
2. Implement immutable shard upload with SHA-256 digest, manifest shard list update, and `progress.jsonl` append in `s3_feature_shards.py`.
3. Attach provenance columns from Q44 on every row before Parquet write.
4. Wire the shard writer into the batch completion path in `generate_features.py`; refuse campaign runs unless `--batch-size 2000`.
5. Implement `final.parquet` consolidation and manifest final block when row completeness check passes.
6. Add `errors.jsonl` append for exhausted per-record failures without mutating successful shards.
7. Add temporary smoke helper that writes one real shard for `is_news_or_opinion`, verifies S3 keys and hashes, then exits.
8. Run live smoke commands. Commit temporary smoke evidence. Delete helper and evidence before merge.

## Exact live smoke/basic check commands with expected output

### Offline path and hash helper check

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
from data_platform.generate_features.s3_feature_campaign import campaign_prefix, input_content_hash
p = campaign_prefix('bluesky_2026_09_03_235130_llm_features_v1', 'is_news_or_opinion')
assert p.endswith('features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/')
h = input_content_hash('bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73', '2026_09_03-23:51:30')
assert len(h) == 64
print('campaign_prefix OK')
print('input_content_hash OK')
"
```

Expected stdout:

```text
campaign_prefix OK
input_content_hash OK
```

### Live one-shard write check (requires `OPENAI_API_KEY` and AWS credentials)

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/smoke_write_s3_shard.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_news_or_opinion \
  --row-count 10
```

Expected stdout:

```text
shard_key=s3://mirrorview-experimental-artifacts/data_platform/data/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/batches/shard_00000.parquet
shard_sha256=<64-char-hex>
manifest_updated=true
progress_appended=true
intermediate_tag=true
```

Expected S3 objects after the command:

- `.../batches/shard_00000.parquet` exists and is tagged `intermediate-artifact=true`
- `.../manifest.json` lists shard 0 with matching SHA-256
- `.../progress.jsonl` has one new line with `durable_rows=10`

### Resume-without-rewrite check

Run the same command a second time without deleting S3 objects.

Expected stdout:

```text
shard_rewrite_refused=true
next_shard_index=1
```

Expected behavior: existing `shard_00000.parquet` bytes and hash remain unchanged.

## Acceptance criteria

- Each completed batch writes at most one new immutable shard object under `batches/`.
- Every row in shards and `final.parquet` carries the full Q44 provenance column set.
- `manifest.json` contains SHA-256 digests only and matches uploaded bytes.
- `progress.jsonl` appends one line per durable shard write.
- Batch shards carry `intermediate-artifact=true`; final and audit files do not.
- Resume continues shard numbering and input order without rewriting prior shards.
- `final.parquet` is written once with exactly 200,000 unique ids when the feature completes.
- Temporary smoke helper and evidence are committed for review and removed before merge.
- No automated tests were added or run.

## Failure conditions

- Overwriting an existing shard key.
- Missing Q44 provenance columns on any written row.
- Using non-SHA-256 manifest hashes.
- Applying `intermediate-artifact=true` to `final.parquet`, `manifest.json`, or `progress.jsonl`.
- Multiple active OpenAI Batch jobs for one feature run.
- Any edit under `/workspace/tests/**`.
- Any code path that launches Cursor agents or other autonomous agent runners.

## PR artifact/commit rules

- Branch name: `cursor/s3-parquet-feature-shards-86b0`
- Keep this PR focused on shard writing and consolidation; do not fold Step 6 smoke cost gate or Step 7 watcher comments into it.
- Commit temporary `smoke_write_s3_shard.py` and `SHARD_SMOKE_EVIDENCE.md` during review.
- Before merge, delete the temporary helper and evidence file.
- PR title: `Write resumable 2,000-row Parquet feature shards to S3`
- PR body must list the exact S3 prefix written during smoke and the shard SHA-256 observed.
