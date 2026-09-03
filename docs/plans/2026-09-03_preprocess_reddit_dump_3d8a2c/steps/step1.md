# Step 1: Promote dump parquet pointers into pipeline raw runs

## Goal

Copy the two month dump Git LFS pointers into completed Reddit raw runs for a new dump dataset. Write a dump YAML, a dataset manifest, and raw metadata so preprocess can load the comments as parquet.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/data_dumps/reddit/promote_to_raw.py` `main`, which reads the dump YAML and copies each source parquet pointer into the named raw run as `comments.parquet`.

**Task:** YAML → write parquet dataset manifest → copy each LFS pointer into `raw/{timestamp}/comments.parquet` → write completed raw metadata. Refuse to overwrite an existing destination parquet.

**Out of scope:** Preprocess sampling. Running preprocess on the million-row files. Bluesky dump files. Live PRAW Reddit ingest. Editing `data_platform/ingestion/data_dumps/reddit/README.md`. Editing `data_platform/preprocessing/README.md`. Editing `docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`. `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-03_preprocess_reddit_dump_3d8a2c/plan.md` | Parent plan |
| `/workspace/data_platform/ingestion/data_dumps/reddit/filtered/RC_2025-05.parquet` | May Git LFS pointer to copy |
| `/workspace/data_platform/ingestion/data_dumps/reddit/filtered/RC_2025-06.parquet` | June Git LFS pointer to copy |
| `/workspace/data_platform/ingestion/data_dumps/reddit/process_dump.py` | Dump directory constants. Do not change the processor |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | `ensure_dataset_manifest`, `require_dataset_id`, completed `sync_status` |
| `/workspace/data_platform/utils/dataset.py` | `write_dataset_manifest`, `ValidDataFormats.PARQUET` |
| `/workspace/data_platform/utils/storage.py` | `RedditStorageManager` reads format from `dataset.json` before choosing `comments.parquet` |
| `/workspace/data_platform/utils/config_paths.py` | `load_yaml_config`, `resolve_config_path`, `to_repo_relative` |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/.gitattributes` | Existing dump parquet LFS rules to extend |
| `/workspace/.gitignore` | `data_platform/data/` ignore that must gain an exception for this dataset |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | Live PRAW YAML folder. Dump YAML must not live there |
| `/workspace/tests/data_platform/conftest.py` | `data_root` fixture for isolated writes |

## Files allowed to change

- `/workspace/data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml`
- `/workspace/data_platform/ingestion/data_dumps/reddit/promote_to_raw.py`
- `/workspace/tests/data_platform/ingestion/test_promote_reddit_dump_to_raw.py`
- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/dataset.json`
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/2025_05_01-00:00:00/comments.parquet`
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/2025_05_01-00:00:00/metadata.json`
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/2025_06_01-00:00:00/comments.parquet`
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/2025_06_01-00:00:00/metadata.json`
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`

Plan package files under `/workspace/docs/plans/2026-09-03_preprocess_reddit_dump_3d8a2c/` may already be on this branch. Do not rewrite them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/data_dumps/reddit/README.md`
- `/workspace/data_platform/ingestion/data_dumps/reddit/process_dump.py`
- `/workspace/data_platform/ingestion/data_dumps/reddit/filtered/RC_2025-05.parquet`
- `/workspace/data_platform/ingestion/data_dumps/reddit/filtered/RC_2025-06.parquet`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/configs/reddit/**`
- `/workspace/data_platform/preprocessing/**` (step 2)
- `/workspace/data_platform/preprocessing/README.md`
- `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

Do not put this YAML under `/workspace/data_platform/ingestion/configs/reddit/`. That folder is the live PRAW ingest contract, and its tests require `limit_per_task`.

Write the dataset manifest before constructing `RedditStorageManager`, so `load_dataset_format` returns parquet and the records file is `comments.parquet`, not `comments.csv`.

Copy the Git LFS pointer file with `shutil.copy2`. Do not read the parquet into pandas. Do not call `write_records`. The destination file must be the same LFS oid as the source.

Raw run directory names are the dump months, not `get_current_timestamp()`. Use `2025_05_01-00:00:00` and `2025_06_01-00:00:00`.

## Contracts to lock

`/workspace/data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml`:

```yaml
dataset_id: reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079
name: reddit-pushshift-dump-2025-05-06
description: Promoted Pushshift dump comments for May and June 2025
output_format: parquet
record_types:
  - reddit.comment
