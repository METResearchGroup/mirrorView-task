# Step 1: Copy dump LFS parquet into pipeline raw and add the dump YAML

## Goal

Copy the existing Bluesky dump parquet Git LFS pointers into a pipeline raw run for a new dump dataset. Write the dataset manifest, completed run metadata, and a preprocess YAML later stages can read. Track that dataset's parquet with Git LFS. Do not map warehouse columns yet. Do not run preprocess.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/data_dumps/bluesky/publish_dump_to_raw.py` `main`.

**Task:** copy dump parquet pointers into `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/2026_09_01-00:00:00/`, write `dataset.json` and `metadata.json`, and land the dump YAML plus git ignore and LFS rules.

**Out of scope:** Mapping dump columns onto `SyncBlueskyPostModel`. Changing preprocess load or sampling. Running preprocess. `git lfs pull` of the 24 hour files. Keyword Bluesky ingest. Reddit dump. Feature generation. Curation. `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/data_dumps/bluesky/data/parquet/` | Source hive layout `date=2026-09-01/hour=00..23/{hash}.parquet`. Files are Git LFS pointers |
| `/workspace/data_platform/ingestion/data_dumps/bluesky/data/summary_statistics.json` | `total_records` is 3450253 |
| `/workspace/.gitattributes` | Existing LFS rules for dump parquet |
| `/workspace/.gitignore` | `data_platform/data/` currently ignores all pipeline data |
| `/workspace/data_platform/utils/dataset.py` | `write_dataset_manifest`, `ValidDataFormats.PARQUET` |
| `/workspace/data_platform/utils/storage.py` | `BlueskyStorageManager`, `write_run_metadata`, `METADATA_FILENAME` |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | `ensure_dataset_manifest` pattern. Do not call keyword sync |
| `/workspace/data_platform/preprocessing/configs/` | Does not exist yet. Curate configs live under `data_platform/curate/configs/` |
| `/workspace/data_platform/ingestion/configs/bluesky/mirrorview2.yaml` | `output_format: parquet` example. Do not add dump YAML here |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | Every file under `data_platform/ingestion/configs/bluesky/` must have `limit_per_task` |
| `/workspace/tests/data_platform/conftest.py` | `data_root` fixture |

## Files allowed to change

- `/workspace/data_platform/ingestion/data_dumps/bluesky/publish_dump_to_raw.py` (new)
- `/workspace/data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml` (new)
- `/workspace/.gitignore`
- `/workspace/.gitattributes`
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/dataset.json` (new, written by the publisher)
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/2026_09_01-00:00:00/**` (copied LFS pointers plus `metadata.json`)
- `/workspace/tests/data_platform/ingestion/test_bluesky_dump_preprocess.py` (new)

Plan package files under `/workspace/docs/plans/2026-09-03_bluesky_dump_preprocess_c8e4b1/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/data_dumps/bluesky/transform_raw_data_to_parquet.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/run_query.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/athena.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/queries.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/summary_statistics.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/parquet/**`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/data_platform/preprocessing/preprocess_bluesky.py`
- `/workspace/data_platform/ingestion/configs/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

- Dataset id is `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73`.
- Raw run directory name is `2026_09_01-00:00:00`. Do not call `get_current_timestamp` for this run folder name.
- Copy files with `shutil.copy2`. Do not rewrite parquet bytes. Do not call `git lfs pull` in this step.
- YAML lives at `/workspace/data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml`, not under ingest configs.
- `ingestion_config` in `dataset.json` is the repo-relative YAML path with forward slashes.

## Contracts to lock

Add `/workspace/data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml` with exactly these keys:

```yaml
dataset_id: bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73
name: jetstream_utc_day_2026_09_01
description: One UTC day of Bluesky Jetstream posts from the lab warehouse dump
date: "2026-09-01"
output_format: parquet
record_types:
  - app.bsky.feed.post
dump:
  parquet_root: data_platform/ingestion/data_dumps/bluesky/data/parquet
  raw_run_timestamp: "2026_09_01-00:00:00"
preprocessing_params:
  sample_size: 200000
  sample_seed: 20260901
```

