# Step 1: Change storage and new dataset manifests

## Goal

Stop `StorageManager` from storing a records file name and from restemming that name from the dataset manifest. Load and write take one package-relative file path. Run-directory helpers return package-relative directory strings. New dataset manifests omit `format`. Tests isolate data by pointing `PACKAGE_ROOT` at a temporary directory.

## Caller / unit of work

**Main caller:** unit tests in `/workspace/tests/data_platform/utils/test_storage.py` and `/workspace/tests/data_platform/utils/test_dataset.py`.

**Slice:** construct a platform storage manager with no records file name; create a run directory; write and load records through a package-relative file path whose suffix chooses csv or parquet; write a new dataset manifest with no `format` key.

**Out of scope:** ingest, preprocess, curate, and feature-generation CLIs (later steps); slimming preprocess/raw/curated metadata keys; rewriting JSON already on disk; sibling issues #83 to #85.

## Decision (locked)

Load and write take a single package-relative file path string. They call `resolve_package_path` from `/workspace/data_platform/utils/paths.py`. Csv versus parquet is `Path(relative_file_path).suffix` (`.csv` or `.parquet`). Unsupported suffixes raise `ValueError`.

`create_new_run_dir` and `latest_run_dir` return package-relative directory strings via `to_package_relative`. They are the run-directory helpers named in the issue.

`root_dir` and `platform_data_root` stay `Path` values under `DATA_ROOT` so existing `.exists()` and `.iterdir()` checks keep working. They are stage roots, not run-directory helpers.

Do not keep `records_filename`, `self.format`, `filename_for`, `load_dataset_format`, or optional `filename=` fallbacks on load/write.

Do not add a new YAML key for ingest parquet. That belongs to step 2. This step only removes format from the manifest writer.

Import `METADATA_FILENAME` from `/workspace/data_platform/constants.py`. Delete the local `METADATA_FILENAME` copy in storage. Keep `DATA_ROOT` as a patchable module global, set at import to `PACKAGE_ROOT / "data"`.

Tests must patch `PACKAGE_ROOT` (on both `data_platform.constants` and `data_platform.utils.paths`) to `tmp_path`, and patch `DATA_ROOT` / `_DATA_ROOT` to `tmp_path / "data"`. Otherwise `to_package_relative` raises because the temp data dir is outside the real package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-02_explicit_storage_file_paths_5cc3af/plan.md` | Parent plan |
| `/workspace/data_platform/constants.py` | `PACKAGE_ROOT`, `POSTS_FILENAME`, `COMMENTS_FILENAME`, `METADATA_FILENAME` |
| `/workspace/data_platform/utils/paths.py` | `resolve_package_path`, `to_package_relative` |
| `/workspace/data_platform/utils/storage.py` | Current API to replace |
| `/workspace/data_platform/utils/dataset.py` | Manifest writer, `load_dataset_format`, `relative_run_path` |
| `/workspace/tests/data_platform/conftest.py` | `data_root` fixture |
| `/workspace/tests/data_platform/utils/test_paths.py` | Helper contracts this step must use, not reimplement |

## Files allowed to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/utils/dataset.py`
- `/workspace/data_platform/utils/deduplication.py`
- `/workspace/tests/data_platform/conftest.py`
- `/workspace/tests/data_platform/utils/conftest.py`
- `/workspace/tests/data_platform/utils/test_storage.py`
- `/workspace/tests/data_platform/utils/test_dataset.py`

## Files forbidden to change

