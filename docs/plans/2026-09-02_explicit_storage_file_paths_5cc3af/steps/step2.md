# Step 2: Switch ingest callers and drop output format from configs

## Goal

Ingest CLIs pass full file names and package-relative file paths into the storage API from step 1. Ingest YAML no longer declares `output_format`. New dataset manifests still omit `format`.

## Caller / unit of work

**Main caller:** `sync_records` in `/workspace/data_platform/ingestion/sync_bluesky.py`, `/workspace/data_platform/ingestion/sync_twitter.py`, and `/workspace/data_platform/ingestion/sync_reddit.py`.

**Slice:** start or resume a raw run; append posts or comments to `posts.csv` or `comments.csv` under that run; write metadata against the package-relative run directory; create a dataset manifest with no format key.

**Out of scope:** preprocess, features, curate; slimming raw metadata keys (no dropping `sync_timestamp`); parquet ingest via a new YAML field.

## Decision (locked)

Ingest always writes `POSTS_FILENAME` and `COMMENTS_FILENAME` from `/workspace/data_platform/constants.py` (`posts.csv`, `comments.csv`). Remove `output_format` from YAML. Do not add a replacement filename key. The two Bluesky configs that currently set `output_format: parquet` will write csv.

`RECORD_TYPE_FILENAMES` in `/workspace/data_platform/ingestion/sync_checkpoint.py` already maps to `posts.csv` and `comments.csv`. Point those values at the constants instead of repeating the literals.

`prepare_sync_run` still creates or resumes a run. It must pass the package-relative directory string from `create_new_run_dir` / `latest_run_dir` into metadata helpers. Checkpoint internals that currently take `Path` run dirs should take the relative string and resolve with `resolve_package_path` only when they need a filesystem `Path` (for example mkdir already happened inside storage).

`ensure_dataset_manifest` must call `write_dataset_manifest` without `data_format` and without reading `config["output_format"]`. Delete the `ValidDataFormats` import from this file.

Join a records file path as `f"{relative_run_dir}/{POSTS_FILENAME}"` (or `COMMENTS_FILENAME`). Pass that string to `append_records`, `load_seen_ids_from_disk`, and `append_deduped_records`.

`sync_records` currently returns `Path`. Returning the package-relative run directory string is allowed if tests are updated. If a caller outside `tests/data_platform` needs a `Path`, resolve it at the edge. Prefer returning the relative string so the public ingest path matches storage.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | Manifest, prepare_sync_run, flush metadata, filename map |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Uses `storage.records_filename` |
| `/workspace/data_platform/ingestion/sync_twitter.py` | `POSTS_CSV` and filename kwargs |
| `/workspace/data_platform/ingestion/sync_reddit.py` | comments and posts filenames |
| `/workspace/data_platform/ingestion/configs/bluesky/mirrorview2.yaml` | `output_format: parquet` |
| `/workspace/data_platform/ingestion/configs/bluesky/trump_econ_iran.yaml` | `output_format: parquet` |
| `/workspace/tests/data_platform/ingestion/` | Checkpoint and durability tests |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview2.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/trump_econ_iran.yaml`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_local_durability.py`
- Other files under `/workspace/tests/data_platform/ingestion/` that fail because they still pass `Path` run dirs or `storage.records_filename`

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/utils/dataset.py`
- `/workspace/data_platform/utils/paths.py`
- `/workspace/data_platform/constants.py`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/generate_features/**`
- Historical `dataset.json` files under `experiments/` or `data_platform/data/`

## Contracts to lock

```text
ensure_dataset_manifest(...)
  if dataset.json missing:
    write_dataset_manifest(platform, dataset_id, name=..., ingestion_config=...)
  Do not pass data_format. Do not read output_format.

prepare_sync_run(...) -> tuple[str, dict]
  First element is the package-relative run directory string.

flush_run_metadata(storage, relative_run_dir: str, metadata)
finalize_local_disk_sync(storage, relative_run_dir: str, metadata)

Bluesky/Twitter append path: f"{relative_run_dir}/{POSTS_FILENAME}"
Reddit comments path: f"{relative_run_dir}/{COMMENTS_FILENAME}"
Reddit posts path: f"{relative_run_dir}/{POSTS_FILENAME}"
```

Remove `filename = storage.records_filename` from `/workspace/data_platform/ingestion/sync_bluesky.py`.

In YAML, delete the `output_format: parquet` line from:

- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview2.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/trump_econ_iran.yaml`

Do not add another key in its place.

## Test design

Update ingest tests so every `create_new_run_dir` result is treated as a relative string. Replace `storage.records_filename` with `POSTS_FILENAME` or `COMMENTS_FILENAME`. Replace `append_records(rows, run_dir)` with `append_records(rows, f"{run_dir}/{POSTS_FILENAME}")`. Replace `load_run_metadata(run_dir)` with the relative directory string (already the return value).

given a first ingest of a new dataset
when ensure_dataset_manifest writes dataset.json
then the file has no `format` key

given a Bluesky checkpoint test that previously passed `filename=storage.records_filename`
when it appends and resumes
then it uses `f"{run_dir}/{POSTS_FILENAME}"` and still skips seen uris

Inspect a written csv in tests through `resolve_package_path(relative_file_path)`, not by treating the run directory string as a `Path`.

## Implementation notes

Follow implement-from-spec. Unattended. Step 1 storage API is already landed. Do not restub storage.

Phase 2 for this step is wiring only: change call signatures in ingest modules so they pass relative paths, with `NotImplementedError` only if you introduce a new helper. Prefer updating real call sites in dependency order rather than adding a new ingest abstraction.

Phase 5 units of work:

1. `ensure_dataset_manifest` and YAML `output_format` removal
2. checkpoint helpers (`prepare_sync_run`, metadata flush) on relative directories
3. Bluesky sync file paths
4. Twitter sync file paths
5. Reddit comments and posts file paths
6. Ingest tests green

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion tests/data_platform/utils/test_storage.py tests/data_platform/utils/test_dataset.py -q
```

Expected: exit 0.

## Must fail / not happen

- Reading `output_format` from ingest YAML.
- Writing `format` into a new `dataset.json`.
- Passing `storage.records_filename` or a stem that storage restems.
- Editing historical `dataset.json` files on disk.
- Adding a new ingest YAML key for file format or file name.
