# Step 1: Add campaign mode with immutable S3 batch objects, manifest, progress log, and S3 provider state

## Goal

Give the Bluesky feature CLI a campaign mode that labels the pinned 200,000-post run in fixed 2,000-post chunks, writes each completed chunk as one immutable Parquet object in S3 with the campaign row columns, records SHA-256 digests in `manifest.json`, appends to `progress.jsonl` and `errors.jsonl`, keeps the in-flight OpenAI Batch state in S3, and resumes from that S3 state without rewriting any batch object.

## Source of truth

The epic step spec is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step5.md`, and the shared layout is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md`. Every locked value below is copied from those two files. If this file disagrees with them, they win and this file is wrong.

## Main caller

`data_platform/generate_features/platform_cli.py` `build_feature_cli_main`, which `generate_bluesky_features.py` turns into the Typer command. In campaign mode the command calls `generate_platform_campaign_feature`, which calls `generate_features.generate_campaign_feature` for the one requested feature.

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

That command labels 200,000 posts and is not run in this PR. The live checks in this file use the temporary smoke helper with ten rows and fake provider ids under a disposable prefix.

Happy path through the caller for one feature: validate the flags, load the pinned preprocessed run through `StorageManager`, sort by `source_record_id`, load or create `manifest.json`, read the ids already in batch objects and in `smoke/output.parquet`, and then for each 2,000-id chunk without a batch object: seed the local engine state from S3, call `OpenAIBatchEngine.label_chunk`, attach identity and audit columns to the rows that arrive, write one batch object, update the manifest, append a progress line, append error lines for exhausted ids, and delete the S3 state. When every id has a row or a line in `errors.jsonl`, write `final.parquet` once with the labeled rows. When the manifest already records a final file, print one line and stop before labeling.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step5.md` | Locked contracts, smoke commands, allowed and forbidden files |
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | S3 layout, campaign row schema, manifest fields, append semantics |
| `data_platform/generate_features/engines/openai_engine.py` | `OpenAIBatchEngine.__init__` takes `sleep_fn`; `label_chunk` writes local state before polling and calls `write_rows` per provider job; `create_openai_client`, `DEFAULT_OPENAI_BATCH_ENGINE_CONFIG` |
| `data_platform/generate_features/openai_batch_state.py` | `active_batch_state_path`, `load_active_batch_state`, `write_active_batch_state` used by the S3 mirror |
| `data_platform/generate_features/engines/base.py` | `RecordLabelFailure` shape returned by `label_chunk` |
| `data_platform/generate_features/generate_features.py` | Legacy orchestrator that stays unchanged except for the new campaign entry point |
| `data_platform/generate_features/platform_cli.py` | Existing flags, `_require_single_feature_run_name`, `load_preprocessed_records` row validation |
| `data_platform/generate_features/metadata.py` | `prompt_hash` and `model_id_for_spec` for the manifest |
| `data_platform/generate_features/registry.py` | The seven OpenAI features and their Pydantic models |
| `data_platform/generate_features/is_news_or_opinion/generate_feature.py` | `IsNewsOrOpinionModel` fields `source_record_id`, `label_timestamp`, `category` |
| `data_platform/utils/storage.py` | `DATA_ROOT`, `StorageManager.load_records`, `_parquet_bytes` |
| `data_platform/utils/object_store.py` | `DEFAULT_S3_BUCKET`, `DEFAULT_S3_REGION`, `S3_BUCKET_ENV_VAR`, `S3_KEY_PREFIX`, `sha256_hex`, `PRECONDITION_FAILED_ERROR_CODES` |
| `lib/aws/s3.py` | `NOT_FOUND_ERROR_CODES` |

## Files allowed to change

- `data_platform/generate_features/s3_feature_campaign.py` (new)
- `data_platform/generate_features/s3_feature_batches.py` (new)
- `data_platform/generate_features/generate_features.py` (campaign entry point only)
- `data_platform/generate_features/generate_bluesky_features.py` (pass through the two flags)
- `data_platform/generate_features/platform_cli.py` (two flags, campaign guards, pinned run loader, campaign runner)
- `data_platform/generate_features/models.py` (campaign config and row metadata model)
- `data_platform/generate_features/smoke_write_s3_batch.py` (new, temporary, deleted before merge)
- `data_platform/generate_features/BATCH_SMOKE_EVIDENCE.md` (new, temporary, deleted before merge)

`CHANGELOG.md` is edited only in a separate commit after implementation.

## Files forbidden to change

- `tests/**`
- `data_platform/generate_features/engines/**`, `openai_batch_state.py`, `metadata.py`, `registry.py`, `deadletter.py`, `llm_retry.py`
- Feature prompt modules under `data_platform/generate_features/is_*`, `political_stance`, `llm_toxicity_tiered`
- `data_platform/utils/**`, `lib/**`, `webapp/**`, `experiments/**`
- Any file under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/` or any earlier child plan folder
- Any git history rewrite

Stage files by explicit path only. Never run `git add -A` or `git add .`. `git status` lists 24 pulled dump parquet files as modified even though `git diff` is empty; never stage them.

## S3 rules for this step

- The only S3 writes allowed are under `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/`.
- The only S3 deletes allowed are of objects under that same prefix.
- Never write `batches/part-*.parquet`, `final.parquet`, `manifest.json`, `progress.jsonl`, `errors.jsonl`, or `active_openai_batch.json` under any real campaign feature prefix in this step.
- Never touch the 53 objects that Step 1 of the epic copied.

## Locked values

| Item | Value |
|------|-------|
| Bucket | `mirrorview-experimental-artifacts`, region `us-east-2` |
| Feature prefix | `data_platform/data/{platform}/{dataset_id}/features/{campaign_id}/{feature}/` |
| Canonical smoke example | `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/` |
| Run id | `{campaign_id}:{feature}`, e.g. `bluesky_2026_09_03_235130_llm_features_v1:is_news_or_opinion` |
| Batch object key | `{feature prefix}batches/part-{index:05d}.parquet`, zero based, immutable, uploaded with `If-None-Match: *` |
| Batch object tag | `intermediate-artifact=true` on `batches/` objects only |
| Untagged objects | `active_openai_batch.json`, `final.parquet`, `manifest.json`, `progress.jsonl`, `errors.jsonl` |
| Chunking | Sort input rows by ascending `source_record_id`. Chunk `k` is rows `[2000k, 2000k + 2000)`. Chunk `k` writes `part-{k:05d}`. Row order inside a batch object follows that global order |
| Campaign row columns | Exactly `source_record_id`, `run_id`, `batch_id`, `request_id`, `attempt_count`, `label_timestamp`, and the feature's label field, e.g. `category` |
| `batch_id` | The OpenAI Batch id of the provider job that produced the row, read from the engine's local state file when `write_rows` runs |
| `request_id` | The request's `custom_id` inside that provider job, `task-{index:05d}` where `index` is the row id's position in the state's `pending_source_record_ids` |
| `attempt_count` | The `attempt_count` of that provider job, an integer 1 through 4 |
| `label_timestamp` | Kept from the engine row, which uses `lib.timestamp_utils.get_current_timestamp` |
| Validation | `spec.model` on `source_record_id`, `label_timestamp`, and the label field. `LabelRowMetadataModel` on the six identity and audit columns. A row with an extra or missing column fails |
| Manifest fields | `campaign_id`, `dataset_id`, `preprocessed_run`, `feature`, `model_id`, `prompt_hash`, `batch_size`, `expected_row_count`, `run_id`, `created_at`, `batches`, `final_parquet` |
| Manifest batch entry | `{part_index, key, row_count, sha256, provider_batch_ids}` where `key` is the bucket key and `sha256` is the lowercase hex digest of the object bytes |
| Manifest final block | `{key, row_count, failed_row_count, sha256}` once `final.parquet` exists, `null` before. `row_count + failed_row_count == expected_row_count` |
| Manifest write | Create with `If-None-Match: *`. Replace with `If-Match: {prior ETag}`. On a 412 or 409 reload and retry up to 5 times. ETag is never used as a hash |
| `progress.jsonl` line | `{"ts", "event": "batch", "run_id", "part_index", "key", "row_count", "sha256", "provider_batch_ids", "rows_total", "batches_total"}`. The final file adds one line with `"event": "final"`, `key`, `row_count`, `failed_row_count`, `sha256` |
| `errors.jsonl` line | `{"ts", "run_id", "part_index", "source_record_id", "error", "attempts"}` per exhausted record |
| Logical append | Read current bytes and ETag (empty and none when missing), append newline terminated JSON, replace with `If-Match` (or `If-None-Match: *` when missing), retry from the latest bytes on conflict |
| `active_openai_batch.json` in S3 | The engine's local state file bytes with `campaign_id` set to the campaign id. Written by the mirror whenever the engine calls `sleep_fn` and whenever `write_rows` runs, using `If-Match` when the object exists. Seeded back to the local state path before each chunk when the local file is missing. Deleted only after the batch object and manifest entry are written |
| Smoke rows | When `{feature}/smoke/output.parquet` exists, its ids are not sent to the provider and its rows are merged into the batch object of the chunk that holds those ids. That is how `part-00000` holds ten smoke rows plus 1,990 new rows after Step 6 |
| Final gate | Every input id is in exactly one batch object or in `errors.jsonl` (read across all runs), with no duplicate id and no id outside the input. Then `final.parquet` is written once with `If-None-Match: *` and no tag, in part order, with the campaign row columns and only the labeled rows. User override: the epic's `step5.md` asks for exactly one valid row per pinned id; the user chose during review of PR #201 to write `final.parquet` anyway and leave permanently failed ids out, with `errors.jsonl` as their record |
| Final guard | When the manifest already records `final_parquet`, the campaign command prints one line and returns before creating the engine. A chunk whose rows all failed permanently has no batch object and is not retried after that point |
| Orphan batch object | A batch object that exists but has no manifest entry is adopted on resume: its bytes are read, hashed, and recorded, and no provider job runs for that chunk |
| Campaign guards | `--campaign-id` and `--preprocessed-run` must be passed together, `--checkpoint` is rejected with them, `--batch-size` must be 2000, and `--features` must name exactly one feature whose `engine_type` is `openai` |
| Storage | Campaign mode always writes S3 with boto3. `DATA_PLATFORM_S3_BUCKET` overrides the bucket name. `DATA_PLATFORM_STORAGE_BACKEND` is not consulted |
| Local engine state dir | `data_platform/data/{platform}/{dataset_id}/features/{campaign_id}/{feature}/`, holding only `{feature}.active_openai_batch.json` while a job is in flight |
| Legacy mode | Unchanged when the two flags are absent |

## Contracts

`data_platform/generate_features/models.py`:

- `@dataclass(frozen=True) class CampaignRunConfig: campaign_id: str; dataset_id: str; preprocessed_run: str; platform: str; batch_size: int`
- `class LabelRowMetadataModel(BaseModel)`: `source_record_id: str`, `run_id: str`, `batch_id: str`, `request_id: str`, `attempt_count: int` with `ge=1, le=4`, `label_timestamp: str`. Every string field has `min_length=1`. `extra="forbid"`.

`data_platform/generate_features/s3_feature_campaign.py`:

- Constants `DEFAULT_CAMPAIGN_PLATFORM = "bluesky"`, `DEFAULT_CAMPAIGN_DATASET_ID = "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"`, `INTERMEDIATE_ARTIFACT_TAG = {"intermediate-artifact": "true"}`, the five file names, `BATCHES_DIRNAME = "batches"`, `SMOKE_OUTPUT_KEY_SUFFIX = "smoke/output.parquet"`, `MAX_CONDITIONAL_WRITE_ATTEMPTS = 5`.
- `run_id_for_feature(campaign_id: str, feature: str) -> str`
- `feature_prefix(campaign_id: str, feature: str, *, platform: str = DEFAULT_CAMPAIGN_PLATFORM, dataset_id: str = DEFAULT_CAMPAIGN_DATASET_ID) -> str` returns the bucket key ending in `/`.
- `s3_uri(bucket: str, key: str) -> str` and `parse_s3_uri(uri: str) -> tuple[str, str]`.
- `@dataclass(frozen=True) class FeaturePaths: bucket: str; prefix: str` with `classmethod for_campaign(campaign_id, feature, *, bucket=None, platform=..., dataset_id=...)` (bucket `None` reads `DATA_PLATFORM_S3_BUCKET` or the default), `classmethod from_root_uri(root_uri: str, feature: str)`, properties `active_state_key`, `manifest_key`, `progress_key`, `errors_key`, `final_key`, `smoke_output_key`, `batches_prefix`, method `batch_key(part_index: int) -> str`, method `uri(key: str) -> str`.
- `@dataclass(frozen=True) class StoredObject: body: bytes; etag: str`
- `@dataclass(frozen=True) class WriteResult: sha256: str; etag: str`
- `class ConditionalWriteConflict(RuntimeError)`
- `class CampaignObjectStore` with `__init__(self, bucket: str, *, region_name: str = DEFAULT_S3_REGION)`, `get(key) -> StoredObject | None`, `put_new(key, body, *, tags: dict[str, str] | None = None) -> WriteResult` raising `FileExistsError` on 412, `replace(key, body, *, etag: str | None) -> WriteResult` raising `ConditionalWriteConflict` on 412 or 409, `delete(key) -> None`, `list_keys(prefix) -> list[str]`, `get_tags(key) -> dict[str, str]`, `append_jsonl(key, records: list[dict]) -> None`.
- `new_manifest(*, campaign: CampaignRunConfig, spec: FeatureSpec, expected_row_count: int) -> dict`
- `load_manifest(store, paths) -> tuple[dict | None, str | None]`
- `save_manifest(store, paths, manifest, etag: str | None) -> str` returns the new ETag.
- `load_active_state(store, paths) -> tuple[dict | None, str | None]`, `save_active_state(store, paths, state, etag) -> str`, `delete_active_state(store, paths) -> None`
- `append_progress(store, paths, record: dict) -> None`, `append_errors(store, paths, records: list[dict]) -> None`
- `class ActiveStateMirror` with `__init__(self, store, paths, *, run_dir: Path, feature_name: str, campaign_id: str)`, `seed_local() -> None`, `sync() -> None`, `sleep(seconds: float) -> None`.

`data_platform/generate_features/s3_feature_batches.py`:

- `ROW_METADATA_COLUMNS = ("source_record_id", "run_id", "batch_id", "request_id", "attempt_count", "label_timestamp")`
- `label_fields(spec) -> list[str]` and `campaign_row_columns(spec) -> list[str]`
- `attach_row_metadata(rows, *, run_id, batch_id, request_ids: Mapping[str, str], attempt_count) -> list[dict]`
- `validate_campaign_rows(rows, spec, *, run_id) -> None` raises `ValueError`.
- `rows_to_parquet_bytes(rows, columns) -> bytes` and `parquet_rows(body) -> pd.DataFrame`
- `@dataclass(frozen=True) class BatchWriteResult: key: str; sha256: str; row_count: int; manifest_etag: str`
- `write_batch(store, paths, manifest, manifest_etag, *, part_index, rows, spec, run_id) -> BatchWriteResult` raises `FileExistsError` when the part is in the manifest or the key exists. Appends the manifest entry in place.
- `adopt_unrecorded_batch(store, paths, manifest, manifest_etag, *, part_index, run_id) -> BatchWriteResult | None`
- `read_batches(store, manifest) -> list[pd.DataFrame]` verifies each SHA-256.
- `labeled_ids(store, manifest) -> set[str]`
- `consolidate_final(store, paths, manifest, manifest_etag, *, expected_ids, spec, run_id) -> str | None` returns the new manifest ETag when it writes the final file, else `None`.

`data_platform/generate_features/generate_features.py`:

- `generate_campaign_feature(records: pd.DataFrame, spec: FeatureSpec, campaign: CampaignRunConfig, run_config: FeatureRunConfig, *, paths: FeaturePaths | None = None) -> FeaturePaths`

`data_platform/generate_features/platform_cli.py`:

- `CAMPAIGN_BATCH_SIZE = 2000`
- `load_pinned_preprocessed_records(spec, dataset_id, preprocessed_run) -> pd.DataFrame`
- `generate_platform_campaign_feature(spec, dataset_id, *, campaign_id, preprocessed_run, feature_subset, batch_size) -> str` returns the feature prefix URI.
- `build_feature_cli_main` gains `--campaign-id` and `--preprocessed-run`.

`data_platform/generate_features/generate_bluesky_features.py`:

- `generate_bluesky_features(..., campaign_id: str | None = None, preprocessed_run: str | None = None)` returns `dict[str, Path | str]`.

## Scenarios (given, when, then)

No pytest is added. These scenarios are the behavior the live smoke, the offline check, and the ad hoc disposable-prefix checks prove.

1. Given the campaign id and feature from the contract, when `feature_prefix` and `run_id_for_feature` run, then the prefix ends with `features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/` and the run id is `bluesky_2026_09_03_235130_llm_features_v1:is_news_or_opinion`.
2. Given an empty disposable prefix and ten rows with identity and audit columns, when `write_batch(part_index=0)` runs, then `batches/part-00000.parquet` exists with tag `intermediate-artifact=true`, its SHA-256 equals the manifest entry, and `progress.jsonl` has one line with that SHA-256.
3. Given part 0 already in the manifest, when `write_batch(part_index=0)` runs again, then it raises `FileExistsError` and no object changes.
4. Given a manifest whose ETag is stale, when `save_manifest` runs, then it raises `ConditionalWriteConflict`.
5. Given `progress.jsonl` with one line, when `append_jsonl` runs with one record, then the object has two lines and the first is unchanged.
6. Given a state dict, when `save_active_state`, `load_active_state`, and `delete_active_state` run in order, then the load returns the same dict and the delete leaves no object.
7. Given every input id is in the manifest batches, when `consolidate_final` runs, then `final.parquet` exists untagged, has the campaign row columns, and the manifest `final_parquet` block holds its SHA-256 with `failed_row_count` 0. A second call returns `None` and writes nothing.
7a. Given three of five ids in a batch object and the other two in `errors.jsonl`, when `consolidate_final` runs with the ids from `read_failed_ids`, then `final.parquet` holds three rows, the manifest and the `final` progress line hold `row_count` 3 and `failed_row_count` 2.
7b. Given an id that is neither in a batch object nor in `errors.jsonl`, when `consolidate_final` runs, then it returns `None` and writes nothing.
7c. Given a manifest that already records `final_parquet`, when `generate_campaign_feature` runs, then it prints one line and returns without creating an OpenAI client or engine.
8. Given a row missing `request_id`, when `validate_campaign_rows` runs, then it raises `ValueError`.
9. Given `--campaign-id` without `--preprocessed-run`, or `--batch-size 64`, or two `--features` values, when the CLI runs, then it exits with a `ValueError` message and makes no S3 call.

## Ordered implementation work

1. Scaffold `s3_feature_campaign.py`, `s3_feature_batches.py`, the campaign entry point stub in `generate_features.py`, the two flags and campaign stub in `platform_cli.py`, the pass-through in `generate_bluesky_features.py`, the new types in `models.py`, and a Typer skeleton for `smoke_write_s3_batch.py`. Commit.
2. Fill in the signatures above with stub bodies. Commit.
3. Record the scenarios above in this file and the smoke helper's expected output lines. Commit.
4. Implement `FeaturePaths`, `run_id_for_feature`, `feature_prefix`, and `CampaignObjectStore`. Run the offline path check. Commit.
5. Implement the manifest, active state, progress, and errors helpers and `ActiveStateMirror`. Commit.
6. Implement row metadata, validation, Parquet bytes, `write_batch`, and `adopt_unrecorded_batch`. Commit.
7. Implement `read_batches`, `labeled_ids`, and `consolidate_final`. Commit.
8. Implement `generate_campaign_feature`. Commit.
9. Implement the CLI guards, pinned run loader, and campaign runner, and the Bluesky pass-through. Commit.
10. Implement `smoke_write_s3_batch.py`. Run the live smoke twice. Commit the helper and `BATCH_SMOKE_EVIDENCE.md`.
11. Delete every object under the disposable prefix with boto3, list it to show it is empty, and list the primary feature `batches/` prefix to show it is empty. Record both in the evidence file. Commit.
12. Run `uv run pytest -q`. Expect 631 passed.
13. Delete the two temporary files in a final commit before merge.

## Exact commands with expected output

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

### Live one-batch write check (AWS credentials; no OpenAI call)

The helper builds ten rows from the first ten ids of the pinned preprocessed run with fake provider ids, so it makes no OpenAI call.

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

The `aws` CLI is not installed in this environment, so the cleanup uses boto3 with the same effect.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
import boto3
s3 = boto3.client('s3', region_name='us-east-2')
bucket = 'mirrorview-experimental-artifacts'
prefix = 'data_platform/data/_smoke/step5_batch_writer/'
keys = [o['Key'] for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix=prefix) for o in page.get('Contents', [])]
for key in keys:
    print('delete:', key)
if keys:
    s3.delete_objects(Bucket=bucket, Delete={'Objects': [{'Key': k} for k in keys]})
left = s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get('KeyCount', 0)
print('remaining_under_disposable_prefix=', left)
canonical = 'data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/batches/'
print('canonical_batches_key_count=', s3.list_objects_v2(Bucket=bucket, Prefix=canonical).get('KeyCount', 0))
"
```

Expected: one `delete:` line per smoke object, then `remaining_under_disposable_prefix= 0` and `canonical_batches_key_count= 0`.

### Existing suite

```bash
cd /workspace
uv run pytest -q
```

Expected: `631 passed`.

## Must pass

- The offline path check prints `feature_prefix OK` and `run_id OK`.
- The first live smoke prints the seven expected lines with a 64 character hex digest.
- The second live smoke prints `batch_rewrite_refused=true`, `next_part_index=1`, and `canonical_batches_prefix_touched=false`.
- The cleanup prints `remaining_under_disposable_prefix= 0` and `canonical_batches_key_count= 0`.
- The offline fake-store checks for scenarios 7, 7a, 7b, 7c, and the duplicate-id case all print `ok`.
- `uv run pytest -q` reports 631 passed with no test file changes.

## Must fail

- Any write to an existing `part-NNNNN.parquet` key.
- Any row without the full campaign row column set.
- Any manifest hash that is not a SHA-256 hex digest, or any use of ETag as a content hash.
- The `intermediate-artifact=true` tag on `final.parquet`, `manifest.json`, `progress.jsonl`, `errors.jsonl`, or `active_openai_batch.json`.
- A second provider job for ids covered by a `polling` or `writing` state.
- Any smoke write under the primary campaign feature prefix.