- `/workspace/data_platform/constants.py`
- `/workspace/data_platform/utils/paths.py`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/generate_features/**`
- Any JSON already on disk under `data_platform/data/` or `experiments/`

## Contracts to lock

`/workspace/data_platform/utils/storage.py`:

```text
DATA_ROOT: Path
  PACKAGE_ROOT / "data" at import time. Tests patch this name.

class StorageManager:
  __init__(self, platform: str, stage: StorageStage, model: type[BaseModel], dataset_id: str) -> None
    No records_filename. No self.format. No self.records_filename.
    Still validates dataset_id.

  platform_data_root -> Path
  root_dir -> Path
    DATA_ROOT / platform / dataset_id / stage

  create_new_run_dir(self, timestamp: str | None = None) -> str
    Create DATA_ROOT / platform / dataset_id / stage / timestamp
    Return to_package_relative of that directory.

  latest_run_dir(self) -> str | None
    Newest timestamped child directory of root_dir, as to_package_relative.
    None if root_dir missing or has no child directories.

  write_records(self, rows: list[dict], relative_file_path: str) -> str
  append_records(self, rows: list[dict], relative_file_path: str) -> str
  write_dataframe(self, df: pd.DataFrame, relative_file_path: str) -> str
  load_records(self, relative_file_path: str) -> pd.DataFrame
    Resolve with resolve_package_path.
    .csv writes/reads csv. .parquet writes/reads parquet.
    Other suffixes raise ValueError.
    Return the same relative_file_path string from writers.

  load_seen_ids_from_disk(self, relative_file_path: str, id_column: str) -> set[str]
  load_seen_uris(self, relative_file_path: str) -> set[str]
    load_seen_ids_from_disk(..., "uri")

  load_seen_ids_from_all_runs(self, id_column: str, file_name: str) -> set[str]
    Union ids from root_dir / <run> / file_name for each child directory.
    Internally build package-relative file paths and call load_seen_ids_from_disk.

  append_deduped_records(self, rows, relative_file_path: str, *, dedupe_session: DedupeSession) -> AppendResult
    No filename kwarg. Use relative_file_path for append.

  write_run_metadata(self, relative_run_dir: str, metadata: dict) -> str
  write_run_metadata_atomic(self, relative_run_dir: str, metadata: dict) -> str
  load_run_metadata(self, relative_run_dir: str) -> dict
    Resolve the directory with resolve_package_path. Read/write METADATA_FILENAME from constants.
    Drop latest=True and run_dir: Path | None.

  all_runs_complete(self) -> bool
    Same completeness rules as today. load_run_metadata takes to_package_relative(path).

class BlueskyStorageManager(StorageManager):
  __init__(self, stage: StorageStage = StorageStage.RAW, dataset_id: str = "") -> None
    model SyncBlueskyPostModel. No records_filename.

class RedditStorageManager(StorageManager):
  __init__(self, stage: StorageStage = StorageStage.RAW, dataset_id: str = "", model: type[BaseModel] | None = None) -> None
    default model SyncRedditCommentModel. No records_filename.
  comment_storage(self) -> RedditStorageManager  # SyncRedditCommentModel
  post_storage(self) -> RedditStorageManager      # SyncRedditPostModel

class TwitterStorageManager(StorageManager):
  __init__(self, stage: StorageStage = StorageStage.RAW, dataset_id: str = "") -> None
    model SyncTwitterPostModel. No records_filename.
  load_records(self, relative_file_path: str) -> pd.DataFrame
    Same suffix dispatch as the base class. For csv, keep dtype={"tweet_id": "string", "author_id": "string"}.
  load_seen_tweet_ids(self, relative_file_path: str) -> set[str]
```

Delete `filename_for`. Delete `_resolve_run_dir`.

`/workspace/data_platform/utils/dataset.py`:

```text
write_dataset_manifest(platform, dataset_id, *, name: str, ingestion_config: str, created_at: str | None = None) -> Path
  Manifest keys: dataset_id, platform, name, created_at, ingestion_config
  No format key. No data_format parameter.

Delete load_dataset_format.
Keep ValidDataFormats only if storage still needs it. Prefer suffix checks in storage and delete ValidDataFormats when unused.
Keep relative_run_path until later steps migrate callers. Do not change its behavior in this step.
```

`/workspace/data_platform/utils/deduplication.py`:

```text
DedupeConfig.filename stays as an optional full file name (posts.csv), used only when warming prior runs by basename.
DedupeSession.warm(self, storage, relative_file_path: str) -> None
  load_seen_ids_from_disk(relative_file_path, id_column)
  if include_prior_runs: also load_seen_ids_from_all_runs(id_column, Path(relative_file_path).name)
```

`/workspace/tests/data_platform/conftest.py` `data_root`:

```text
root = tmp_path / "data"
monkeypatch.setattr(constants_mod, "PACKAGE_ROOT", tmp_path)
monkeypatch.setattr(paths_mod, "PACKAGE_ROOT", tmp_path)
monkeypatch.setattr(storage_mod, "DATA_ROOT", root)
monkeypatch.setattr(dataset_mod, "_DATA_ROOT", root)
return root
```

Import `data_platform.constants` and `data_platform.utils.paths` in that fixture file so both aliases are patched.

## Test design

Rewrite `/workspace/tests/data_platform/utils/test_storage.py` to the new API. Keep the existing behaviors (header once, dedupe, metadata atomic write, row validation). Add coverage for the new contracts.

given a BlueskyStorageManager for a dataset
when create_new_run_dir("2026_05_30-10:00:00")
then result is the POSIX string "data/bluesky/{dataset_id}/raw/2026_05_30-10:00:00"
and resolve_package_path(result) exists as a directory

given two run directories
when latest_run_dir()
then it returns the package-relative string of the lexicographically latest timestamp dir

given rows and relative path "data/bluesky/{id}/raw/{ts}/posts.csv"
when write_records then load_records
then the dataframe round-trips
and the file suffix is .csv

given the same rows and a .parquet relative path
when write_records then load_records
then the parquet file round-trips

given a relative path whose suffix is .json
when write_records
then raise ValueError

given append_records twice on the same .csv path
then the header is written once and both rows are present

given write_dataset_manifest without a format argument
when load_dataset_manifest
then the loaded dict has no "format" key
and still has dataset_id, platform, name, created_at, ingestion_config

Storage construction with a `records_filename` keyword must fail (TypeError). Do not keep a compatibility alias.

## Implementation notes

Follow implement-from-spec phases. Unattended / full auto. One Git commit per phase and per unit of work.

Phase 2: change signatures on `StorageManager` and subclasses to the contracts above. Method bodies that changed raise `NotImplementedError`. Keep `root_dir` working so tests can still create isolation directories if needed, or stub it too and let tests fail until Phase 5. Prefer stubbing the methods whose contracts changed.

Phase 3: freeze the signatures. No load/write logic yet.

Phase 4: rewrite failing tests.

Phase 5 units of work, in this order:

1. `data_root` fixture patches `PACKAGE_ROOT`
2. `write_dataset_manifest` omits `format`; delete `load_dataset_format`
3. Run-directory helpers return package-relative strings
4. write/load/append/dataframe suffix dispatch
5. metadata load/write against relative directories
6. seen-id helpers and `append_deduped_records`
7. Platform subclass constructors and Twitter csv dtypes

Use `POSTS_FILENAME` from constants in tests instead of the literal `"posts.csv"` when joining a run directory to a records file.

Numpy-style docstrings on changed public methods. Module docstring may include `PYTHONPATH=. uv run pytest tests/data_platform/utils/test_storage.py tests/data_platform/utils/test_dataset.py -q`.

Other packages under `tests/data_platform` will be red until later steps. Do not "fix" them in this step.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_storage.py tests/data_platform/utils/test_dataset.py tests/data_platform/utils/test_paths.py -q
```

Expected: exit 0.

## Must fail / not happen

- `StorageManager` storing `records_filename` or calling `load_dataset_format`.
- Load/write taking `run_dir: Path` plus optional `filename`.
- `create_new_run_dir` or `latest_run_dir` returning `Path`.
- New manifests containing `"format"`.
- Edits to ingest, preprocess, curate, or generate_features production files.
- Rewriting JSON already on disk.
- Reimplementing `resolve_package_path` or `to_package_relative`.
