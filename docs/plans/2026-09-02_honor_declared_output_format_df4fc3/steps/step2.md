# Step 2: Point the Reddit writer at the storage filename

## Goal

Make `sync_reddit.run_sync_tasks` write raw comments and posts using `comment_storage.records_filename` and `post_storage.records_filename`, after the dataset manifest exists, matching Bluesky and the Twitter change in step 1.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_reddit.py` `sync_records` through `run_sync_tasks`.

**Task:** create the dataset manifest, construct comment and post storage so they read `dataset.json` format, then pass those storage filenames into the Reddit write loop.

**Out of scope:** Twitter writers (step 1, already done). YAML key changes. Twitter record type validation. Bluesky `author_filter`. Repo relative config path helper. Making `record_type_to_filename` format aware. Adding `twitter.tweet` to `RECORD_TYPE_FILENAMES`. Sibling issues. `CHANGELOG.md` during implementation.

## Decision (locked)

Do not invent a second filename scheme. Do not change `record_type_to_filename` so it takes a format. That helper always returns `.csv` and is the bug. Stop calling it from Reddit writers.

`RedditStorageManager` already restems through `StorageManager.__init__`. Default comment storage uses stem `comments.csv`. `post_storage()` uses stem `posts.csv`. After a parquet manifest, those become `comments.parquet` and `posts.parquet`.

Copy Bluesky and step 1 for construct order:

```text
ensure_dataset_manifest(
    RedditStorageManager(StorageStage.RAW, dataset_id),
    "reddit",
    dataset_id,
    config,
    config_path,
)
comment_storage = RedditStorageManager(StorageStage.RAW, dataset_id)
post_storage = comment_storage.post_storage()
```

In `run_sync_tasks`, replace:

```text
comments_csv = record_type_to_filename(COMMENTS_RECORD_TYPE)
posts_csv = record_type_to_filename(POSTS_RECORD_TYPE)
```

with:

```text
comments_filename = comment_storage.records_filename
posts_filename = post_storage.records_filename
```

Rename the `comments_csv` and `posts_csv` parameters on `_open_reddit_dedupe_sessions` and `_append_subreddit_deduped_rows` to `comments_filename` and `posts_filename`. Leave `record_type_to_filename` and `RECORD_TYPE_FILENAMES` in `/workspace/data_platform/ingestion/sync_checkpoint.py` unchanged. Tests for that helper stay as they are.

Remove the `record_type_to_filename` import from `sync_reddit.py` when it has no remaining uses.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-02_honor_declared_output_format_df4fc3/plan.md` | Parent plan |
| `/workspace/docs/plans/2026-09-02_honor_declared_output_format_df4fc3/steps/step1.md` | Twitter pattern this step copies |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Manifest then storage then `storage.records_filename` |
| `/workspace/data_platform/ingestion/sync_twitter.py` | Step 1 result |
| `/workspace/data_platform/ingestion/sync_reddit.py` | Current `record_type_to_filename` calls and construct order |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | `record_type_to_filename` stays csv only and unused by this writer |
| `/workspace/data_platform/utils/storage.py` | `RedditStorageManager.comment_storage` and `post_storage` |
| `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Existing Reddit write tests |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | `test_record_type_to_filename_known_types` must still pass |
| `/workspace/tests/data_platform/utils/test_storage.py` | Add Reddit parquet filename coverage here |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/workspace/tests/data_platform/utils/test_storage.py`

Plan files under `/workspace/docs/plans/2026-09-02_honor_declared_output_format_df4fc3/` are already on this branch. Do not rewrite them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/utils/dataset.py`
- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/ingestion/configs/**`
- `/workspace/CHANGELOG.md` during implementation
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

`run_sync_tasks` keeps this signature:

```text
run_sync_tasks(
    reddit,
    ingestion_params,
    output_dir,
    comment_storage,
    post_storage,
    metadata,
    sync_tasks,
    *,
    include_comments: bool,
    include_posts: bool,
) -> None
```

It must not take hardcoded csv names from `record_type_to_filename`.

Internal helpers take storage filenames:

```text
comments_filename: str
posts_filename: str
```

Behavior:

- Default csv dataset: comments file is `comments.csv`, posts file is `posts.csv`.
- Manifest `format` parquet: comments file is `comments.parquet`, posts file is `posts.parquet`. The csv names are not written.
- YAML `output_format: parquet` on a new dataset: after `ensure_dataset_manifest`, reconstructed storage reports parquet filenames, and the write loop uses them.
- Keep `record_type_to_filename("reddit.comment") == "comments.csv"` in the shared helper. That is leftover csv mapping, not the writer path.

## Test design

One test class per function. Use `data_root`. Prefer public `run_sync_tasks` and `sync_records`.

```text
given dataset.json format parquet for a Reddit dataset
when comment storage and post storage are constructed
then comment records_filename is comments.parquet
and post records_filename is posts.parquet

given a csv Reddit dataset
when run_sync_tasks writes comments and posts
then run_dir / comments.csv and run_dir / posts.csv exist
and parquet names do not exist

given a parquet Reddit dataset
when run_sync_tasks writes comments and posts
then run_dir / comments.parquet and run_dir / posts.parquet exist
and csv names do not exist

given sync_records config with output_format parquet
when sync_records runs with mocked client and run_sync_tasks
then run_sync_tasks receives comment_storage.records_filename comments.parquet
and post_storage.records_filename posts.parquet
```

The `sync_records` parquet case must use the real `ensure_dataset_manifest`. Existing `run_sync_tasks` tests stay on csv default.

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means renaming `comments_csv` and `posts_csv` to `comments_filename` and `posts_filename` while still assigning them from `record_type_to_filename`, so existing tests stay green.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Rename the csv parameter names. Keep assigning from `record_type_to_filename`.
3. Phase 3 contracts. Confirm the helper argument names. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the parquet filename tests. They must fail while Reddit still uses `record_type_to_filename` and still constructs storage before the manifest.
5. Phase 5 units, in this order, one commit each:
   1. Recreate Reddit storage after `ensure_dataset_manifest`. Assign filenames from `comment_storage.records_filename` and `post_storage.records_filename`. Drop the `record_type_to_filename` import from `sync_reddit.py`.
6. Phase 6. Run the must-pass commands.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion tests/data_platform/utils/test_storage.py tests/data_platform/utils/test_dataset.py -q
```

Expected: exit 0.

## Must fail / not happen

- `record_type_to_filename` taught about format or about `twitter.tweet`.
- A new filename helper.
- YAML keys changed.
- Twitter or Bluesky product code changed in this step.
- Shared checkpoint helper tests failing because `record_type_to_filename` was deleted.
- Sibling GitHub issues implemented in this PR.