Add in `publish_dump_to_raw.py`:

```text
DUMP_DATASET_ID = "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"
DUMP_RAW_RUN_TIMESTAMP = "2026_09_01-00:00:00"
DUMP_PARQUET_ROOT = Path("data_platform/ingestion/data_dumps/bluesky/data/parquet")
DUMP_CONFIG_PATH = Path("data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml")

def publish_dump_to_raw(
    parquet_root: Path,
    dataset_id: str,
    raw_run_timestamp: str,
    config_path: Path,
) -> Path
```

Behavior:

- Resolve `parquet_root` relative to the repo root when it is relative.
- Raise `FileNotFoundError` when `parquet_root` is missing or contains no `*.parquet` files.
- Destination run dir is `BlueskyStorageManager(StorageStage.RAW, dataset_id).root_dir / raw_run_timestamp`.
- Raise `FileExistsError` when that run directory already exists.
- Copy every file under `parquet_root` whose suffix is `.parquet`, preserving relative `date=` / `hour=` folders.
- Call `write_dataset_manifest` with `name="jetstream_utc_day_2026_09_01"`, `ingestion_config=to_repo_relative(config_path, REPO_ROOT)`, `data_format=ValidDataFormats.PARQUET`.
- Write `metadata.json` with `dataset_id`, `sync_status="completed"`, `sync_timestamp=raw_run_timestamp`, `source="jetstream_dump"`, `source_parquet_root` as the repo-relative parquet root, `row_count=3450253`.
- Return the destination run directory.
- Numpy docstring. Module docstring includes `PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/publish_dump_to_raw.py`.

`.gitignore` change: replace the `data_platform/data/` ignore with:

```text
data_platform/data/**
!data_platform/data/bluesky/
!data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/
!data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**
```

`.gitattributes` add:

```text
data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**/*.parquet filter=lfs diff=lfs merge=lfs -text
```

After the publisher runs against the real dump folder, `git add` the copied pointers. Each copied parquet must keep the same LFS oid as its source file.

## Test design

New file `/workspace/tests/data_platform/ingestion/test_bluesky_dump_preprocess.py`. Use the `data_root` fixture. One test class per function.

```text
given a temp hive parquet tree with two hour files
when publish_dump_to_raw(parquet_root, DUMP_DATASET_ID, DUMP_RAW_RUN_TIMESTAMP, config_path)
then the destination run dir contains those relative parquet paths
and destination file bytes equal source file bytes
and dataset.json format is parquet
and dataset.json ingestion_config is the repo-relative config path
and metadata.json sync_status is completed
and metadata.json row_count is 3450253

given a destination run dir that already exists
when publish_dump_to_raw(...)
then raise FileExistsError
and do not copy additional files

given a missing parquet_root
when publish_dump_to_raw(...)
then raise FileNotFoundError

given an empty parquet_root directory
when publish_dump_to_raw(...)
then raise FileNotFoundError
```

The committed YAML test:

```text
given data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml
when loaded with yaml.safe_load
then dataset_id is bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73
and output_format is parquet
and dump.raw_run_timestamp is 2026_09_01-00:00:00
and preprocessing_params.sample_size is 200000
and preprocessing_params.sample_seed is 20260901
```

Tests must fail with `FileNotFoundError` / `NotImplementedError` until the publisher exists, then pass.

## Pass / fail

Pass:

- Publisher copies parquet files without changing bytes.
- YAML, `dataset.json`, and completed `metadata.json` exist.
- Copied dump pointers are on the branch and share LFS oids with `data_platform/ingestion/data_dumps/bluesky/data/parquet/`.
- `PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_bluesky_dump_preprocess.py -q` exits 0.
- `PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_ingest_yaml_keys.py -q` still exits 0.

Fail:

- Dump parquet under `data_platform/ingestion/data_dumps/bluesky/data/parquet/` is rewritten.
- YAML is added under `data_platform/ingestion/configs/`.
- Preprocess mapping or sampling is implemented in this step.
- Destination run uses `get_current_timestamp()` as the folder name.
