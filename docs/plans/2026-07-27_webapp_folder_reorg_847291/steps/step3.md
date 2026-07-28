# Step 3: Repair local path contracts

## Goal

Update Terraform archive source paths for the new Lambda locations, standardize upload tooling on a single CWD / `PYTHONPATH` convention under the webapp unit, and retarget gitignore rules for the moved public and infra artifacts. Do not change S3 allowlist key shapes or live API URLs in site config.

## Caller / unit of work

**Main callers after this step:**

1. Terraform: `cd webapp/infra && terraform plan` (executed in Step 6)
2. Upload staging: `cd webapp && PYTHONPATH=. uv run python scripts/upload_to_s3/stage_public_for_s3.py` (executed in Step 5)

**In scope:** Mechanical path updates listed in [FILES_MOVED.md](../FILES_MOVED.md) § Mechanical path updates.

**Out of scope:** Docs/runbooks (Step 7); Terraform apply (Step 8); changing `ALLOWED_UPLOAD_KEYS` / `CRITICAL_S3_KEYS` string values; editing `webapp/public/config.js` URLs.

## Frozen convention (Option A) — do not invent alternatives

| Concern | Locked choice |
|---------|---------------|
| Upload CWD | Always `webapp/` |
| `PYTHONPATH` | `.` while CWD is `webapp/` |
| Package import | Keep `from scripts.upload_to_s3...` |
| Package init | Create `/Users/mark/src/work/mirrorView-task/webapp/scripts/__init__.py` (empty) if missing |
| `SOURCE_PUBLIC_DIR` | Keep `Path("public")` (resolves to `webapp/public` when CWD=`webapp/`) |
| `STAGING_ROOT` | Keep `Path("s3_upload")` → staging dir is `webapp/s3_upload/` |
| `run_upload.sh` root | `dirname/../..` from `webapp/scripts/upload_to_s3/` resolves to `webapp/` — update comments from “repository root” to “webapp root”; keep `cd` to that directory; keep `PYTHONPATH=. uv run python scripts/upload_to_s3/...` |
| Terraform lambdas | `file("${path.module}/../lambdas/lambda-get-post-assignments.mjs")` and same for save |
| S3 keys / allowlist | Unchanged string literals (`index.html`, `img/flips_scaled_2026_06_18.csv`, …) |
| API URLs in config.js | Unchanged |

## Files to inspect

| Path | What to verify |
|------|----------------|
| `webapp/infra/main.tf` | Current `file("${path.module}/../lambda-*.mjs")` lines |
| `webapp/scripts/upload_to_s3/constants.py` | `SOURCE_PUBLIC_DIR`, `STAGING_ROOT`, allowlist keys |
| `webapp/scripts/upload_to_s3/run_upload.sh` | REPO_ROOT / cd / PYTHONPATH / script paths |
| `webapp/scripts/upload_to_s3/stage_public_for_s3.py` | Import + missing-dir error uses `SOURCE_PUBLIC_DIR` |
| `webapp/scripts/upload_to_s3/upload_public_to_s3.py` | `from scripts.upload_to_s3...` |
| `webapp/scripts/upload_to_s3/verify_s3_upload.py` | Same import |
| `webapp/scripts/upload_to_s3/verify_s3_object_matches_local.sh` | Example `--local` path comments |
| `.gitignore` | `public/img/...`, `infra/*.zip`, `s3_upload/` |
| `webapp/public/config.js` | URLs must remain bit-identical to pre-move |

## Files allowed to change

| Path | Exact change |
|------|--------------|
| `webapp/infra/main.tf` | `../lambda-get-post-assignments.mjs` → `../lambdas/lambda-get-post-assignments.mjs`; same for save |
| `webapp/scripts/__init__.py` | Create empty if absent |
| `webapp/scripts/upload_to_s3/constants.py` | Keep `SOURCE_PUBLIC_DIR = Path("public")`; do not change allowlist key tuples |
| `webapp/scripts/upload_to_s3/run_upload.sh` | Comment + ensure cd target is webapp root; invocations stay `scripts/upload_to_s3/...` with `PYTHONPATH=.` |
| `webapp/scripts/upload_to_s3/stage_public_for_s3.py` | Only if error strings / comments still say repo-root `public/` incorrectly; imports stay `scripts.upload_to_s3` |
| `webapp/scripts/upload_to_s3/upload_public_to_s3.py` | Only if imports break (should not if PYTHONPATH=webapp) |
| `webapp/scripts/upload_to_s3/verify_s3_upload.py` | Same |
| `webapp/scripts/upload_to_s3/verify_s3_object_matches_local.sh` | Example `--local public/img/...` stays valid **relative to webapp CWD**; update any “repo root” wording |
| `.gitignore` | See Exact commands below |

## Files forbidden to change

- `webapp/public/config.js` — especially `POST_ASSIGNMENTS_URL` / `SAVE_DATA_URL`
- `CRITICAL_S3_KEYS` / `ALLOWED_UPLOAD_KEYS` values in `constants.py` (shape must stay bucket-root)
- `jobs/**`, `experiments/**`, `lib/**`, root `scripts/export_*`, `scripts/postprocess_*`
- Docs (`AGENTS.md`, runbooks, README) — Step 7
- `webapp/lambdas/*.mjs` source logic (path location already set in Step 2)
- AWS resources / Terraform apply

