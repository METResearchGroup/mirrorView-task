# Step 1: Land the dump package and SELECT-only download

## Goal

Add a dump package that submits one SELECT of Jetstream posts for UTC 2026-09-01, waits for Athena, and downloads the workgroup CSV into a gitignored raw folder.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/data_dumps/bluesky/run_query.py` `main`, run as:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
```

**Slice:** build the posts SELECT → `Athena.run_query` → `Athena.get_output_location` → stream the result CSV to disk.

**Out of scope:** parquet transform, summary stats, keyword sync, UNLOAD, CREATE, tests.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/tmp/lab_data_integrations_interface/data_platform/aws/athena.py` | Copy source: wait loop, `get_output_location`. Do not copy `register_partition`. |
| `/tmp/lab_data_integrations_interface/bluesky_ingestion_jetstream/schemas/arrow_schemas.py` | Warehouse post schema has more columns; this dump selects only `uri`, `did`, `created_at`, `text`. |
| `/workspace/lib/aws/s3.py` | Existing boto3 S3 client pattern. Use `download_file` for the GB CSV; do not `get_bytes` the whole object. |
| `/workspace/.gitignore` | Already ignores `*.csv`. Still ignore the whole raw dump directory so Athena `.csv.metadata` cannot be committed. |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Must stay unchanged. |

## Files allowed to change

- `/workspace/data_platform/ingestion/data_dumps/bluesky/queries.py` (new)
- `/workspace/data_platform/ingestion/data_dumps/bluesky/athena.py` (new)
- `/workspace/data_platform/ingestion/data_dumps/bluesky/run_query.py` (new)
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/raw/` (runtime CSV only; gitignored)
- `/workspace/.gitignore`

Plan package files under `/workspace/docs/plans/2026-09-03_bluesky_jetstream_posts_dump_abfb8f/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/data/**`
- `/workspace/lib/aws/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Dump-folder constants (put database, workgroup, and SQL in `queries.py`; region default `us-east-2` on the Athena client):

```text
GLUE_DATABASE = "bluesky_raw"
ATHENA_WORKGROUP = "bluesky_raw_maintenance"
DAY_START = "2026-09-01 00:00:00 UTC"
DAY_END = "2026-09-02 00:00:00 UTC"
```

`queries.py` exposes one function:

```text
posts_for_utc_day_sql() -> str
```

Return exactly this statement (no trailing semicolon required):

```sql
SELECT
  uri,
  did,
  created_at,
  text
FROM posts
WHERE created_at >= TIMESTAMP '2026-09-01 00:00:00 UTC'
  AND created_at <  TIMESTAMP '2026-09-02 00:00:00 UTC'
```

Do not `SELECT *`. Do not filter on `ingested_at`. Do not query likes, reposts, or follows.

`athena.py` class `Athena`:

```text
__init__(self, region: str = "us-east-2") -> None
run_query(self, query: str, *, database: str, workgroup: str) -> str
get_output_location(self, execution_id: str) -> str
```

- `run_query` uses `boto3.client("athena", region_name=region)`, `start_query_execution` with `QueryExecutionContext={"Database": database}` and `WorkGroup=workgroup`, then polls `get_query_execution` every 1 second until `SUCCEEDED`, `FAILED`, or `CANCELLED`.
- On `FAILED` or `CANCELLED`, raise `RuntimeError` including the Athena `StateChangeReason`.
- Return the execution id on success.
- Before `start_query_execution`, reject the statement unless the first non-whitespace, non-`--` comment token is `SELECT` or `WITH`. Raise `ValueError` for `UNLOAD`, `CREATE`, `ALTER`, `DELETE`, `UPDATE`, `INSERT`, `MERGE`, `DROP`, `OPTIMIZE`, `VACUUM`, `EXPLAIN`, and any other non-SELECT verb.
- Do not copy `register_partition`, `fetch_column_as_set`, `fetch_rows`, or `query_column_as_set`.
- Do not default database or workgroup to `lab_data_integrations_interface` / `lab-data-integrations-interface`. Callers pass `bluesky_raw` and `bluesky_raw_maintenance`.

`run_query.py` `main() -> int`:

1. Call `posts_for_utc_day_sql()`.
2. `Athena().run_query(..., database=GLUE_DATABASE, workgroup=ATHENA_WORKGROUP)`.
3. `get_output_location` → parse `s3://<bucket>/<key>`.
4. `boto3.client("s3").download_file` into `/workspace/data_platform/ingestion/data_dumps/bluesky/data/raw/posts.csv`.
5. Print the local path and return 0.

Use the default boto3 credential chain. In the Cloud Agent environment, export `LAB_AWS_ACCESS_KEY_ID` / `LAB_AWS_ACCESS_KEY_SECRET` as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` before running. Do not pass keys in code.

`.gitignore` add:

```text
data_platform/ingestion/data_dumps/bluesky/data/raw/
```

## Implementation notes (implement-from-spec)

User waived tests. Skip Phase 4. Do not create files under `tests/`. Full auto on contracts. One Git commit per phase that changes the repo, and one commit per Phase 5 unit.

1. Phase 1 scope. Caller is `run_query.py` `main`. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Create the three Python files with imports and stub bodies (`raise NotImplementedError`). Create `data/raw/` as a runtime directory only. Add the gitignore line. Commit.
3. Phase 3 contracts. Lock signatures and the SQL string in `queries.py`. Bodies still stubs except the SQL return value may already be the exact SELECT (it is data, not control flow). SELECT-guard in `run_query` still stubbed. Commit.
4. Phase 4 skipped.
5. Phase 5 units, in this order, one commit each:
   1. SELECT-only guard in `Athena.run_query`.
   2. Athena wait loop and `get_output_location`.
   3. `run_query.py` `main` downloads the CSV to `data/raw/posts.csv`.
6. Phase 6. Run the must-pass commands. Confirm no files under `tests/`. Confirm `sync_bluesky.py` is unchanged.

## Must pass

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2
PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
```

Expected: exit 0. File exists at `data_platform/ingestion/data_dumps/bluesky/data/raw/posts.csv` and size is greater than 0. Athena execution state is `SUCCEEDED`.

```bash
cd /workspace
PYTHONPATH=. uv run python -c "from data_platform.ingestion.data_dumps.bluesky.athena import Athena; Athena().run_query('UNLOAD (SELECT 1) TO \'s3://example/\'', database='bluesky_raw', workgroup='bluesky_raw_maintenance')"
```

Expected: `ValueError` before `start_query_execution`. No new Athena execution for UNLOAD.

```bash
cd /workspace
git check-ignore -v data_platform/ingestion/data_dumps/bluesky/data/raw/posts.csv
```

Expected: the path is ignored via `data_platform/ingestion/data_dumps/bluesky/data/raw/`.

## Must fail / not happen

- Any file created under `/workspace/tests/`.
- `register_partition` or `ALTER TABLE` in `athena.py`.
- UNLOAD, CREATE, DELETE, UPDATE used to fetch posts.
- Query of likes, reposts, or follows.
- Filter on ingest time instead of creation time.
- `data_platform/ingestion/sync_bluesky.py` changed.
- CSV committed to git.
