# Existing Migration Pattern (bluesky-research)

Source inspected:
[`METResearchGroup/bluesky-research` → `scripts/migrate_research_data_to_s3`](https://github.com/METResearchGroup/bluesky-research/tree/main/scripts/migrate_research_data_to_s3)
(main branch, sparse-cloned for analysis on 2026-07-20).

Purpose there: archive ~1-year-old Bluesky Nature paper (2024) research data from a large local data tree into S3 for long-term storage while pipeline work continues.

---

## 1. Overview

The migration is a **Python-only, two-phase, SQLite-tracked** workflow:

1. **Initialize (discover + register)** — walk local prefixes, map each file to an S3 key, insert rows into a local SQLite DB as `pending` (or `skipped` for empty files).
2. **Run (upload)** — query pending / in-progress rows per prefix, upload with **boto3** `upload_file` (multipart for large files), update row status to `completed` or `failed`.
3. **View (status)** — optional CLI to print per-prefix and overall checklist.

There is **no bash upload path**, **no AWS CLI**, and **no separate worker process / queue**. “Runner vs worker” is a **sequential script split** (init vs run vs view), not distributed workers.

Shared infra used by the runner (not defined inside the migration folder):

- `lib.aws.s3.S3` — bucket hard-coded as `bluesky-research`; client from `lib.aws.helper.create_client("s3")`.
- Credentials via `boto3.Session(profile_name=AWS_PROFILE_NAME from .env, region=us-east-2)`, with fallback to default credentials.
- Local data root: `lib.constants.root_local_data_directory` → `{repo_parent}/bluesky_research_data`.

---

## 2. Key files and responsibilities

| File | Role |
|------|------|
| `README.md` | Operator docs: steps, status lifecycle, S3 destination shape |
| `constants.py` | `PREFIXES_TO_MIGRATE` (explicit list of relative local dirs) + `DEFAULT_S3_ROOT_PREFIX` |
| `initialize_migration_tracker_db.py` | File discovery, S3 key generation, DB registration (idempotent inserts) |
| `migration_tracker.py` | SQLite schema + status API (`MigrationTracker`, `MigrationStatus`) |
| `run_migration.py` | Upload loop: mark started → boto3 upload → mark completed/failed |
| `view_migration_tracker_db.py` | Human-readable per-prefix status + overall checklist |
| `integration_prefixes.py` | Filter `PREFIXES_TO_MIGRATE` by integration name (for scoped backfills) |
| `requirements.in` / `.txt` | Only `tqdm` listed here; boto3 comes from the broader repo |
| `tests/` | Unit tests for init, tracker, run, and integration prefix filtering |

DB file location (local, next to scripts):

```text
scripts/migrate_research_data_to_s3/migration_tracker.db
```

S3 destination shape (from README + `constants.py`):

```text
s3://bluesky-research/{DEFAULT_S3_ROOT_PREFIX}/{relative_path_under_local_data_root}
# DEFAULT_S3_ROOT_PREFIX = "bluesky_research/2024_nature_paper_study_data"
```

---

## 3. End-to-end flow

```text
PREFIXES_TO_MIGRATE (constants)
        │
        ▼
initialize_migration_tracker_db.py
  - os.walk each local prefix under root_local_data_directory
  - (cache dirs: only keep partition_date=YYYY-MM-DD children)
  - special-case: collapse preprocessed_posts firehose+most_liked → one S3 layout
  - register_files() → SQLite UNIQUE(local_path); empty → skipped; else pending
        │
        ▼
migration_tracker.db
  rows: local_path, s3_key, file_size_bytes, status, timestamps, error_message
        │
        ▼
run_migration.py
  for each prefix:
    get_files_to_migrate_for_prefix()  # status IN (pending, in_progress)
    for each file:
      mark_started → migrate_file_to_s3 (boto3 upload_file) → completed | failed
        │
        ▼
view_migration_tracker_db.py  (optional)
  per-prefix counts + print_checklist()
```

### Operator commands (from README)

```bash
python initialize_migration_tracker_db.py   # discover + register
python view_migration_tracker_db.py         # optional status
python run_migration.py                     # upload all prefixes
```

`run_migration.py` also exposes `run_migration_for_prefixes(prefixes, ...)` for scoped runs (used with `integration_prefixes.prefixes_for_integrations`); the `__main__` path always runs all prefixes.

---

## 4. Patterns worth reusing (for mirrorView-task experiment artifact migration)

### 4.1 Explicit allowlist of roots/prefixes

Do not “migrate everything under experiments/.” Bluesky uses an **explicit list** in `constants.py`. For mirrorView, prefer an allowlist of experiment dirs / artifact globs (or a generated manifest from a prior inventory pass).

### 4.2 Two-phase: inventoy/register first, upload second

Separating discovery from upload makes dry-run of the *plan* easy (inspect DB / print counts) and keeps uploads resumable without re-walking the tree every time.

### 4.3 SQLite (or equivalent) as the migration manifest

Schema pattern from `migration_tracker.py`:

- `local_path` **UNIQUE** → idempotent registration
- `s3_key` stored up front (stable mapping)
- `file_size_bytes` at register time
- `status` CHECK-constrained enum: `pending | in_progress | completed | failed | skipped`
- indexes on `status`, `local_path`, `s3_key`, and `(status, local_path)`
- `error_message` + timestamps for debugging

Empty files → `skipped` (no pointless uploads).

### 4.4 Status-driven resume

- Mark `in_progress` **before** upload.
- On interrupt, re-run picks up `pending` **and** `in_progress` (assumes crash left files unfinished).
- Completed rows are never re-uploaded (unless you manually reset status).

### 4.5 Python + boto3 `upload_file` (not AWS CLI)

```python
# run_migration.py — conceptual
s3_client.client.upload_file(local_filepath, s3_client.bucket, s3_key, Callback=callback)
```

Benefits they rely on:

- multipart for files &gt; ~8MB
- streaming (not loading whole file into memory)
- botocore’s built-in retry behavior for the transfer
- progress callback for logging

Prefer this over shelling out to `aws s3 cp` for programmatic status updates and typed error handling.

### 4.6 Deterministic S3 key mapping

`get_s3_key_for_local_filepath`:

- require path under a known root
- `Path.relative_to(root)` → forward-slash string
- prepend a fixed archival root prefix

Special-case remapping when local layout should not be mirrored 1:1 (their `preprocessed_posts` collapse), with **hard-fail on S3 key collisions**.

### 4.7 Prefix-scoped processing + selective backfill

- Process by prefix for progress reporting and partial runs.
- `integration_prefixes.py`: map logical integration names → matching prefixes (`name` or `name/...`).

### 4.8 Clear error taxonomy in the upload function

`migrate_file_to_s3` returns `(ok, error_message)` and distinguishes:

- FS errors (`FileNotFoundError`, `OSError`) → fail row
- AWS `ClientError` → fail row with error code
- config/validation → fail row
- unexpected → log critical and **re-raise** (don’t silently swallow)

### 4.9 Status viewer separate from runner

Keep a read-only status script so operators can inspect without starting uploads.

### 4.10 Unit tests around tracker + upload mocking

Their tests mock boto3 / S3 client and assert status transitions, prefix LIKE queries, and collision/filter behavior — good model for a small migration package.

---

## 5. Patterns that may NOT apply / differences to watch for

| Bluesky pattern | Why it may not fit mirrorView-task |
|-----------------|-------------------------------------|
| Huge flat research data tree under `bluesky_research_data` with Hive-like `partition_date=` dirs | Experiments are many small trees under `experiments/*/outputs/**` with heterogeneous file types (csv, json, png, joblib, parquet, etc.) |
| Hard-coded bucket `bluesky-research` + repo `.env` AWS profile | Need mirrorView’s own bucket/prefix/credentials story; don’t assume their `lib.aws` package exists here |
| No dry-run flag | Worth adding for artifact migration (`--dry-run` that only prints planned keys / writes DB without upload) |
| README says failed files are retried on re-run | **Code gap:** `get_files_to_migrate_for_prefix` only selects `pending` and `in_progress`, **not** `failed`. Failed retries need an explicit reset-to-pending step (or query change) |
| No application-level retry loop around failed files | Relies on boto3 transfer retries + re-running; failed status sticks until manually fixed |
| Empty-file skip | Fine for data lakes; experiment artifacts that are intentionally empty markers may need different policy |
| Collapse / remapping of duplicate sources | Only needed if two local paths must share one S3 key; otherwise 1:1 relative paths are simpler |
| Sequential single-process upload | Fine for moderate volumes; large experiment trees might want concurrency with care around SQLite writes |
| “Runner vs worker” as separate processes | Not present — don’t over-engineer queues unless volume demands it |
| Prefix list as relative paths under one data root | Experiment migration may want repo-relative paths from `experiments/` and a richer exclude list (`.git`, `__pycache__`, huge raw dumps) |
| tqdm + project logger | Reusable; not required |

### Important README vs code mismatch (failed retries)

README claims:

> Query the database for pending and failed files  
> … files in `in_progress` or `failed` status will be retried

Actual query in `migration_tracker.get_files_to_migrate_for_prefix`:

```sql
WHERE status IN ('pending', 'in_progress') AND local_path LIKE ?
```

If reusing this design, either:

1. include `failed` in that query, or  
2. add `reset_failed_to_pending()`, or  
3. document that failed files require a manual SQL/status reset.

---

## 6. Concrete excerpts / pseudocode (by file)

### Config — `constants.py`

```python
PREFIXES_TO_MIGRATE = [
    "daily_superposters/cache",
    "feeds",
    # ... many ml_inference_*/{active,cache}, study_user_activity/..., etc.
    "user_session_logs/cache",
]
DEFAULT_S3_ROOT_PREFIX = "bluesky_research/2024_nature_paper_study_data"
```

### Discovery — `initialize_migration_tracker_db.py`

```python
def get_filepaths_for_local_prefix(local_prefix: str) -> list[str]:
    full = join(root_local_data_directory, local_prefix)
    for root, dirs, files in os.walk(full):
        # Under */cache: only descend into partition_date=YYYY-MM-DD
        if root == full and local_prefix.endswith("/cache"):
            dirs[:] = [d for d in dirs if is_valid_partition_date_dirname(d)]
        ...
```

S3 key:

```python
relative = Path(local_filepath).relative_to(root_local_data_directory)
s3_key = f"{s3_root_prefix}/{str(relative).replace(chr(92), '/')}"
```

Idempotent register (`migration_tracker.register_files`):

```python
INSERT INTO migration_files (local_path, s3_key, file_size_bytes, status)
VALUES (?, ?, ?, ?)
# IntegrityError on UNIQUE(local_path) → count as already registered
# file_size == 0 → status = skipped else pending
```

### Tracker schema — `migration_tracker.py`

```sql
CREATE TABLE IF NOT EXISTS migration_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  local_path TEXT NOT NULL UNIQUE,
  s3_key TEXT NOT NULL,
  file_size_bytes INTEGER,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending','in_progress','completed','failed','skipped')),
  started_at TEXT,
  completed_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Upload loop — `run_migration.py`

```python
files = tracker.get_files_to_migrate_for_prefix(prefix)  # pending + in_progress
for row in files:
    tracker.mark_started(row["local_path"])
    ok, err = migrate_file_to_s3(row["local_path"], row["s3_key"], s3)
    if ok:
        tracker.mark_completed(row["local_path"])
    else:
        tracker.mark_failed(row["local_path"], err)
```

S3 client wiring (`lib/aws/s3.py` + `lib/aws/helper.py`):

```python
ROOT_BUCKET = "bluesky-research"
class S3:
    def __init__(self, create_client_flag: bool = True):
        self.client = create_client("s3") if create_client_flag else None
        self.bucket = ROOT_BUCKET
# create_client → boto3.Session(profile_name=AWS_PROFILE_NAME, region_name="us-east-2")
```

### Scoped prefixes — `integration_prefixes.py`

```python
# Match PREFIXES_TO_MIGRATE entries equal to name or starting with "name/"
prefixes_for_integrations(["ml_inference_ime"]) 
# → ["ml_inference_ime/active", "ml_inference_ime/cache", ...]
```

---

## 7. Quick checklist for a mirrorView experiment-artifacts migration

Reuse:

- [ ] Explicit roots / globs allowlist  
- [ ] Phase 1: discover → write SQLite (or JSONL) manifest with planned `s3_key`  
- [ ] Phase 2: upload only non-completed rows; mark in_progress before upload  
- [ ] boto3 `upload_file` + structured error → failed row  
- [ ] Status viewer / summary counts  
- [ ] Collision detection if remapping paths  

Add / change vs bluesky:

- [ ] Dry-run mode  
- [ ] Explicit failed-retry policy (don’t copy the README/code mismatch)  
- [ ] Bucket + prefix + credentials config owned by mirrorView  
- [ ] Exclude lists suited to experiment trees  
- [ ] Decide whether empty / tiny sidecar files should skip or upload  

---

## Source map

| Concern | Primary file(s) |
|---------|-----------------|
| How files are discovered | `initialize_migration_tracker_db.py` (`os.walk`, partition filter, special collapse) |
| How uploads happen | `run_migration.py` → boto3 `upload_file` via `lib.aws.s3.S3` |
| Idempotency / status | `migration_tracker.py` SQLite UNIQUE + status machine |
| Runner vs “worker” | Init script vs run script (same process model; no queue workers) |
| Config | `constants.py` + `lib.constants` + `lib.aws.helper` / `S3.ROOT_BUCKET` |
| Dry-run / retries | No dry-run; boto3 transfer retries; failed-row app retry incomplete |
| Manifest | SQLite `migration_tracker.db` (not a separate JSON/CSV manifest) |
