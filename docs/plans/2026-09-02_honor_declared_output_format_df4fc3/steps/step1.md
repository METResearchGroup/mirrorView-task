# Step 1: Point the Twitter writer at the storage filename

## Goal

Make `sync_twitter.sync_records` write raw tweets using `TwitterStorageManager.records_filename`, after the dataset manifest exists, matching `sync_bluesky.sync_records`.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_twitter.py` `sync_records`, reached from `main` through `run_sync_cli`.

**Task:** create the dataset manifest, construct storage so it reads `dataset.json` format, then pass `storage.records_filename` into `run_sync_tasks`.

**Out of scope:** Reddit writers (step 2). YAML key changes. Twitter record type validation behavior. Bluesky `author_filter`. Repo relative config path helper. Teaching `RECORD_TYPE_FILENAMES` about `twitter.tweet` or about format. Changing `StorageManager` restem logic. Sibling issues. `CHANGELOG.md` during implementation.

## Decision (locked)

Match Bluesky. In `/workspace/data_platform/ingestion/sync_bluesky.py`, `sync_records` calls `ensure_dataset_manifest` with a temporary `BlueskyStorageManager`, then constructs the run storage, then sets `filename = storage.records_filename` and passes `filename=` into `run_sync_tasks`.

`StorageManager.__init__` in `/workspace/data_platform/utils/storage.py` already sets `self.records_filename = f"{stem}.{self.format.value}"` from `load_dataset_format`. Do not add a second filename helper. Do not call `filename_for` from Twitter ingest. Bluesky uses `storage.records_filename`.

Twitter currently constructs storage, then calls `ensure_dataset_manifest`, then passes `csv_filename=POSTS_CSV` where `POSTS_CSV = "posts.csv"`. That ignores format. Copy the Bluesky order so a new parquet dataset is not still seen as csv.

Rename the `run_sync_tasks` argument `csv_filename` to `filename` so it matches Bluesky. Remove `POSTS_CSV` once nothing uses it. `TwitterStorageManager` already defaults `records_filename="posts.csv"`, and restem turns that into `posts.csv` or `posts.parquet`.

Do not change `TwitterStorageManager.load_records` in this step. Writer tests assert the file path. Parent `load_seen_ids_from_disk` already reads parquet.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-02_honor_declared_output_format_df4fc3/plan.md` | Parent plan |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Pattern: `ensure_dataset_manifest` then `storage = BlueskyStorageManager(...)` then `filename = storage.records_filename` |
| `/workspace/data_platform/ingestion/sync_twitter.py` | Current `POSTS_CSV` and `csv_filename` |
| `/workspace/data_platform/utils/storage.py` | `StorageManager.__init__` restem. `TwitterStorageManager` default stem `posts.csv` |
| `/workspace/data_platform/utils/dataset.py` | `ValidDataFormats`, `write_dataset_manifest`, `load_dataset_format` |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | `ensure_dataset_manifest` writes `format` from YAML `output_format` defaulting to csv |
| `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Existing Twitter tests pass `csv_filename=sync_twitter.POSTS_CSV` |
| `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Existing Bluesky tests pass `filename=storage.records_filename` |
| `/workspace/tests/data_platform/utils/test_storage.py` | Add Twitter parquet filename coverage here |
| `/workspace/tests/data_platform/conftest.py` | `data_root` fixture |
| `/workspace/tests/data_platform/constants.py` | `VALID_TWITTER_DATASET_ID`, `TEST_INGEST_CONFIG_PATH` |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/utils/test_storage.py`

Plan files under `/workspace/docs/plans/2026-09-02_honor_declared_output_format_df4fc3/` are already on this branch. Do not rewrite them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/utils/dataset.py`
- `/workspace/data_platform/utils/storage.py` unless a writer cannot compile without a tiny signature fix, which this step does not need
- `/workspace/data_platform/ingestion/configs/**`
- `/workspace/CHANGELOG.md` during implementation
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

In `/workspace/data_platform/ingestion/sync_twitter.py` `sync_records`, match Bluesky order:

