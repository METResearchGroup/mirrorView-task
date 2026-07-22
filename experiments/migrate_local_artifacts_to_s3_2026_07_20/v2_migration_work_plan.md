# V2: Migrate local experiment artifacts to S3

**Date:** 2026-07-20  
**Status:** Refined work plan (pre-spec)  
**Supersedes for design intent:** `init_migration_work_plan.md` (objectives/scope/layout kept; tooling shape revised)  
**Incorporates:** `EXSITING_MIGRATION_PATTERN.md` (Bluesky two-phase + SQLite lifecycle)  
**Inventory grounding:** `AFFECTED_FILES.md` (~239 csv/json, 9 experiment folders, ~86 MB)

**Bucket:** `mirrorview-experimental-artifacts`  
**Key convention:** repo-relative path, e.g. `experiments/{folder}/…/*.csv|json`

---

## 1. Design verdict (what changed from init → v2)

| Concern | Init plan | Bluesky pattern | **V2 decision** |
| --- | --- | --- | --- |
| Discovery vs upload | Separate Python scripts + JSON manifests | Two-phase: register then upload | **Two-phase**, SQLite is source of truth |
| Upload implementation | Python upload script (implied boto3/`aws`) | Pure boto3 `upload_file` in Python | **Bash `upload_to_s3.sh`** (AWS CLI) called by Python runner |
| Orchestration | `upload_artifacts.py` | `run_migration.py` | **`runner.py`** owns status transitions; shells out for bytes |
| Tracking | JSON/CSV manifests | SQLite status machine | **SQLite** (+ optional JSON export for humans/git) |
| Roots | Walk all of `experiments/` | Explicit prefix allowlist | **Allowlist of experiment folders** (default = the 9 with csv/json) |
| Resume | Resume-from-manifest (sketch) | `pending` + `in_progress` re-run | **Same**, with an **explicit failed-retry** policy (fix Bluesky README/code gap) |
| Dry-run | Inventory-only | Not present | **Required**: discover-only and upload dry-run |
| Verify | Separate verify script | Implicit via success | Keep **post-upload verify** (hash/size); can reuse patterns from `scripts/upload_to_s3/` |
| Scope | csv+json only; no delete | Large research archive | Unchanged: csv+json under allowlisted folders; no auto-delete |

**Non-negotiable for v1 tooling shape:** prefer the prescribed split below over Bluesky’s “all boto3 in Python,” while keeping Bluesky’s discovery → DB → status-driven resume model.

---

## 2. Objectives and scope (carried forward)

### Goal

Upload `*.csv` and `*.json` under allowlisted `experiments/{folder}/` trees into `s3://mirrorview-experimental-artifacts/` with path-preserving keys, so large/regenerable run outputs have a durable remote home.

### In scope (v1)

- Files: `*.csv` / `*.json` under allowlisted experiment folders (~239 today).
- Ops: discover → register → upload → verify → status/report.
- Idempotent re-runs and crash resume via SQLite.
- Experiment-local tooling under this folder (do not conflate with `scripts/upload_to_s3/` release flow).

### Out of scope (v1)

- Other types (`.png`, `.pkl`, `.parquet`, `.joblib`, `.npy`, models, …).
- Rewriting notebooks/scripts to read from S3 by default.
- Auto-deleting local copies after upload.
- Sharing keyspace with study/release buckets without an explicit prefix policy.

### Scale (why simple tooling is enough)

| Metric | Approx. |
| --- | ---: |
| csv + json | ~239 |
| Combined size | ~86 MB |
| Folders with artifacts | 9 |
| Largest files | ~5–10 MB |

Sequential AWS CLI uploads are fine; concurrency is optional later. Multipart is AWS CLI’s problem for the few larger CSVs.

---

## 3. S3 layout (unchanged from init)

```text
s3://mirrorview-experimental-artifacts/{repo-relative path}
```

Examples:

