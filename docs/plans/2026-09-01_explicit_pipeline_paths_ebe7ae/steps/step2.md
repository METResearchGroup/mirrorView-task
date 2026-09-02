# Step 2: Switch storage and all callers to explicit file paths

## Goal

`StorageManager` no longer infers a records file name or suffix. Every load/write takes a file path relative to `data_platform/`. Run-directory helpers return package-relative directory paths. Callers join those dirs with `POSTS_FILE`, `COMMENTS_FILE`, a feature spec filename, or a curation/ingest config filename. New dataset manifests omit `format`. Ingest configs stop using `output_format`. Newly written `source_*_runs` lists use package-relative directory strings. Metadata field *sets* other than those path strings stay as they are (slim in later steps).

## Caller / unit of work

**Main caller:** existing data-platform tests after storage and callers are updated.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: exit 0.

**In scope:** Storage API, dataset manifest writer, `relative_run_path`, ingest yaml + checkpoint manifest, feature spec filenames, curation `output.filename`, all production callers and tests that construct `StorageManager` or join records names.

**Out of scope:** Slimming preprocess metadata keys (Step 3); dropping raw `sync_timestamp` from metadata (Step 4); dropping curated `files` map and experiment `files.export` readers (Step 5); migrating historical JSON.

## Decision (locked)

- No `records_filename` on `StorageManager.__init__`. No subclass defaults. Delete `filename_for`. Delete restem via `load_dataset_format`.
- `create_new_run_dir` and `latest_run_dir` return a directory path relative to `data_platform/` (POSIX string or `Path` of `data/<platform>/<id>/<stage>/<ts>`). Internally mkdir under `resolve_package_path(...)`.
- Load/write/append/load-seen-ids take an explicit file path relative to `data_platform/`. CSV vs parquet is that path’s suffix (`.csv` / `.parquet`). Unknown suffix raises `ValueError`.
- Metadata I/O uses `METADATA_FILE` as sibling of the records file (join run dir with `METADATA_FILE`).
- `relative_run_path` becomes package-relative (implement via `to_package_relative`). Call sites that pass dataset root as the first argument must be updated.
- Ingest: remove `output_format` from yaml. `write_dataset_manifest` no longer takes or writes `format`. Parquet Bluesky configs set `records_file: posts.parquet`. All other ingest callers use `POSTS_FILE` or `COMMENTS_FILE`.
- Feature specs gain an explicit `filename` (e.g. `is_political.csv`). Registry keys stay logical names. Do not `f"{name}.csv"` inside storage.
- Curation yaml: `output.filename: mirrorview.csv` (and the same full name on the other platform yaml files). `OutputConfig.stem` is removed. This step still *writes* `files.export` using that filename so Step 5 can delete the map separately.
- Tests: `data_root` fixture monkeypatches `PACKAGE_ROOT` so `PACKAGE_ROOT / "data"` is the isolated data tree (keep pointing storage/dataset data roots at `tmp_path / "data"`).

