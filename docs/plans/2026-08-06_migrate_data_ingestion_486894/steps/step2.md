# Step 2: Make local-disk sync pass the durability gate

## Goal

After a successful Twitter or Reddit sync that never uploads to S3, preprocess must not raise because `s3_upload_status` is false. Bluesky in this repository must default to local-only durability so a routine sync does not write to the shared lab S3 bucket unless the operator opts in.

## Caller / unit of work

**Main caller:** preprocess entry after a local sync. Shared gate is `data_platform.utils.gate_checks.require_all_runs_uploaded`, called from `data_platform.preprocessing.runner.preprocess_records`.

**In scope:** Mark successful local Twitter/Reddit sync runs as durable. Add an explicit opt-in for Bluesky S3 upload; default off; when off, skip upload and mark the run durable so the shared preprocess gate passes.

**Out of scope:** Parameterizing bucket names in `data_platform/aws/constants.py`; Prefect orchestration changes; sample script; live multi-keyword production sync; deleting lab cloud resources.

## Decision (locked)

1. Twitter and Reddit: on successful sync completion, write `s3_upload_status: true` into that run's `metadata.json` even though no S3 upload occurred (local disk is the durability store for these platforms in this repo).
2. Bluesky: introduce env opt-in `DATA_PLATFORM_BLUESKY_S3_UPLOAD` (string `"1"` / `"true"` enables upload). Default unset/false: skip S3 (and Athena registration if that is tied to the same completion path), still set `s3_upload_status: true` on successful local completion so preprocess can run.
3. Do not remove the gate function; keep it for the opt-in Bluesky cloud path and for `require_dataset_fully_uploaded` cleanup semantics.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt2/docs/plans/2026-08-06_migrate_data_ingestion_486894/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/utils/gate_checks.py` | Gate that raises |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/preprocessing/runner.py` | Calls gate before preprocess |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/sync_twitter.py` | Where sync completes / metadata written |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/sync_reddit.py` | Same for Reddit |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/sync_bluesky.py` | Where S3 upload happens today |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/utils/storage.py` | `all_runs_uploaded` / metadata helpers |
| Lab tests under `tests/data_platform/preprocessing/test_preprocess_*.py` | Expected metadata shape |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/sync_twitter.py`
- `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/sync_reddit.py`
- `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/sync_bluesky.py`
- `/Users/mark/src/work/mirrorview-wt2/lib/load_env_vars.py` (add `DATA_PLATFORM_BLUESKY_S3_UPLOAD` to allowlist if the sync reads it via `EnvVarsContainer`)
- Optional small helper under `/Users/mark/src/work/mirrorview-wt2/data_platform/utils/` only if needed to avoid duplicating the opt-in parse in three files (prefer one helper)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt2/data_platform/aws/constants.py` (no bucket rename in this step)
- `/Users/mark/src/work/mirrorview-wt2/data_platform/preprocessing/runner.py` (keep calling the gate; fix producers instead)
- `/Users/mark/src/work/mirrorview-wt2/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`
- `/Users/mark/src/work/mirrorview-wt2/webapp/**`
- `/Users/mark/src/work/lab_data_integrations_interface/**`

## Implementation requirements

### Twitter / Reddit

Locate the code path that marks a sync run `completed` (or equivalent final metadata write). Ensure final metadata includes `"s3_upload_status": true`.

If metadata is written incrementally, the **final** completed state must have the flag true before preprocess is expected to run.

### Bluesky

1. Read opt-in from env (via `EnvVarsContainer.get_env_var("DATA_PLATFORM_BLUESKY_S3_UPLOAD", required=False)` or `os.environ` if that file pattern is already local). Treat missing, empty, `"0"`, `"false"` (case-insensitive) as disabled. Treat `"1"` or `"true"` as enabled.
2. When disabled: do not call S3 upload / Athena registration on the completion path; still set `s3_upload_status` true on successful local completion.
3. When enabled: keep existing upload behavior, including setting the flag after a real upload.

Add a single clear log/print line when upload is skipped, e.g. that Bluesky S3 upload is disabled and the run is marked local-durable.

## Exact verification commands

Use a temp dataset id and fixture-style metadata write if a full API sync is unavailable. Prefer a unit-level check:

```bash
cd /Users/mark/src/work/mirrorview-wt2
PYTHONPATH=. uv run python - <<'PY'
"""Simulate Twitter raw metadata after sync completion semantics."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

# After implementation, import the helper or re-read sync completion writer.
# Minimal acceptance: gate passes when flag is true.
from data_platform.utils.storage import StorageManager, StorageStage
from data_platform.utils.gate_checks import require_all_runs_uploaded

# This block may need adjustment to match StorageManager constructors after inspect.
# Fail the step if you cannot construct a StorageManager pointing at a temp raw run
# with metadata s3_upload_status true and have require_all_runs_uploaded return without raise.
print("GATE_CONTRACT_CHECK_PLACEHOLDER")
PY
```

Replace the placeholder script during implementation with a concrete temp-dir test that:

1. Creates a raw run dir + `metadata.json` with `s3_upload_status: true` the way Twitter sync now writes it.
2. Calls `require_all_runs_uploaded` and does not raise.
3. Creates a second case with `s3_upload_status: false` and asserts `RuntimeError`.

Also assert Bluesky opt-in parsing:

```bash
PYTHONPATH=. uv run python - <<'PY'
# Import the helper added for Bluesky upload opt-in (exact name from implementation).
# Default (env unset): upload disabled.
# DATA_PLATFORM_BLUESKY_S3_UPLOAD=1: enabled.
print("BLUESKY_OPT_IN_OK")
PY
```

## Pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Twitter/Reddit completion metadata | Final completed run has `s3_upload_status: true` | Flag missing/false after successful sync path |
| Gate | `require_all_runs_uploaded` passes for local-durable metadata | Preprocess still raises for Twitter/Reddit-shaped runs |
| Bluesky default | Unset env skips S3 upload | Upload attempted with no opt-in |
| Bluesky opt-in | `DATA_PLATFORM_BLUESKY_S3_UPLOAD=1` keeps upload path | Opt-in ignored |

## Out of scope reminders

- Do not change sample discovery (Step 3).
- Do not port the full test suite here beyond what you need to prove the gate (Step 4 owns the suite).
- Do not rewrite `aws/constants.py` bucket names.
