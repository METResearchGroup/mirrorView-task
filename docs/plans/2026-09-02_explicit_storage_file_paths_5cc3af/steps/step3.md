# Step 3: Switch preprocess callers and newly written source-run paths

## Goal

Preprocess loads raw records and writes preprocessed records through package-relative file paths. Newly written `source_raw_runs` / `source_raw_run` values are package-relative directory strings. All other preprocess metadata keys stay.

## Caller / unit of work

**Main caller:** `preprocess_records` in `/workspace/data_platform/preprocessing/runner.py`, used by `/workspace/data_platform/preprocessing/preprocess_bluesky.py`, `preprocess_twitter.py`, and `preprocess_reddit.py`.

**Slice:** load every raw run's `posts.csv` or `comments.csv`; write preprocessed records to a new run; persist metadata whose source-run list uses package-relative directories.

**Out of scope:** dropping preprocess metadata keys (issue #83). Keep `dataset_id`, `source_raw_run`, `source_raw_runs`, `preprocess_timestamp`, `row_counts`, and `files`.

## Decision (locked)

Replace `relative_run_path(dataset_root, run_dir)` with `to_package_relative` for newly written source-run lists. Do not keep a dual reader for the old `raw/{timestamp}` shape.

Load a raw file as `f"{to_package_relative(run_dir_path)}/{POSTS_FILENAME}"` or `COMMENTS_FILENAME` depending on the platform columns (`records_file_key` / platform). Bluesky and Twitter use `POSTS_FILENAME`. Reddit preprocess uses `COMMENTS_FILENAME` because Reddit storage defaults to comments.

If `create_new_run_dir` already returns a relative string, write with `f"{output_dir}/{POSTS_FILENAME}"` (or comments).

`load_records` no longer accepts a run directory. Tests that call `preprocessed_storage.load_records(output_dir)` must pass `f"{output_dir}/{POSTS_FILENAME}"` (or comments). `load_run_metadata(output_dir)` already takes the relative directory.

`DedupeSession.warm` takes the relative file path of the current preprocess output file, even if that file does not exist yet, plus `include_prior_runs` so prior preprocess runs are scanned by basename.

Keep the `files` map. Its value is the full file name (`posts.csv` or `comments.csv`), not a restemmed suffix.

Do not edit `/workspace/data_platform/preprocessing/preprocess_bluesky.py` unless it still constructs storage with `records_filename`. Prefer changing only `/workspace/data_platform/preprocessing/runner.py` plus tests. Platform entry files may need no edits.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/preprocessing/runner.py` | `load_raw_records`, `save_preprocessed`, `preprocess_records` |
| `/workspace/data_platform/utils/platform_specific_columns.py` | `records_file_key`, `records_id_column` |
| `/workspace/tests/data_platform/preprocessing/` | Assertions on `source_raw_runs` |

## Files allowed to change

- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/data_platform/preprocessing/preprocess_bluesky.py` (only if constructor or path calls still use the old API)
- `/workspace/data_platform/preprocessing/preprocess_twitter.py` (same)
- `/workspace/data_platform/preprocessing/preprocess_reddit.py` (same)
- `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py`
- Other files under `/workspace/tests/data_platform/preprocessing/` that fail on the new storage API

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/utils/dataset.py` (`relative_run_path` may still exist for curate/features until later steps)
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/generate_features/**`
- Historical preprocess `metadata.json` files on disk

## Contracts to lock

```text
load_raw_records(...) -> tuple[pd.DataFrame, list[str]]
  Second value is package-relative raw run directory strings, newest last if you sort by name.
  Skip a run when the records file does not exist (same as today's exists check).

save_preprocessed(...) -> str
  Returns the package-relative preprocess run directory.
  source_raw_runs: list of to_package_relative directories (or the strings already returned by load_raw_records).
  source_raw_run: last element of that list, or None.
  files[records_file_key]: POSTS_FILENAME or COMMENTS_FILENAME (full name including .csv).

Do not remove preprocess_timestamp, row_counts, or files.
```

Example newly written `source_raw_runs` entry:

```text
data/twitter/{dataset_id}/raw/2026_05_31-11:00:00
```

Not:

```text
raw/2026_05_31-11:00:00
```

## Test design

given two raw Twitter runs
when preprocess_records
then metadata["source_raw_runs"] has two package-relative directories under data/twitter/{id}/raw/
and metadata["source_raw_runs"][-1] == metadata["source_raw_run"]
and the old short string "raw/..." is not stored
and metadata still has preprocess_timestamp, row_counts, and files

given tests that write raw rows
when they call write_records
then they pass f"{run_dir}/{POSTS_FILENAME}" (Twitter/Bluesky) or COMMENTS_FILENAME (Reddit)

given tests that load preprocess output
then they call load_records(f"{output_dir}/{POSTS_FILENAME}") or comments

## Implementation notes

Follow implement-from-spec. Unattended.

Phase 5 units of work:

1. `load_raw_records` uses relative file paths and returns relative run dirs
2. `save_preprocessed` writes relative file paths and package-relative source-run lists
3. `preprocess_records` / dedupe warm path
4. Preprocess tests green

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing tests/data_platform/ingestion tests/data_platform/utils/test_storage.py -q
```

Expected: exit 0.

## Must fail / not happen

- Dropping `preprocess_timestamp`, `row_counts`, `files`, or `source_raw_run`.
- Writing source-run strings relative only to the dataset root.
- Rewriting historical preprocess metadata JSON.
- Using `storage.records_filename`.