| Local | S3 key |
| --- | --- |
| `experiments/followup_model_error_analysis_2026_07_15/outputs/confusion_splits/false_positives.csv` | same path as key |
| `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv` | same |
| `experiments/predict_keep_remove_2026_07_01/keep_remove_results_2026_06_23.csv` | same |

Rules:

- No flattening, no content-hash renaming in v1.
- No `latest/` aliases / env prefixes unless later needed.
- S3 key = `Path.relative_to(repo_root)` with `/` separators.
- Hard-fail registration if two local paths map to the same `s3_key` (should not happen with 1:1 mirroring).

**Note:** timestamp dirs with `:` (e.g. `2026_06_17-14:50:48`) are valid S3 keys; bash must quote paths.

---

## 4. Resolved architecture: bash upload + Python lifecycle

### Responsibility split

```text
┌─────────────────────┐
│  file_discovery.py  │  Walk allowlisted roots → compute s3_key → INSERT SQLite
└──────────┬──────────┘
           │ migration_tracker.db
           ▼
┌─────────────────────┐
│     runner.py       │  Select rows by status → mark started → invoke bash →
│                     │  mark completed/failed → optional verify → status report
└──────────┬──────────┘
           │ subprocess per file (or small batch)
           ▼
┌─────────────────────┐
│  upload_to_s3.sh    │  aws s3 cp / sync one object; exit 0/non-zero
└─────────────────────┘
```

| Component | Language | Owns |
| --- | --- | --- |
| `file_discovery.py` | Python | Globs, excludes, size/mtime/sha256, s3_key mapping, idempotent DB register |
| `migration_tracker.py` (module) | Python | Schema, status API, queries (like Bluesky `MigrationTracker`) |
| `runner.py` | Python | CLI: `init` / `upload` / `status` / `retry-failed` / `verify`; calls bash; updates DB |
| `upload_to_s3.sh` | Bash | Single-object upload via AWS CLI (`aws s3 cp`); no DB awareness |
| `constants.py` | Python | Bucket name, allowlist, exclude globs, DB path, region default |
| Optional: `export_manifest.py` or `runner.py export` | Python | Dump completed rows → JSON under `manifests/` for audit/git |

### Why not Bluesky’s pure boto3?

- Matches the **prescribed** experiment tooling shape (bash for AWS bytes, Python for control plane).
- Aligns with existing repo comfort (`scripts/upload_to_s3/verify_s3_object_matches_local.sh` already uses AWS CLI).
- Keeps credentials/profile behavior identical to operator `aws` CLI usage.
- Volume is small; losing programmatic multipart callbacks is acceptable.

### Why not init’s JSON-only manifests?

- SQLite gives UNIQUE(local_path), indexed status queries, and crash-safe resume without re-parsing growing JSON.
- Optional JSON export remains for human review and for committing a snapshot after a successful full run.

### Supporting modules (recommended, thin)

- `migration_tracker.py` — schema + `register_files`, `mark_started|completed|failed`, `get_files_to_upload`, `reset_failed_to_pending`, `summary_counts`.
- `verify.py` or runner subcommand — compare local sha256/size to remote (head + optional download); patterns from `scripts/upload_to_s3/`.

Do **not** invent queue workers / separate long-running daemons. “Runner” here means the upload-phase orchestrator, same process model as Bluesky.

---

## 5. Recommended file layout

