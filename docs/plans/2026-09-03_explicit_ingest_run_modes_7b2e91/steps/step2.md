# Step 2: Require an explicit mode on Bluesky ingest only

## Goal

Replace Bluesky's combined `sync_records` plus shared `run_sync_cli` with two public functions and two CLI commands: `new-run` and `resume`. Resume takes exactly one of `--run-dir` or `--latest`. Twitter and Reddit keep `sync_records` and `run_sync_cli`.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_bluesky.py` `main`, which dispatches to `sync_records_new_run` or `sync_records_from_checkpoint`.

**Task:** load config and storage once, open the run with the Step 1 helpers, then run the existing keyword loop and finalize.

**Out of scope:** Twitter and Reddit CLIs. Changing `prepare_sync_run` or `run_sync_cli`. Feature-generation `--run-dir`. Force-reopen. Dedup policy. `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_bluesky.py` | Current `sync_records`, stub functions, `main` via `run_sync_cli` |
| `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_checkpoint.py` | Step 1 helpers, `run_sync_cli` (leave as-is), `ensure_dataset_manifest` |
| `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | `minimal_sync_config`, `make_bluesky_client`, `test_resume_skips_completed_tasks` |
| `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/conftest.py` | Bluesky fixtures |
| `/Users/mark/src/work/mirrorView-task/tests/data_platform/constants.py` | `TEST_INGEST_CONFIG_PATH`, `VALID_DATASET_ID` |
| `/Users/mark/src/work/mirrorView-task/data_platform/README.md` | Bluesky ingest commands |
| `/Users/mark/src/work/mirrorView-task/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Bluesky sync sequence and checkpoint resume flow |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_bluesky.py`
- `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/data_platform/README.md`
- `/Users/mark/src/work/mirrorView-task/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`

Do not edit the plan package during implementation.

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_twitter.py`
- `/Users/mark/src/work/mirrorView-task/data_platform/ingestion/sync_reddit.py`
- `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/Users/mark/src/work/mirrorView-task/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

In `sync_bluesky.py`:

Delete the `pass` stubs named `sync_records_from_start` and `sync_records_from_checkpoint` if they are still present. Do not keep a public `sync_records` that guesses new vs resume.

```text
def load_bluesky_sync_context(config_path: Path) -> BlueskySyncContext:

def sync_records_new_run(config_path: Path) -> Path:

def sync_records_from_checkpoint(
    config_path: Path,
    run_dir_name: str | None,
    latest: bool,
) -> Path:

def execute_bluesky_sync(
    context: BlueskySyncContext,
    output_dir: Path,
    metadata: dict[str, Any],
) -> Path:
```

`BlueskySyncContext` is a frozen dataclass holding config, config_path, storage, ingestion_params, sync_tasks, client, and filename. `load_bluesky_sync_context` contains today's config load, `require_dataset_id`, `ensure_dataset_manifest`, storage construction, `build_sync_tasks`, record-type check, and `BlueskyClient()` construction.

`sync_records_new_run`:

- Load context.
- `output_dir, metadata = start_new_sync_run(storage, init_metadata_fn=...)`.
- Return `execute_bluesky_sync(...)`.

`sync_records_from_checkpoint`:

- Raise `ValueError` if `latest` is True and `run_dir_name` is not None.
- Raise `ValueError` if `latest` is False and `run_dir_name` is None. Message must say resume requires exactly one of a named run directory or latest.
- Load context.
- If `latest`, `run_dir_name = require_latest_in_progress_run_dir(storage).name`.
- `output_dir, metadata = load_checkpoint_run(storage, sync_tasks, run_dir_name, "keywords")`.
- Return `execute_bluesky_sync(...)`.

`execute_bluesky_sync` is today's `run_sync_tasks` plus `finalize_local_disk_sync` plus the existing print and return of `output_dir`.

CLI: replace `run_sync_cli` with a Typer app that has two subcommands and `no_args_is_help=True`.

```text
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py new-run \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml

PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py resume \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml \
  --run-dir 2026_05_30-12:00:00

PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py resume \
  --config data_platform/ingestion/configs/bluesky/mirrorview.yaml \
  --latest
