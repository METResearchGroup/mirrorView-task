# Step 3: Summary stats and the parquet PR payload

## Goal

Compute dump summary statistics from the zstd parquet, write a small stats file, and commit parquet plus stats. Do not commit raw CSV.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/data_dumps/bluesky/summary_statistics.py` `main`, run as:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/summary_statistics.py
```

**Slice:** read all parquet under `data/parquet/` → compute four stats → write JSON → `git add` parquet and JSON only.

**Out of scope:** Athena, keyword sync, tests, Git LFS, `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/data_dumps/bluesky/data/parquet/` | Input from step 2. Confirm ZSTD before `git add`. |
| `/workspace/.gitignore` | Raw dir must still be ignored. `*.csv` already ignores CSV. |

## Files allowed to change

- `/workspace/data_platform/ingestion/data_dumps/bluesky/summary_statistics.py` (new)
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/summary_statistics.json` (new, committed)
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/parquet/**/*.parquet` (commit after codec check)

Plan package files under `/workspace/docs/plans/2026-09-03_bluesky_jetstream_posts_dump_abfb8f/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/queries.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/athena.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/run_query.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/transform_raw_data_to_parquet.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/raw/**` (must not be staged)
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

```text
PARQUET_ROOT = Path(__file__).resolve().parent / "data" / "parquet"
STATS_PATH = Path(__file__).resolve().parent / "data" / "summary_statistics.json"
```

`main() -> int` writes `STATS_PATH` and returns 0.

JSON object keys (exact):

```text
total_records
average_text_length
average_records_per_did
median_records_per_did
```

Definitions:

- `total_records`: row count across all parquet files.
- `average_text_length`: mean of `len(text)` treating missing text as empty string. Character length, not bytes.
- `average_records_per_did`: `total_records / number of distinct did`. Raise `ZeroDivisionError` if there are no DIDs.
- `median_records_per_did`: median of per-DID row counts (the middle value of the per-DID histogram). Use a true median, not `approx_percentile`.

Write JSON with `json.dump` and an indent of 2. Print `STATS_PATH` and the four values.

Live preview from the warehouse (step 3 should be in this neighborhood, not exact until the dump is local):

```text
total_records: 3450253
average_text_length: ~98.4
average_records_per_did: ~6.00
median_records_per_did: 2
```

Before `git add` of parquet, re-run the step 2 codec/size check. Stage only:

- `data_platform/ingestion/data_dumps/bluesky/*.py` already committed from earlier steps
- `data_platform/ingestion/data_dumps/bluesky/data/parquet/**/*.parquet`
- `data_platform/ingestion/data_dumps/bluesky/data/summary_statistics.json`

Do not stage `data/raw/`.

## Implementation notes (implement-from-spec)

User waived tests. Skip Phase 4. Do not create files under `tests/`. Full auto on contracts. One Git commit per phase that changes the repo, and one commit per Phase 5 unit.

1. Phase 1 scope. Caller is `summary_statistics.py` `main`.
2. Phase 2 scaffold. Stub `main`. Commit.
3. Phase 3 contracts. JSON keys locked. Body still stub. Commit.
4. Phase 4 skipped.
5. Phase 5 units, in this order, one commit each:
   1. Compute the four stats from parquet and write `summary_statistics.json`.
   2. Codec/size check, then `git add` parquet and JSON (not raw) and commit.
6. Phase 6. Run the must-pass commands. Confirm `git status` does not list `data/raw/posts.csv` as staged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/summary_statistics.py
```

Expected: exit 0. File `data_platform/ingestion/data_dumps/bluesky/data/summary_statistics.json` exists and contains the four keys. `total_records` is about 3450253. `median_records_per_did` is 2. Mean text length and mean posts per DID are near 98.4 and 6.00.

```bash
cd /workspace
git check-ignore -v data_platform/ingestion/data_dumps/bluesky/data/raw/posts.csv
git status --short data_platform/ingestion/data_dumps/bluesky/data/
```

Expected: raw CSV is ignored. `git status` shows parquet files and `summary_statistics.json` as added when staged. No `data/raw/` path staged.

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
import pyarrow.parquet as pq
root = Path("data_platform/ingestion/data_dumps/bluesky/data/parquet")
for path in root.rglob("*.parquet"):
    assert path.stat().st_size <= 50 * 1024 * 1024, path
    metadata = pq.read_metadata(path)
    for i in range(metadata.num_row_groups):
        rg = metadata.row_group(i)
        for j in range(rg.num_columns):
            assert rg.column(j).compression == "ZSTD", (path, rg.column(j).compression)
print("zstd ok")
PY
```

Expected: prints `zstd ok`.

## Must fail / not happen

- Raw CSV or Athena metadata staged or committed.
- Uncompressed or snappy parquet committed.
- Files created under `/workspace/tests/`.
- `CHANGELOG.md` edited.
- `data_platform/ingestion/sync_bluesky.py` changed.