```text
experiments/migrate_local_artifacts_to_s3_2026_07_20/
├── init_migration_work_plan.md          # original proposal (keep)
├── EXSITING_MIGRATION_PATTERN.md        # Bluesky notes (keep)
├── AFFECTED_FILES.md                    # inventory snapshot (keep)
├── v2_migration_work_plan.md            # this document
├── README.md                            # operator how-to (after tooling exists)
├── constants.py                         # bucket, allowlist, excludes, paths
├── file_discovery.py                    # phase 1: discover + register
├── migration_tracker.py                 # SQLite API
├── runner.py                            # phase 2+ CLI orchestrator
├── upload_to_s3.sh                      # AWS CLI single-object upload
├── migration_tracker.db                 # local DB (gitignore)
├── inventory/                           # optional dry-run JSON dumps
│   └── artifacts_inventory.json
├── manifests/                           # optional exported completed snapshots
│   ├── pilot_manifest.json
│   └── full_upload_manifest.json
├── notes/
│   └── aws_setup.md                     # account/region/IAM crumbs
└── tests/                               # tracker + discovery unit tests; mock subprocess for runner
```

Keep implementation experiment-scoped until proven; only then consider promoting shared helpers.

---

## 6. SQLite schema sketch

```sql
CREATE TABLE IF NOT EXISTS migration_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  local_path TEXT NOT NULL UNIQUE,          -- repo-relative, POSIX separators
  s3_key TEXT NOT NULL,                    -- same as local_path for v1 1:1 mirror
  file_size_bytes INTEGER NOT NULL,
  sha256 TEXT,                             -- computed at register (or lazy on upload)
  mtime_ns INTEGER,                        -- optional drift detection
  experiment_prefix TEXT NOT NULL,         -- e.g. experiments/followup_...
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN (
      'pending','in_progress','completed','failed','skipped','verified'
    )),
  started_at TEXT,
  completed_at TEXT,
  verified_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_migration_status ON migration_files(status);
CREATE INDEX IF NOT EXISTS idx_migration_prefix ON migration_files(experiment_prefix);
CREATE INDEX IF NOT EXISTS idx_migration_status_prefix
  ON migration_files(status, experiment_prefix);
CREATE UNIQUE INDEX IF NOT EXISTS idx_migration_s3_key ON migration_files(s3_key);
```

### Status states

| Status | Meaning | Upload loop selects? |
| --- | --- | --- |
| `pending` | Registered, not yet uploaded | Yes |
| `in_progress` | Upload started; crash may leave this | Yes (resume) |
| `completed` | Bash upload exited 0 | No (unless force/reset) |
| `failed` | Bash non-zero or preflight error | No by default; use `retry-failed` |
| `skipped` | Empty file and/or exclude rule | No |
| `verified` | Optional: remote hash matched local | No |

**Failed-retry policy (explicit, unlike Bluesky):**

- Default upload query: `status IN ('pending', 'in_progress')`.
- `runner.py retry-failed` → set `failed` → `pending` (clear `error_message`), then operator re-runs upload.
- Do **not** silently include `failed` in the default loop (avoids hammering bad credentials / missing files).

**Empty files:** register as `skipped` (Bluesky default). Document if any intentional empty markers must upload (unlikely for this inventory).

**Re-registration (idempotency):**

- `INSERT … ON CONFLICT(local_path) DO NOTHING` (or count IntegrityError) for unchanged rows.
- Optional `--refresh-metadata`: update size/sha/mtime for existing non-completed rows; never auto-demote `completed` without `--force-reupload`.

**Local drift after completed:**

- If size/sha differs from DB for a `completed` row → flag in `status` report as `stale` (computed, not necessarily a DB status) and require `--force-reupload` to reset to `pending`.

---

## 7. Discovery rules (`file_discovery.py`)

### Allowlist (default)

Use an explicit list in `constants.py`, seeded from `AFFECTED_FILES.md` folders with artifacts:

```text
experiments/fetch_reddit_pushshift_dump_2026_06_15
experiments/followup_model_error_analysis_2026_07_15
experiments/mirrors_content_analysis_2026_04_24
experiments/model_errors_analysis_2026_07_15
experiments/predict_keep_remove_2026_05_07
experiments/predict_keep_remove_2026_07_01
experiments/scaled_mirrors_generation_2026_06_02
experiments/simplified_predict_remove_2026_05_13
experiments/truncate_posts_2026_06_19
```