## Exact edits

### 1. Terraform archive paths

In `webapp/infra/main.tf`, change only the two `file(...)` path strings:

```hcl
# Before (broken after Step 2):
file("${path.module}/../lambda-get-post-assignments.mjs")
file("${path.module}/../lambda-save-jspsych-data.mjs")

# After:
file("${path.module}/../lambdas/lambda-get-post-assignments.mjs")
file("${path.module}/../lambdas/lambda-save-jspsych-data.mjs")
```

### 2. Upload package init + runner comments

```bash
# Create package marker if missing
test -f webapp/scripts/__init__.py || : > webapp/scripts/__init__.py
```

In `webapp/scripts/upload_to_s3/run_upload.sh`:

- Header comment: `Run from webapp root: bash scripts/upload_to_s3/run_upload.sh` (or `bash webapp/scripts/upload_to_s3/run_upload.sh` from repo root — both OK if script self-cds).
- Keep:

```bash
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
PYTHONPATH=. uv run python scripts/upload_to_s3/stage_public_for_s3.py
# ... upload + verify lines unchanged in structure
```

(`REPO_ROOT` here means webapp root after the move; rename variable to `WEBAPP_ROOT` only if you update every reference in that file — optional clarity, not required.)

### 3. `.gitignore`

Replace path prefixes (keep `s3_upload/` for legacy root staging if present; add webapp staging):

| Old line | New line |
|----------|----------|
| `public/img/large_datasets/` | `webapp/public/img/large_datasets/` |
| `public/img/raw_stimuli/` | `webapp/public/img/raw_stimuli/` |
| `infra/*.zip` | `webapp/infra/*.zip` |

Add (if not covered):

```gitignore
webapp/s3_upload/
webapp/public/img/flips_scaled_2026_06_18.csv
```

Only add the CSV ignore line if the repo previously relied on `*.csv` gitignore or an equivalent rule already covering it — do not weaken existing `*.csv` ignores. Confirm with:

```bash
rg -n 'csv|public/img|infra/\*\.zip|s3_upload' .gitignore
```

## Exact verification commands

```bash
cd /Users/mark/src/work/mirrorView-task

# Terraform paths resolve on disk
python3 - <<'PY'
from pathlib import Path
mod = Path("webapp/infra").resolve()
for name in ("lambda-get-post-assignments.mjs", "lambda-save-jspsych-data.mjs"):
    p = mod / ".." / "lambdas" / name
    assert p.is_file(), p
    print("OK", p.resolve())
PY

rg -n 'file\("\$\{path\.module\}' webapp/infra/main.tf
# Expect both lines to contain ../lambdas/lambda-

# SOURCE_PUBLIC_DIR still Path("public"); allowlist keys unchanged
rg -n 'SOURCE_PUBLIC_DIR|CRITICAL_S3_KEYS|img/flips_scaled' webapp/scripts/upload_to_s3/constants.py

# Import resolves with frozen CWD convention
cd webapp
PYTHONPATH=. uv run python -c "from scripts.upload_to_s3.constants import SOURCE_PUBLIC_DIR; assert SOURCE_PUBLIC_DIR == __import__('pathlib').Path('public'); assert SOURCE_PUBLIC_DIR.is_dir(); print('OK import + public dir', SOURCE_PUBLIC_DIR.resolve())"
cd ..

# config.js URLs unchanged
rg -n 'POST_ASSIGNMENTS_URL|SAVE_DATA_URL' webapp/public/config.js
# Expect:
#   https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments
#   https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/save-jspsych-data

# gitignore retargeted
rg -n 'webapp/public/img|webapp/infra/\*\.zip|webapp/s3_upload' .gitignore
test ! -e public  # still no leftover root public
```

### Expected outputs

- `OK /Users/mark/.../webapp/lambdas/lambda-....mjs` for both lambdas
- `rg` on main.tf shows `../lambdas/`
- `OK import + public dir .../webapp/public`
- config.js URLs match the two production URLs above
- `.gitignore` contains `webapp/`-prefixed public/infra rules

## Pass / fail

### Pass

1. Terraform `file()` paths resolve to real files under `webapp/lambdas/`.
2. `cd webapp && PYTHONPATH=.` imports `scripts.upload_to_s3` without `ModuleNotFoundError`.
3. `SOURCE_PUBLIC_DIR` is `Path("public")` and that directory exists when CWD=`webapp/`.
4. Allowlist key strings still bucket-root (no `webapp/` or `public/` prefix on keys).
5. `config.js` API URLs byte-identical to pre-reorg production URLs.
6. `.gitignore` no longer points only at root `public/` / `infra/*.zip` for those artifacts.

### Fail

1. Terraform still points at `${path.module}/../lambda-*.mjs` (missing `lambdas/`).
2. `SOURCE_PUBLIC_DIR = Path("public")` with documentation that says “run from repo root” — dual convention.
3. `ModuleNotFoundError: scripts.upload_to_s3` under the frozen CWD.
4. Any change to allowlist key strings or config.js URLs.
5. Docs rewritten in this step (defer to Step 7).

## Rollback

Revert Step 3 commit only (path edits). Tree layout from Step 2 can remain.

## Done when

Frozen convention is implemented and verification commands print OK; Step 4 (static serve) can proceed without further path surgery.
