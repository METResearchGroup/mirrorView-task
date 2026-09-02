# Step 3: Slim preprocess metadata

## Goal

New preprocess `metadata.json` documents contain only `dataset_id`, `source_raw_runs`, and `row_counts` (`input` / `output`). Drop `files`, `source_raw_run`, and `preprocess_timestamp`. Update preprocess tests and the preprocess section of the stimuli runbook. Do not migrate old JSON.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/runner.py` `save_preprocessed` → `write_run_metadata`.

Prove with:

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q
```

Expected: exit 0.

**In scope:** Preprocess writer, preprocess tests, runbook preprocess outputs list, preprocess log noun if it still uses `records_file_key` (print `POSTS_FILE` / `COMMENTS_FILE` instead).

**Out of scope:** Raw checkpoint metadata (Step 4); curated `files` map (Step 5); storage path API (Step 2, already landed).

## Decision (locked)

Exact keys for new preprocess metadata:

- `dataset_id`
- `source_raw_runs`: list of package-relative run dirs (`data/<platform>/<id>/raw/<ts>`), every raw directory that existed, not only dirs that contributed rows
- `row_counts.input` (after dedupe, before filters)
- `row_counts.output` (after filters)

No `files`, no `source_raw_run`, no `preprocess_timestamp`. Loaders still do not read metadata to find the records file.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/runner.py` | `save_preprocessed` metadata dict |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/preprocessing/test_preprocess_twitter.py` | Asserts `files.posts` and `source_raw_run` |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/preprocessing/test_preprocess_reddit.py` | Asserts `files.comments` |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/preprocessing/test_preprocess_bluesky.py` | Metadata assertions if present |
| `/Users/mark/src/work/mirrorview-wt/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` | Preprocess outputs list |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/runner.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/platform_specific_columns.py` (remove `records_file_key` if nothing else uses it after the log-noun switch)
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/preprocessing/**`
- `/Users/mark/src/work/mirrorview-wt/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` (preprocess outputs and column table rows for `records_file_key`)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/**`
- Historical `metadata.json` under experiments or `data_platform/data/`

## Implementation

In `save_preprocessed`, build only the locked keys. Delete `source_raw_run = source_raw_runs[-1]`. Print the records filename constant, not `records_file_key`.

Tests:

- `test_preprocess_records_merges_all_raw_runs_and_sets_source_raw_runs`: assert two package-relative raw dirs; **do not** assert `source_raw_run`.
- Replace `assert metadata["files"]["posts"] == "posts.csv"` (and comments equivalent) with `assert "files" not in metadata`.
- Assert metadata keys are exactly the locked set (or at least that the dropped keys are absent).
- `source_raw_runs` entries start with `data/` and include `/raw/`.

Runbook: replace the preprocess metadata bullet list with the locked three concerns. Remove `records_file_key` from the column table; say records files are `posts.csv` / `comments.csv` (or `posts.parquet` when the caller passed that name).

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing tests/data_platform/utils -q
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Exit 0.

## Must not happen

- Dual-key writer (`source_raw_run` still emitted).
- Reading metadata to locate `posts.csv`.
- Rewriting old preprocess JSON on disk.