Always exclude this migration folder itself and any `__pycache__` / `.git` noise.

### Selection

- Include: `**/*.csv`, `**/*.json` under each allowlisted prefix.
- Exclude (configurable): paths matching an exclude list / file (sensitive paths, committed tiny configs if we decide so later).
- Record: `local_path`, `s3_key`, `file_size_bytes`, `sha256`, `mtime_ns`, `experiment_prefix`.

### Outputs of phase 1

1. Rows in `migration_tracker.db`.
2. Optional `inventory/artifacts_inventory.json` (same fields) for review before any upload.
3. Printed summary counts per prefix.

Discovery is safe to re-run anytime (idempotent inserts).

---

## 8. Upload path (`runner.py` → `upload_to_s3.sh`)

### `upload_to_s3.sh` contract

```bash
# Usage (sketch):
#   bash upload_to_s3.sh --bucket NAME --key S3_KEY --local LOCAL_PATH [--region R] [--dry-run]
#
# Exit 0 on success (or dry-run print).
# Exit non-zero on aws failure; stderr should carry a short error for the runner to store.
```

Implementation sketch: `aws s3 cp "$local" "s3://$bucket/$key"` with quoted paths; optional `--only-show-errors`; no DB writes.

### Runner upload loop (per file)

1. `mark_started(local_path)` → `in_progress`.
2. Preflight: local file still exists and size matches registered (else `failed`).
3. Invoke `upload_to_s3.sh` via `subprocess.run` (capture stderr).
4. On exit 0 → `completed`; else → `failed` + `error_message`.
5. Optional `--verify`: after completed, check remote vs local; on success → `verified`; on mismatch → `failed` with verify error (or keep `completed` and set a verify flag—prefer fail-closed to `failed` for v1 simplicity).

### Dry-run modes

| Mode | Behavior |
| --- | --- |
| `file_discovery.py` / `runner.py init --dry-run` | Walk + print planned rows; **no DB writes** (or write to a temp DB) |
| `runner.py upload --dry-run` | Select pending/in_progress; print bash commands / planned keys; **no status changes**, **no aws** |
| `upload_to_s3.sh --dry-run` | Print the `aws s3 cp` line; exit 0 |

### Idempotency summary

- Register once per `local_path`.
- Completed never re-uploaded unless reset.
- Interrupted runs resume `pending` + `in_progress`.
- Failed requires explicit retry.
- Optional: skip upload if remote already exists with matching size/etag/sha (policy TBD—see open questions); if enabled, mark `completed` without rewriting bytes.

---

## 9. Operator CLI / ops flow

Recommended entrypoint: `runner.py` as the front door; discovery can also be invoked directly.

```bash
# From repo root (sketch)

# 0) One-time AWS: create private bucket, document in notes/aws_setup.md

# 1) Discover + register (safe; no uploads)
PYTHONPATH=. uv run python experiments/migrate_local_artifacts_to_s3_2026_07_20/runner.py init
# alias: file_discovery.py --write-db

# 2) Inspect plan
PYTHONPATH=. uv run python …/runner.py status
# review inventory/*.json if exported

# 3) Pilot: one mid-size prefix
PYTHONPATH=. uv run python …/runner.py upload \
  --prefix experiments/followup_model_error_analysis_2026_07_15 \
  --verify

# 4) Spot-check a few keys in console / aws s3 ls

# 5) Full upload
PYTHONPATH=. uv run python …/runner.py upload --verify

# 6) Retry failures after fixing root cause
PYTHONPATH=. uv run python …/runner.py retry-failed
PYTHONPATH=. uv run python …/runner.py upload --verify

# 7) Export human manifest
PYTHONPATH=. uv run python …/runner.py export --out manifests/full_upload_manifest.json
```

### Suggested rollout order (from init, kept)

