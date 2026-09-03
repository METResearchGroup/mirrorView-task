# Step 2: Write UTC date and hour zstd parquet

## Goal

Convert `data/raw/posts.csv` into Hive-style `date=<date>/hour=<hour>/{hash}.parquet` files. Every parquet file is zstd-compressed and under 50 MiB.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/data_dumps/bluesky/transform_raw_data_to_parquet.py` `main`, run as:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/transform_raw_data_to_parquet.py
```

**Slice:** read the CSV from step 1 → partition rows by UTC date and hour of `created_at` → write zstd parquet with content-hash names, splitting until each file is under 50 MiB.

**Out of scope:** Athena, summary stats, keyword sync, tests, Git LFS.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/data_dumps/bluesky/data/raw/posts.csv` | Input from step 1. Do not commit it. |
| `/tmp/lab_data_integrations_interface/bluesky_ingestion_jetstream/aws/constants.py` | Warehouse already uses zstd. Match that codec locally. |
| Step 1 `queries.py` | Column names in the CSV match the SELECT list. |

## Files allowed to change

- `/workspace/data_platform/ingestion/data_dumps/bluesky/transform_raw_data_to_parquet.py` (new)
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/parquet/` (runtime output; later committed in step 3)

Plan package files under `/workspace/docs/plans/2026-09-03_bluesky_jetstream_posts_dump_abfb8f/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/queries.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/athena.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/run_query.py`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

```text
RAW_CSV = Path(__file__).resolve().parent / "data" / "raw" / "posts.csv"
PARQUET_ROOT = Path(__file__).resolve().parent / "data" / "parquet"
MAX_FILE_BYTES = 50 * 1024 * 1024
PARQUET_COMPRESSION = "zstd"
PARQUET_COMPRESSION_LEVEL = 9
```

`main() -> int` reads `RAW_CSV`, writes under `PARQUET_ROOT`, prints the output root, returns 0.

Path layout (UTC, zero-padded hour):

```text
data_platform/ingestion/data_dumps/bluesky/data/parquet/date=YYYY-MM-DD/hour=HH/<sha256 hex>.parquet
```

`HH` is `00` through `23`. Date and hour come from `created_at` converted to UTC. Ingest time is not used for folders.

Rows whose `created_at` falls on a different UTC date than 2026-09-01 may still be written under their own `date=` folder. That is allowed.

Write with PyArrow:

```text
pyarrow.parquet.write_table(..., compression="zstd", compression_level=9)
```

Do not call `pandas.DataFrame.to_parquet` without an explicit zstd codec. Do not write snappy. Do not write uncompressed parquet.

After writing a candidate file, if `stat().st_size > MAX_FILE_BYTES`, split that hour's rows in half and write again until every file is `<= MAX_FILE_BYTES`. Then rename each file to `{sha256 of file bytes}.parquet`.

Keep post columns from the CSV. Parse `created_at` and `ingested_at` as UTC timestamps. Keep `langs` as a list of strings if Athena serialized an array; if it arrives as a string, store that string rather than inventing a parser beyond one obvious Athena array form.

Raise `FileNotFoundError` if `RAW_CSV` is missing. Do not call Athena.

## Implementation notes (implement-from-spec)

User waived tests. Skip Phase 4. Do not create files under `tests/`. Full auto on contracts. One Git commit per phase that changes the repo, and one commit per Phase 5 unit.

1. Phase 1 scope. Caller is `transform_raw_data_to_parquet.py` `main`.
2. Phase 2 scaffold. File exists with stub `main`. Commit.
3. Phase 3 contracts. Constants and signature locked. Body still stub. Commit.
4. Phase 4 skipped.
5. Phase 5 units, in this order, one commit each:
   1. Read CSV and group rows by UTC date and hour of `created_at`.
   2. Write zstd parquet (`compression="zstd"`, `compression_level=9`), split over 50 MiB, rename to sha256.
6. Phase 6. Run the must-pass commands. Confirm codec is ZSTD in parquet metadata. Confirm no test files.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/transform_raw_data_to_parquet.py
```

Expected: exit 0. Directories exist under `data_platform/ingestion/data_dumps/bluesky/data/parquet/date=2026-09-01/hour=00` through at least some hours in `00`–`23`. Filenames are hex plus `.parquet`.

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
import pyarrow.parquet as pq

root = Path("data_platform/ingestion/data_dumps/bluesky/data/parquet")
files = list(root.rglob("*.parquet"))
assert files, "no parquet files"
max_bytes = 50 * 1024 * 1024
total = 0
for path in files:
    size = path.stat().st_size
    total += size
    assert size <= max_bytes, (path, size)
    metadata = pq.read_metadata(path)
    for row_group_index in range(metadata.num_row_groups):
        row_group = metadata.row_group(row_group_index)
        for column_index in range(row_group.num_columns):
            codec = row_group.column(column_index).compression
            assert codec == "ZSTD", (path, codec)
print(f"files={len(files)} total_mib={total / 1024 / 1024:.1f}")
PY
```

Expected: exit 0. Every column codec is `ZSTD`. Every file size `<= 52428800`. Printed `total_mib` should be at or below the warehouse day's 1084.4 MiB, not an uncompressed blow-up.

## Must fail / not happen

- Any parquet file with codec `UNCOMPRESSED`, `SNAPPY`, `GZIP`, or `BROTLI`.
- Any parquet file larger than 50 MiB.
- Folders keyed on ingest time instead of creation time.
- Athena UNLOAD used to produce parquet.
- Files created under `/workspace/tests/`.
- Raw CSV committed.
