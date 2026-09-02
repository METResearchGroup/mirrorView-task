# Step 4: Resume raw ingest from the run directory name

## Goal

New raw run metadata omits `sync_timestamp`. Resume stamps each ingested row’s `sync_timestamp` column from the run directory’s name (`output_dir.name`, the timestamp folder). Keep `row_count` and Reddit `post_row_count`. Do not migrate old metadata.

## Caller / unit of work

**Main caller:** ingest resume paths in `sync_twitter.py`, `sync_reddit.py`, and Bluesky task loops that stamp rows.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0.

**In scope:** `build_base_sync_metadata`, resume readers of `metadata["sync_timestamp"]`, tests that assert that key, any Bluesky path that copies metadata timestamp onto rows.

**Out of scope:** Renaming `row_count` to `row_counts`; preprocess/curated metadata; storage path API.

## Decision (locked)

- Drop `sync_timestamp` from new raw `metadata.json`.
- On resume (and on first run), row-level `sync_timestamp` is the run directory name. After Step 2, `output_dir` is package-relative; `.name` is still the timestamp folder (e.g. `2026_05_31-12:00:00`).
- Do not use `metadata["sync_timestamp"]`.
- `row_count` / `post_row_count` unchanged.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_checkpoint.py` | `build_base_sync_metadata` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_twitter.py` | `sync_timestamp = str(metadata["sync_timestamp"])` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_reddit.py` | same |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_bluesky.py` | How Bluesky stamps rows today |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/twitter_client.py` | Row builder takes `sync_timestamp` |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/ingestion/test_sync_checkpoint.py` | Metadata shape |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Resume |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Resume |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Resume |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_checkpoint.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_twitter.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_reddit.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_bluesky.py` (if it reads metadata for the stamp)
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/ingestion/**`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/models/sync.py` (row models still have a `sync_timestamp` **column**)
- Historical raw `metadata.json` on disk

## Implementation

Remove `"sync_timestamp": sync_timestamp` from `build_base_sync_metadata`. `init_metadata_fn` / `prepare_sync_run` still receive the timestamp to **create** the directory; they must not persist it in JSON.

Replace `str(metadata["sync_timestamp"])` with `Path(output_dir).name` (or the existing run-dir Path’s `.name`). Thread that string into row builders as today.

Tests: new metadata must not contain `sync_timestamp`. Resume tests still complete a second wave into the same run dir; row `sync_timestamp` values equal the run folder name. Do not add a reader that falls back to `metadata["sync_timestamp"]`.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Exit 0.

## Must not happen

- Dual-key (`sync_timestamp` still written “for compatibility”).
- Changing `row_count` field names.
- Using the full package-relative path as the row timestamp (must be the folder name only).
