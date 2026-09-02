# Step 1: Omit the metadata field and stamp rows from the folder name

## Goal

New raw `metadata.json` does not contain `sync_timestamp`. Twitter and Reddit resume stamps CSV row timestamps from the run folder name, which is the last path segment, not the full package-relative directory. `row_count` and `post_row_count` stay as they are. Row models keep their `sync_timestamp` column.

## Caller / unit of work

**Main caller:** `prepare_sync_run` in `/workspace/data_platform/ingestion/sync_checkpoint.py`, used by `sync_records` in `sync_twitter.py`, `sync_reddit.py`, and `sync_bluesky.py`. Twitter and Reddit then stamp rows during `run_sync_tasks`.

**Slice:** write new raw metadata without `sync_timestamp`; on resume and on a new run, stamp Twitter and Reddit rows with `Path(relative_run_dir).name`; keep resume completing a second wave into the same run directory.

**Out of scope:** dropping curated `files` (issue #85); rewriting JSON already on disk; a reader that still looks up `metadata["sync_timestamp"]`; adding `sync_timestamp` to Bluesky rows; renaming `row_count` or `post_row_count`; changing row models; experiments under `/workspace/experiments/`.

## Decision (locked)

Pick the option that most literally matches Done-when.

1. `build_base_sync_metadata` in `/workspace/data_platform/ingestion/sync_checkpoint.py` does not include a `sync_timestamp` key. Remove the `sync_timestamp` parameter from that function. Do not write the key on any other path.
2. `init_sync_metadata` in `/workspace/data_platform/ingestion/sync_twitter.py`, `/workspace/data_platform/ingestion/sync_reddit.py`, and `/workspace/data_platform/ingestion/sync_bluesky.py` drops the `sync_timestamp` parameter and stops passing it into `build_base_sync_metadata`.
3. `prepare_sync_run` still creates a new run directory with `get_current_timestamp()`. Change `init_metadata_fn` to `Callable[[], dict[str, Any]]` and call it with no argument. The three `sync_records` lambdas become `lambda: init_sync_metadata(config, config_path, sync_tasks)`.
4. Stamp value is `Path(relative_run_dir).name`. That is the timestamp folder, for example `2026_05_30-10:00:00`. It is not the package-relative directory, for example `data/twitter/{dataset_id}/raw/2026_05_30-10:00:00`. Inline `Path(...).name` at the two stamp sites. Do not add a new helper module. Do not add a named helper unless a third call site appears.
5. Twitter: remove the `sync_timestamp` parameter from `run_sync_tasks`. Set `sync_timestamp = Path(relative_run_dir).name` inside `run_sync_tasks` and pass that string into `fetch_posts_for_keyword`. Remove `sync_timestamp = str(metadata["sync_timestamp"])` from `sync_records`.
6. Reddit: in `run_sync_tasks`, replace `sync_timestamp = str(metadata["sync_timestamp"])` with `sync_timestamp = Path(relative_run_dir).name`. Keep passing that string into `fetch_records_for_subreddit`.
7. Bluesky rows have no `sync_timestamp` column. Do not add one. Only drop the unused metadata parameter on Bluesky `init_sync_metadata`.
8. Keep `sync_timestamp` on `SyncTwitterPostModel`, `SyncRedditPostModel`, and `SyncRedditCommentModel` in `/workspace/data_platform/models/sync.py`. Keep fixture rows in `twitter_conftest.py` and `reddit_conftest.py` with that column.
9. Keep metadata keys `row_count` and `post_row_count` with the same names and meanings. Reddit still writes both.
10. Do not strip `sync_timestamp` from metadata loaded on resume. Flush writes the dict that was loaded. Old JSON that still has the key may keep it. New JSON must not grow the key.
11. Do not read `metadata["sync_timestamp"]` as a fallback. Do not add a dual-key writer.

No new modules. Phases 2 and 3 have no new files. Do not stub `build_base_sync_metadata`, `prepare_sync_run`, or `run_sync_tasks`. Unattended: skip Phase 3 approval.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-02_resume_raw_ingest_from_run_dir_9f2b18/plan.md` | Parent plan |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | Shared metadata writer and `prepare_sync_run` |
| `/workspace/data_platform/ingestion/sync_twitter.py` | Reads metadata stamp; `run_sync_tasks` takes an explicit stamp |
| `/workspace/data_platform/ingestion/sync_reddit.py` | Reads metadata stamp inside `run_sync_tasks` |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | `init_sync_metadata` still takes the unused stamp |
| `/workspace/data_platform/models/sync.py` | Row models keep the column |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | `test_build_base_sync_metadata_includes_tasks` |
| `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Resume and `init_sync_metadata` / `run_sync_tasks` calls |
| `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Resume and `init_sync_metadata` calls |
| `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | `init_sync_metadata` calls |
| `/workspace/data_platform/utils/storage.py` | `create_new_run_dir` returns a package-relative directory |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`

## Files forbidden to change

- `/workspace/data_platform/models/sync.py`
- `/workspace/data_platform/ingestion/twitter_client.py`
- `/workspace/tests/data_platform/ingestion/twitter_conftest.py`
- `/workspace/tests/data_platform/ingestion/reddit_conftest.py`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/generate_features/**`
- Historical `metadata.json` under `experiments/` or `data_platform/data/`
- Plan files under `/workspace/docs/plans/2026-09-02_resume_raw_ingest_from_run_dir_9f2b18/` during implementation

## Contracts to lock

`build_base_sync_metadata` writes this mapping plus optional `extra_fields`, and does not include `sync_timestamp`:

```text
{
  "sync_status": SyncStatus.IN_PROGRESS.value,
  "dataset_id": require_dataset_id(config),
  "name": config["name"],
  "description": config["description"],
  "date": config["date"],
  "ingestion_config": config_path.name,
  "record_types": config["record_types"],
  "ingestion_params": config["ingestion_params"],
  "row_count": 0,
  "tasks": {task.task_id: task_progress_builder(task) for task in sync_tasks},
}
```

Signature:

```text
def build_base_sync_metadata(
    config: dict[str, Any],
    config_path: Path,
    sync_tasks: Sequence[TTask],
    *,
    task_progress_builder: Callable[[TTask], dict[str, Any]],
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]
```

`prepare_sync_run`:

```text
init_metadata_fn: Callable[[], dict[str, Any]]
...
metadata = init_metadata_fn()
```

Twitter and Reddit row stamp:

```text
sync_timestamp = Path(relative_run_dir).name
```

`row_count` remains the comment or post count already stored today. Reddit `post_row_count` remains the post count.

## Test design

given `build_base_sync_metadata` for a Twitter config with extra_fields post_row_count 0
when the function returns
then "sync_timestamp" is not a key
and metadata["row_count"] == 0
and metadata["post_row_count"] == 0

given Twitter, Reddit, and Bluesky `init_sync_metadata` without a timestamp argument
when the function returns
then "sync_timestamp" is not a key
and the task ledger is unchanged

given a Twitter run directory whose package-relative path ends with `2026_05_30-10:00:00`
and task alpha already completed
when `run_sync_tasks` resumes the remaining task
then only beta is fetched
and resumed metadata["row_count"] == 2
and every stored row's `sync_timestamp` equals `Path(run_dir).name`
and that value is not equal to `run_dir`
and "sync_timestamp" is not a key in resumed metadata

given a Reddit run directory whose package-relative path ends with `2026_05_30-10:00:00`
and subreddit alphasub already completed
when `run_sync_tasks` resumes the remaining subreddit
then only betasub is fetched
and resumed metadata["row_count"] == 2
and stored comment and post rows from the second wave have `sync_timestamp` equal to `Path(run_dir).name`
and that value is not equal to `run_dir`
and "sync_timestamp" is not a key in resumed metadata

given Bluesky resume of a completed task
when `run_sync_tasks` runs the second wave
then it still skips the completed task and finishes into the same run directory
and "sync_timestamp" is not a key in resumed metadata

Twitter resume `fake_fetch` must write `sync_timestamp` from the argument it receives onto the returned rows, using `mock_tweet_row(..., sync_timestamp=sync_timestamp)`. Reddit resume `fake_fetch` must do the same for `mock_post_row` and `mock_comment_row`. After Phase 4, drop `sync_timestamp=` from every Twitter `run_sync_tasks` call. After Phase 4, drop the timestamp positional argument from every `init_sync_metadata` and `build_base_sync_metadata` call.

Load stored rows with `storage.load_records(f"{run_dir}/{POSTS_FILENAME}")` (and comments for Reddit). Assert the column values, not only that the key exists.

Update existing tests. Do not add a second test module.

## Implementation notes

Follow implement-from-spec. Unattended.

Phase 1: scope above.

Phase 2: no new files. Do not commit an empty scaffold.

Phase 3: contracts above. Do not stub the live writer. Skip approval.

Phase 4: change the tests listed above. Commit. They must fail because metadata still contains `sync_timestamp`, Twitter `run_sync_tasks` still requires the stamp argument, and Reddit `run_sync_tasks` still reads `metadata["sync_timestamp"]`.

Phase 5 units of work:

1. `build_base_sync_metadata` omits `sync_timestamp` and drops that parameter. `init_sync_metadata` on all three platforms drops the parameter. `prepare_sync_run` calls `init_metadata_fn()` with no argument. Metadata tests go green.
2. Twitter `run_sync_tasks` derives `Path(relative_run_dir).name` and no longer takes `sync_timestamp`. Twitter `sync_records` no longer reads the metadata field. Twitter resume tests go green.
3. Reddit `run_sync_tasks` derives `Path(relative_run_dir).name` instead of `metadata["sync_timestamp"]`. Reddit resume tests go green.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion tests/data_platform -q
```

Expected: exit 0.

A newly written raw metadata mapping has `"sync_timestamp" not in metadata`.

Twitter and Reddit resume tests complete a second wave into the same `run_dir`. Stored row `sync_timestamp` values equal `Path(run_dir).name`.

## Must fail / not happen

- Writing `sync_timestamp` in new raw metadata.
- Stamping rows with the full package-relative run directory string.
- Reading `metadata["sync_timestamp"]` as the stamp source.
- A second write path that still emits the dropped field.
- Renaming `row_count` or `post_row_count`.
- Removing `sync_timestamp` from row models.
- Adding `sync_timestamp` to Bluesky rows.
- Rewriting historical raw JSON under `experiments/` or `data_platform/data/`.
- Dropping curated `files`.