## Files to inspect (read-only first)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py` | API to replace |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/dataset.py` | `relative_run_path`, `write_dataset_manifest`, `load_dataset_format` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/constants.py` | Step 1 constants |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/paths.py` | Step 1 helpers |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/conftest.py` | `data_root` monkeypatch |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_checkpoint.py` | Manifest + filename plumbing |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_bluesky.py` | `storage.records_filename` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_reddit.py` | Two files per run dir |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_twitter.py` | Twitter load dtypes |
| `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/runner.py` | Join run dir + records name |
| `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/generate_features.py` | Feature file path |
| `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/registry.py` | Every `FeatureSpec` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/models.py` | `FeatureSpec` fields |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/feature_labels.py` | `filename_for` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/curate/runner.py` | Glob + `filename_for` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/curate/apply_rules.py` | `OutputConfig.stem` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/configs/bluesky/mirrorview2.yaml` | `output_format: parquet` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/configs/bluesky/trump_econ_iran.yaml` | `output_format: parquet` |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/dataset.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/feature_labels.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/platform_specific_columns.py` (may keep `records_file_key` until Step 5 if still used as a log noun in preprocess; do not use it as a path)
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/**` (Python + yaml that declare `output_format`)
- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/runner.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/**` (models, registry, generate_features, platform_cli, metadata, tests’ FeatureSpec constructors)
- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/runner.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/apply_rules.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/configs/**/*.yaml`
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/**` (call sites of storage, FeatureSpec, `output.stem`, `records_filename`, `DATA_ROOT` / `_DATA_ROOT`)
- `/Users/mark/src/work/mirrorview-wt/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` (path/filename convention only; do not slim the preprocess metadata field list yet)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` (Step 5)
- `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py` (Step 5)
- Historical JSON under `experiments/**/data/**` and `data_platform/data/**`
- `/Users/mark/src/work/mirrorview-wt/lib/constants.py`

## Storage contract (replace)

Delete `records_filename` from `__init__` and subclasses. Delete `self.format` and the `load_dataset_format` call. Delete `filename_for`.

`BlueskyStorageManager.__init__(stage, dataset_id)` — no filename kwarg. Same for Twitter. Reddit: drop `records_filename` kwarg; keep `model=` for comments vs posts. `comment_storage()` / `post_storage()` still return two managers that differ by **model**, not by a stored filename. Callers pass `COMMENTS_FILE` vs `POSTS_FILE` at each I/O call.

`create_new_run_dir` return value is package-relative (e.g. `data/twitter/<id>/raw/2026_05_31-12:00:00`). `latest_run_dir` same or `None`.

`load_records(file_path)`, `write_records(rows, file_path)`, `append_records(rows, file_path)`, `write_dataframe(df, file_path)`, `load_seen_ids_from_disk(file_path, id_column)`: `file_path` is package-relative. Resolve with `resolve_package_path`. Branch on suffix.

`write_run_metadata(run_dir, metadata)` / `load_run_metadata(run_dir)`: `run_dir` is package-relative directory; metadata file is `run_dir / METADATA_FILE`.

Twitter `load_records` keeps `dtype={"tweet_id": "string", "author_id": "string"}` for `.csv`. If a Twitter path is `.parquet`, read parquet (no dtype dict required beyond pandas defaults) — Twitter ingest is csv-only today.

Remove `load_dataset_format` if nothing remains that calls it. `ValidDataFormats` may remain only if still referenced; do not use it to name files.

`write_dataset_manifest`: drop `data_format`. Written keys: `dataset_id`, `platform`, `name`, `ingestion_config`, `created_at`. Update `tests/data_platform/utils/test_dataset.py` so a new manifest has no `format` key.

## Ingest yaml

Replace `output_format: parquet` in:

- `data_platform/ingestion/configs/bluesky/mirrorview2.yaml`
- `data_platform/ingestion/configs/bluesky/trump_econ_iran.yaml`

with `records_file: posts.parquet`. Default configs with no key use `POSTS_FILE` / `COMMENTS_FILE` in Python. `ensure_dataset_manifest` must not read `output_format`.

## Feature filenames

Add `filename: str` to `FeatureSpec`. Registry entries (and every test `FeatureSpec(...)`) set it to `<name>.csv` written as a literal (`"is_political.csv"`), not composed at runtime in storage. `FeatureLabelQuery` takes the filename from the spec (or the caller passes the full file path). `generate_features.py` writes `features_dir` joined with `spec.filename` via `to_package_relative`.

`platform_cli.py` currently constructs `StorageManager(..., records_filename="features")` — that default file is unused for per-feature CSVs; stop passing it.

## Curation

`OutputConfig.filename: str` (required or default `"dataset.csv"`). Yaml:

```yaml
output:
  filename: mirrorview.csv
```

for every file under `data_platform/curate/configs/`. Writer still sets metadata `files.export` to that same string this step.

Preprocess glob: `preprocessed_storage.root_dir / "*" / POSTS_FILE` or `COMMENTS_FILE` from the platform spec’s records file constant — not `storage.records_filename`.

## Preprocess / features source lists

`relative_run_path` output examples: `data/twitter/<id>/raw/<ts>`. Update tests that assert `raw/<ts>` or `source_raw_runs[-1] == source_raw_run` (the equality may still hold). Do not remove `source_raw_run` or `files` from preprocess metadata in this step.

## Tests fixture

`tests/data_platform/conftest.py` `data_root`: monkeypatch `PACKAGE_ROOT` to `tmp_path`, and keep data at `tmp_path / "data"`. Patch every module that captured `DATA_ROOT` / `_DATA_ROOT` at import. `create_new_run_dir` return values are relative; tests that treated them as absolute `Path` for `/` joins must use `resolve_package_path` or `PACKAGE_ROOT / relative`.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Exit 0.

Assert in `test_write_and_load_dataset_manifest`: `"format" not in loaded`.

At least one storage test writes and reads a `.parquet` path without a dataset manifest.

At least one test shows `create_new_run_dir` return value `as_posix()` starts with `data/`.

## Must not happen

- `StorageManager` calls `load_dataset_format`.
- `filename_for` remains.
- Dual API (`records_filename=` still on `__init__`).
- Changing preprocess metadata keys other than `source_raw_runs` string shape.
- Editing experiment `files.export` readers (Step 5).