sources:
  - parquet: data_platform/ingestion/data_dumps/reddit/filtered/RC_2025-05.parquet
    raw_run: "2025_05_01-00:00:00"
  - parquet: data_platform/ingestion/data_dumps/reddit/filtered/RC_2025-06.parquet
    raw_run: "2025_06_01-00:00:00"
preprocess:
  sample_size: 200000
  sample_seed: 20260903
```

`/workspace/data_platform/ingestion/data_dumps/reddit/promote_to_raw.py`:

```text
DUMP_DATASET_CONFIG = Path("data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml")

def promote_dump_sources_to_raw(config_path: Path, data_root: Path | None) -> Path
  Read the YAML.
  Validate dataset_id.
  Write dataset.json with output_format parquet and ingestion_config as the repo-relative YAML path.
  For each sources entry:
    Resolve parquet path from the repo root.
    Raise FileNotFoundError if the source parquet is missing.
    Create raw/{raw_run}/.
    Copy the source file to raw/{raw_run}/comments.parquet.
    Raise FileExistsError if that destination already exists.
    Write metadata.json with:
      dataset_id
      sync_status: completed
      ingestion_config: repo-relative YAML path
      source_dump_file: repo-relative source parquet path
  Return the dataset root.
```

`data_root` is for tests. Production `main` passes `None` and uses the package data root from `data_platform.utils.dataset.dataset_root`.

Do not invent a new timestamp helper. The raw run names come from YAML.

`.gitattributes` must add:

```text
data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/**/*.parquet filter=lfs diff=lfs merge=lfs -text
```

`.gitignore` must keep ignoring `data_platform/data/`, then un-ignore this dataset:

```text
!data_platform/data/reddit/
!data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/
!data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/**
```

After a successful promote of the real files, `git lfs ls-files` must show the two destination parquet files with the same oids as the dump filtered files:

- May oid `sha256:9c0adb4302728c7ef879f8b870978a0f25798ce67ce83f15c225723c4e726337`
- June oid `sha256:f8b5f27b2c470847809a51b8dd116b6b37087c947fc5bd5e17bdede7d6700540`

## Tests that must pass

In `/workspace/tests/data_platform/ingestion/test_promote_reddit_dump_to_raw.py`, using `data_root` and tiny source files (plain text is enough; do not need real parquet bytes):

1. Happy path: two sources copy to `comments.parquet` under the named raw runs, `dataset.json` has `format: parquet` and the repo-relative YAML path, each `metadata.json` has `sync_status: completed` and the matching `source_dump_file`.
2. Missing source file raises `FileNotFoundError` and writes neither destination parquet.
3. Existing destination parquet raises `FileExistsError` and does not overwrite the existing bytes.
4. Constructing `RedditStorageManager` for the promoted dataset after the manifest exists uses `comments.parquet`.

Run:

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_promote_reddit_dump_to_raw.py -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/promote_to_raw.py
```

Expected: writes the two raw run directories and `dataset.json` under `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/`. A second run fails because the destination parquet files already exist.

```bash
git lfs ls-files | rg "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw"
```

Expected: two parquet pointers whose oids match the dump filtered files.

## Architecture runbook

In `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`, add one short note that dump Reddit comments are promoted into `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/` from the dump YAML. Do not say to commit every dataset under `data_platform/data/`. Do not edit the agent-owned stimuli runbook.

## Pass / fail

Pass when the YAML exists, the promote CLI copies LFS pointers into completed raw runs, tests above are green, and the two real destination parquet files share oids with the dump filtered files.

Fail if the YAML is under `data_platform/ingestion/configs/reddit/`, if the destination is `comments.csv`, if pandas rewrites the parquet, or if a new LFS oid is created for the same bytes.