```

Both subcommands take `--config`. Resume takes `--run-dir` as optional str and `--latest` as a flag defaulting to False at the CLI layer only. The resume subcommand passes those two values into `sync_records_from_checkpoint` with no extra defaulting in the Python function.

Module docstring, `data_platform/README.md` Bluesky ingest example, and the Bluesky sync / checkpoint sections of `docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` must show `new-run` and `resume`, not config-only Bluesky ingest. The runbook sequence diagram must not say Bluesky calls `prepare_sync_run`. Leave Twitter and Reddit command examples as they are.

Do not import or call `prepare_sync_run` or `run_sync_cli` from `sync_bluesky.py`.

## Test design

Add classes in `test_sync_bluesky_checkpoint.py`. Mock `BlueskyClient._search_posts_page` the same way as `test_run_sync_tasks_appends_per_keyword`. Write a real YAML file in the test tmp dir that matches `minimal_sync_config()`, or patch `load_yaml_config` / write YAML via the existing `TEST_INGEST_CONFIG_PATH` only if that file already matches. Prefer writing a temp YAML from `minimal_sync_config()` so tests do not depend on committed mirrorview YAML.

Monkeypatch `get_current_timestamp` for new-run tests. Patch `BlueskyClient.__init__` or pass through the existing `make_bluesky_client` by monkeypatching `sync_bluesky.BlueskyClient` to a factory that returns `make_bluesky_client()`.

```text
given a temp config and no raw runs
when sync_records_new_run(config_path)
then a new run directory is created
and both keyword tasks complete

given an in_progress raw run for that dataset
when sync_records_new_run(config_path)
then raise ValueError matching "unfinished"

given an in_progress run with alpha completed and beta pending
when sync_records_from_checkpoint(config_path, run_dir_name=that_name, latest=False)
then beta is fetched
and alpha is not refetched

given the same in_progress run
when sync_records_from_checkpoint(config_path, run_dir_name=None, latest=True)
then the same run directory is returned

given no unfinished run
when sync_records_from_checkpoint(config_path, run_dir_name=None, latest=True)
then raise FileNotFoundError

given a completed run
when sync_records_from_checkpoint(config_path, run_dir_name=that_name, latest=False)
then raise ValueError matching "completed"

when sync_records_from_checkpoint(config_path, run_dir_name="x", latest=True)
then raise ValueError matching "exactly one"

when sync_records_from_checkpoint(config_path, run_dir_name=None, latest=False)
then raise ValueError matching "exactly one"
```

Keep existing `run_sync_tasks` resume tests. They still prove the loop skips completed tasks.

Optional: one `typer.testing.CliRunner` test that invoking the module with no subcommand exits non-zero or prints help. Skip if wiring the Typer app for import is awkward; the Python-level exclusivity tests are required.

## Implementation notes (implement-from-spec)

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `BlueskySyncContext`, `load_bluesky_sync_context`, `sync_records_new_run`, `sync_records_from_checkpoint`, and `execute_bluesky_sync` as stubs (`raise NotImplementedError`). Point `main` at a Typer app with `new-run` and `resume` subcommands that call those functions. Delete `sync_records` and the `pass` stubs. Commit.
3. Phase 3 contracts. Signatures match the freeze. Full auto.
4. Phase 4 test design. Add the tests. They fail for `NotImplementedError` or missing exclusivity. Commit.
5. Phase 5 units, in this order, one commit each:
   1. Implement `load_bluesky_sync_context` and `execute_bluesky_sync`.
   2. Implement `sync_records_from_checkpoint` exclusivity plus named and latest resume.
   3. Implement `sync_records_new_run`.
   4. Update `data_platform/README.md` and the ingest runbook Bluesky sections.
6. Phase 6. Run the must-pass commands. Confirm Twitter and Reddit still import `run_sync_cli` and `prepare_sync_run`. Confirm `sync_bluesky.py` does not import those two names.

## Must pass

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_checkpoint.py tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py -q
```

Expected: exit 0.

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. Twitter and Reddit tests unchanged.

```bash
cd /Users/mark/src/work/mirrorView-task
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py --help
```

Expected: exit 0. Help lists `new-run` and `resume`, not a config-only default command.

## Must fail / not happen

- Twitter or Reddit CLI changed.
- `prepare_sync_run` or `run_sync_cli` called from `sync_bluesky.py`.
- A public Bluesky `sync_records` that auto-resumes.
- Completed Bluesky runs reopened.
- Feature-generation scripts edited.
- `CHANGELOG.md` edited.
