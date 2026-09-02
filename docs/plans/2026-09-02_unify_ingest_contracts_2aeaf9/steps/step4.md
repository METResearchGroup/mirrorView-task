# Step 4: Honor declared output format for Twitter and Reddit raw files

## Goal

YAML `output_format` and `dataset.json` `format` already exist. Bluesky writes `storage.records_filename` (stem + manifest suffix). Twitter hardcodes `POSTS_CSV = "posts.csv"`. Reddit uses `record_type_to_filename`, which always returns `.csv`. Parquet configs then lie.

## Caller / unit of work

**Main caller:** `sync_twitter.sync_records` and `sync_reddit.sync_records` when appending records.

**Slice:** after `ensure_dataset_manifest`, use the storage manager’s format-aware `records_filename` (and Reddit post/comment managers) for append and dedupe filenames.

**Out of scope:** The explicit-pipeline-paths plan (`docs/plans/2026-09-01_explicit_pipeline_paths_ebe7ae`). Do not redesign StorageManager APIs beyond using `records_filename` already implemented in `data_platform/utils/storage.py`.

## Decision (locked)

- Twitter: drop the write path’s dependency on a hardcoded `posts.csv` string. Pass `storage.records_filename` into `run_sync_tasks` the way Bluesky passes `filename=storage.records_filename`.
- Reddit: `record_type_to_filename` must take the dataset format (or return a stem and let StorageManager restem). Result files are `posts.csv`/`comments.csv` or `posts.parquet`/`comments.parquet` matching `ValidDataFormats` from the manifest.
- `RECORD_TYPE_FILENAMES` in `sync_checkpoint.py` may store stems (`posts`, `comments`) plus suffix from format, or keep `.csv` names and let `StorageManager` restem as it already does (`Path(records_filename).stem` + `format.value`). Prefer the existing restem: pass `posts.csv` / `comments.csv` into the manager, then write using `manager.records_filename`.
- Tests that pass `csv_filename=sync_twitter.POSTS_CSV` must pass the storage manager’s `records_filename` instead (still `posts.csv` when format is csv).
- Do not add new YAML keys.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `data_platform/ingestion/sync_bluesky.py` | `filename = storage.records_filename` |
| `data_platform/ingestion/sync_twitter.py` | `POSTS_CSV` and `csv_filename` |
| `data_platform/ingestion/sync_reddit.py` | `record_type_to_filename` |
| `data_platform/ingestion/sync_checkpoint.py` | `RECORD_TYPE_FILENAMES`, `record_type_to_filename` |
| `data_platform/utils/storage.py` | restem in `StorageManager.__init__` |
| `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | `csv_filename=sync_twitter.POSTS_CSV` |
| `data_platform/ingestion/configs/bluesky/mirrorview2.yaml` | `output_format: parquet` example |

## Files allowed to change

- `data_platform/ingestion/sync_twitter.py`
- `data_platform/ingestion/sync_reddit.py`
- `data_platform/ingestion/sync_checkpoint.py` (`record_type_to_filename` / `RECORD_TYPE_FILENAMES` only if required)
- `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_checkpoint.py` if filename helper tests live there
- `tests/data_platform/utils/test_storage.py` for `StorageManager.records_filename` / restem assertions
- `CHANGELOG.md`

## Files forbidden to change

- `data_platform/utils/storage.py` unless a one-line bugfix is required for restem (prefer not)
- Preprocess / features / curate
- YAML except if a test fixture YAML must declare parquet (prefer tmp configs in tests)

## Contracts

```text
TwitterStorageManager(RAW, dataset_id).records_filename
  == "posts.csv" when dataset.json format is csv
  == "posts.parquet" when format is parquet

Reddit comment_storage().records_filename similarly comments.{csv|parquet}
Reddit post_storage().records_filename similarly posts.{csv|parquet}

append_deduped_records(..., filename=that records_filename)
```

## Tests (write first)

`TestStorageManagerRecordsFilename` in `tests/data_platform/utils/test_storage.py` — use `data_root`, `write_dataset_manifest(..., data_format=ValidDataFormats.CSV|PARQUET)`, then construct managers with the default stem (`posts.csv` / `comments.csv`) and assert restem:

- given `dataset.json` `format: csv`, when `TwitterStorageManager(RAW, dataset_id)` is constructed, then `records_filename == "posts.csv"`.
- given `format: parquet`, when the same manager is constructed, then `records_filename == "posts.parquet"`.
- given `format: parquet`, when `RedditStorageManager(RAW, dataset_id).comment_storage()` / `.post_storage()` are constructed, then `records_filename` is `comments.parquet` / `posts.parquet` respectively.

`TestTwitterSyncRecordsFilename` in `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`:

- given a parquet manifest and existing `run_sync_tasks` mocks, when `sync_records` or `run_sync_tasks` runs, then `append_deduped_records` / `append_records` is called with `filename="posts.parquet"` (spy or assert output path under `run_dir / "posts.parquet"`).
- given csv manifest (default), existing checkpoint tests still pass when they pass `storage.records_filename` instead of `sync_twitter.POSTS_CSV` (still `posts.csv`).

`TestRedditSyncRecordsFilename` in `tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`:

- given parquet manifest, when `run_sync_tasks` appends comments and posts, then writers use `comment_storage.records_filename` and `post_storage.records_filename` (`comments.parquet`, `posts.parquet`) — not hardcoded `.csv` from `record_type_to_filename` alone.
- given csv manifest, filenames remain `comments.csv` / `posts.csv`.

If `record_type_to_filename` gains a format parameter, extend `TestRecordTypeToFilename` in `tests/data_platform/ingestion/test_sync_checkpoint.py`; if restem-only, add one test that passing `posts.csv` into `TwitterStorageManager` with a parquet manifest still yields `posts.parquet` on write.

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. One test class per function or manager under test.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion tests/data_platform/utils/test_storage.py tests/data_platform/utils/test_dataset.py -q
```

Exit 0.

## Must not happen

- Bluesky write path regressed to a hardcoded csv name.
- Manifest `format` parquet with Twitter still creating `posts.csv` in a new run.
- Changing preprocess file discovery in this PR.
