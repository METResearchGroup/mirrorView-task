# Step 1: Add fail-fast new-run and resume helpers beside the combined opener

## Goal

Add two openers in the shared checkpoint module that cannot take the other branch: one that only creates a new raw run, and one that only loads an unfinished named run. Add a helper that requires a latest unfinished run and fails when none exists. Leave `prepare_sync_run` and `find_resume_run_dir` unchanged so Twitter and Reddit keep today's combined behavior.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_checkpoint.py` `start_new_sync_run`, `load_checkpoint_run`, and `require_latest_in_progress_run_dir`.

**Task:** prove the four fail-fast outcomes and the `--latest` locator against storage and metadata, without wiring Bluesky yet.

**Out of scope:** Bluesky CLI and `sync_records` split (Step 2). Twitter and Reddit scripts. Changing `prepare_sync_run` or `find_resume_run_dir`. Feature-generation `--run-dir`. Force-reopen of completed runs. `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_checkpoint.py` | `find_resume_run_dir`, `prepare_sync_run`, `validate_tasks_for_resume`, `flush_run_metadata`, `SyncStatus` |
| `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_checkpoint.py` | Existing `test_find_resume_run_dir_*` and metadata helpers. Pattern for storage fixtures |
| `/Users/mark/src/work/mirrorView-task/tests/data_platform/constants.py` | `VALID_DATASET_ID` |
| `/Users/mark/src/work/mirrorView-task/data_platform/utils/storage.py` | `create_new_run_dir`, `load_run_metadata`, `write_run_metadata_atomic` |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_checkpoint.py`

Plan package files under `/Users/mark/src/work/mirrorView-task/docs/plans/2026-09-03_explicit_ingest_run_modes_7b2e91/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_bluesky.py`
- `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_twitter.py`
- `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_reddit.py`
- `/Users/mark/src/work/mirrorView-task/data_platform/README.md`
- `/Users/mark/src/work/mirrorView-task/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`
- `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add these public helpers in `sync_checkpoint.py`. Do not change `prepare_sync_run` or `find_resume_run_dir`.

```text
def start_new_sync_run(
    storage: StorageManager,
    init_metadata_fn: Callable[[str], dict[str, Any]],
) -> tuple[Path, dict[str, Any]]:

def load_checkpoint_run(
    storage: StorageManager,
    sync_tasks: Sequence[HasTaskId],
    run_dir_name: str,
    entity_label: str,
) -> tuple[Path, dict[str, Any]]:

def require_latest_in_progress_run_dir(storage: StorageManager) -> Path:
```

Behavior:

- `start_new_sync_run`: if `find_resume_run_dir(storage, run_dir_name=None)` is not None, raise `ValueError` whose message says an unfinished run exists and the operator must resume it. Otherwise call `get_current_timestamp()`, `storage.create_new_run_dir(sync_timestamp)`, `init_metadata_fn(sync_timestamp)`, `flush_run_metadata`, and return `(output_dir, metadata)`. Do not load existing metadata.
- `load_checkpoint_run`: resolve `storage.root_dir / run_dir_name`. Raise `FileNotFoundError` if that path is not a directory. Load metadata. If `sync_status` is `completed`, raise `ValueError` whose message says the run is already completed. Call `validate_tasks_for_resume`. If `sync_status` is not `in_progress`, set it to `in_progress` and flush. Return `(run_dir, metadata)`. Never create a directory.
- `require_latest_in_progress_run_dir`: call `find_resume_run_dir(storage, run_dir_name=None)`. If the result is None, raise `FileNotFoundError` whose message says no unfinished run exists. Otherwise return that path.
- Numpy docstrings on all three.
- Keep `prepare_sync_run` as the Twitter/Reddit combined opener. Keep `find_resume_run_dir` returning None when nothing is unfinished, including when `run_dir_name` is None.

Do not add a `--force` flag or a reopen path for completed runs.

## Test design

One test class per new function. Use `BlueskyStorageManager` or `TwitterStorageManager` with the existing `data_root` fixture, matching `test_find_resume_run_dir_*`. Use `_StubTask` already in the file. Monkeypatch `get_current_timestamp` for new-run tests.

```text
given no raw runs
when start_new_sync_run(storage, init_metadata_fn)
then a new run directory named with the patched timestamp exists
and metadata is the init payload flushed to disk

given an in_progress raw run
when start_new_sync_run(storage, init_metadata_fn)
then raise ValueError matching "unfinished"
and no additional run directory is created

given only completed raw runs
when start_new_sync_run(storage, init_metadata_fn)
then a new run directory is created

given an in_progress run whose tasks match the stub tasks
when load_checkpoint_run(storage, tasks, that run dir name, "keywords")
then return that directory and its metadata

given no such directory
when load_checkpoint_run(...)
then raise FileNotFoundError

given a completed run
when load_checkpoint_run(...)
then raise ValueError matching "completed"
and metadata on disk stays completed

given an in_progress run whose tasks do not match
when load_checkpoint_run(...)
then raise ValueError from validate_tasks_for_resume

given a newer in_progress run and an older completed run
when require_latest_in_progress_run_dir(storage)
then return the newer in_progress directory

given only completed runs, or no runs
when require_latest_in_progress_run_dir(storage)
then raise FileNotFoundError matching "unfinished"
```

Keep `test_find_resume_run_dir_specific_run` and `test_find_resume_run_dir_latest_in_progress` passing unchanged.

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means adding the three helpers as `raise NotImplementedError` in `sync_checkpoint.py`. Do not put the real fail-fast logic in until Phase 5.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add the three helpers with `raise NotImplementedError` and numpy docstrings. Commit.
3. Phase 3 contracts. Confirm signatures match the freeze. Bodies stay stubs. Full auto. Commit only if signatures change.
4. Phase 4 test design. Add the tests from the pseudocode. They must fail for `NotImplementedError`. Commit.
5. Phase 5 units, in this order, one commit each:
   1. Implement `require_latest_in_progress_run_dir`. Its tests pass.
   2. Implement `load_checkpoint_run`. Its tests pass. `require_latest` tests stay green.
   3. Implement `start_new_sync_run`. All new tests pass. Existing `find_resume_run_dir` and `prepare_sync_run` callers stay green.
6. Phase 6. Run the must-pass commands. Confirm `prepare_sync_run` body is unchanged.

## Must pass

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_checkpoint.py -q
```

Expected: exit 0.

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. Twitter and Reddit checkpoint tests still pass through `prepare_sync_run`.

## Must fail / not happen

- `prepare_sync_run` rewritten or deleted.
- `find_resume_run_dir` now raising instead of returning None.
- Bluesky, Twitter, or Reddit CLI changed.
- Completed runs reopened as in_progress by the new helpers.
- `CHANGELOG.md` edited.