```text
ensure_dataset_manifest(
    TwitterStorageManager(StorageStage.RAW, dataset_id),
    "twitter",
    dataset_id,
    config,
    config_path,
)
storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
filename = storage.records_filename
```

`run_sync_tasks` keyword argument:

```text
filename: str
```

Call site:

```text
run_sync_tasks(..., filename=filename)
```

Behavior:

- Default csv dataset: `storage.records_filename` is `posts.csv`. The write loop writes `posts.csv`.
- Manifest `format` parquet: `storage.records_filename` is `posts.parquet`. The write loop writes `posts.parquet` and does not write `posts.csv`.
- YAML `output_format: parquet` on a new dataset: `ensure_dataset_manifest` writes that format, then the second storage object reads it, then `run_sync_tasks` receives `posts.parquet`.
- Keep `sync_records(config_path: Path, *, run_dir_name: str | None = None) -> Path`.
- Keep the record type membership check. Do not change its message or when it runs relative to `init_twitter_client`.

## Test design

One test class per function. Use `data_root`. Prefer public `sync_records` and `run_sync_tasks`. Update existing `run_sync_tasks` calls from `csv_filename=sync_twitter.POSTS_CSV` to `filename=storage.records_filename`.

```text
given no dataset.json
when TwitterStorageManager is constructed
then records_filename is posts.csv

given dataset.json format parquet for a Twitter dataset
when TwitterStorageManager is constructed
then records_filename is posts.parquet

given a csv Twitter dataset and run_sync_tasks with filename=storage.records_filename
when fake fetch returns rows
then run_dir / posts.csv exists
and run_dir / posts.parquet does not exist

given a parquet Twitter dataset and run_sync_tasks with filename=storage.records_filename
when fake fetch returns rows
then run_dir / posts.parquet exists
and run_dir / posts.csv does not exist

given sync_records config with output_format parquet
when sync_records runs with mocked client and run_sync_tasks
then ensure_dataset_manifest is not mocked away
and run_sync_tasks is called with filename posts.parquet
```

The `sync_records` parquet case must use the real `ensure_dataset_manifest`. Keep the existing record type tests that mock it as a no-op. Those tests stay on csv.

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means renaming `csv_filename` to `filename` in `run_sync_tasks` and in existing tests, and adding `filename = storage.records_filename` next to a `raise NotImplementedError` in `sync_records` only on a new parquet helper path if that would break existing tests. Do not break existing `TestSyncRecords` happy paths in Phase 2. Existing tests must stay green after the rename.

Safer scaffold: rename `csv_filename` to `filename` in the signature and in existing tests, still passing `POSTS_CSV` or `storage.records_filename` for csv default (both are `posts.csv` when no manifest exists). Do not recreate storage after the manifest yet. Do not delete `POSTS_CSV` yet.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Rename `csv_filename` to `filename`. Point existing tests at `filename=storage.records_filename`. Keep `POSTS_CSV` unused or still referenced until Phase 5.
3. Phase 3 contracts. Confirm `filename: str` and the Bluesky order comments as stubs if needed. Bodies that already run stay as they are except the renamed argument. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the parquet filename tests. They must fail while `sync_records` still passes `POSTS_CSV` and still constructs storage before the manifest.
5. Phase 5 units, in this order, one commit each:
   1. Recreate Twitter storage after `ensure_dataset_manifest`, pass `filename=storage.records_filename` from `sync_records`, remove `POSTS_CSV`.
6. Phase 6. Run the must-pass commands for this step.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/utils/test_storage.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion tests/data_platform/utils/test_storage.py tests/data_platform/utils/test_dataset.py -q
```

Expected: exit 0. No new failures. Reddit still writes csv names until step 2.

## Must fail / not happen

- `RECORD_TYPE_FILENAMES` gains `twitter.tweet`.
- A new filename helper besides `StorageManager.records_filename`.
- YAML keys changed.
- Bluesky or Reddit product code changed in this step.
- Sibling GitHub issues 103 to 105 and 107 to 116 implemented in this PR.
- `sync_records` still passing a hardcoded `posts.csv` after Phase 5.