1. Confirm AWS account/region/IAM.
2. Create bucket (private, SSE, block public access).
3. Dry-run discovery; sensitivity review.
4. Pilot one folder (`followup_model_error_analysis_2026_07_15` or `scaled_mirrors_generation_2026_06_02`).
5. Verify hashes/keys.
6. Full upload + export manifest.
7. Document consume path (`aws s3 cp` / sync folder back).
8. Separate decision: local retention / gitignore hygiene.

---

## 10. Tests (minimal but high value)

Mirror Bluesky’s test focus, adapted to the bash split:

- **Tracker:** status transitions, UNIQUE insert idempotency, prefix queries, `retry-failed`.
- **Discovery:** allowlist + glob + exclude; s3_key == relative path; empty → skipped; collision hard-fail.
- **Runner:** mock `subprocess` / stub `upload_to_s3.sh`; assert started→completed / started→failed; dry-run does not mutate.
- **Shell:** smoke test with `--dry-run` arg parsing (optional).

---

## 11. Tensions resolved (explicit)

1. **Upload stack:** Init implied Python upload; Bluesky used boto3; **v2 uses bash AWS CLI** for uploads and Python for discovery/status.
2. **Manifest format:** Init favored JSON manifests; Bluesky used SQLite; **v2 uses SQLite as SoT**, optional JSON export for audit.
3. **Discovery breadth:** Init “walk experiments/”; Bluesky allowlist; **v2 allowlist of 9 folders** (extensible in `constants.py`).
4. **Failed retries:** Bluesky README claimed failed retries but code did not; **v2 documents default exclusion + `retry-failed`**.
5. **Dry-run:** Bluesky lacked it; init wanted it; **v2 requires discover + upload dry-run**.
6. **Component names:** Prefer `file_discovery.py`, `runner.py`, `upload_to_s3.sh` over Bluesky’s `initialize_migration_tracker_db.py` / `run_migration.py` naming—same phases, different packaging.
7. **Verify:** Keep as first-class (init + existing repo verify scripts); Bluesky treated upload success as enough—**v2 prefers `--verify` on pilot/full runs**.

---

## 12. Open questions (still blocking or policy)

### Blocking before first real upload

- AWS account, region, IAM principal / profile name?
- Is `mirrorview-experimental-artifacts` available and aligned with org naming?
- Sensitivity review: any csv/json that must not leave the machine?

### Policy (can default, then confirm)

- Bucket versioning / lifecycle rules?
- Overwrite if remote exists but hash differs: overwrite vs fail-closed?
- Skip-if-remote-matches (size+sha) on re-run of reset rows?
- Exclude tiny committed JSON configs from upload?
- After success: keep local as cache, update `.gitignore` guidance, or optional prune (never auto in v1)?
- Store `sha256` as S3 metadata on upload for cheaper later verify?

### Non-blocking follow-ons

- Download helper / “local miss → fetch from S3”.
- Expand globs to parquet/pkl/png.
- Promote tooling next to `scripts/upload_to_s3/` if reused.

---

## 13. Risks (from init + tooling choices)

- Sensitive social/prediction artifacts in the wrong account or overly broad IAM.
- Colon-containing path segments: quote carefully in bash.
- Partial uploads without DB status → messy resume (SQLite mitigates).
- Runner/bash boundary: must capture stderr and map non-zero exits cleanly.
- Confusion with study/release buckets—document experiment bucket clearly in README.
- Drift if new large csv/json keep landing only locally with no re-init habit.

---

## 14. Next actions

1. Lock AWS context + sensitivity rules (open questions above).
2. Author `spec.md` from this v2 plan (separate agent / follow-on)—freeze CLI flags, schema, and shell contract.
3. Implement in order: `constants.py` → `migration_tracker.py` → `file_discovery.py` → `upload_to_s3.sh` → `runner.py` → tests.
4. Dry-run init → pilot upload → full upload → export manifest.

**Do not** treat this document as an implementation spec; it is the agreed design direction for that next spec.
