# Step 5: Staging dry-run without upload

## Goal

Run the staging script so it finds the new public tree and emits a manifest whose keys match today’s bucket-root layout (no `webapp/` or `public/` prefix on keys). Stop before any production S3 write; if AWS credentials are missing, document that limitation and still prove path resolution.

## Caller / unit of work

**Main caller:** `stage_public_for_s3.py` invoked under the Step 3 frozen convention:

```bash
cd /Users/mark/src/work/mirrorView-task/webapp
PYTHONPATH=. uv run python scripts/upload_to_s3/stage_public_for_s3.py
```

**In scope:** Staging only; manifest key assertions; path-resolution proof if AWS blocks full stage.

**Out of scope:** `upload_public_to_s3.py`, `run_upload.sh` full pipeline, Terraform, docs.

## Prep references

- Phase 3 commands: [ROLLOUT_PLAN.md](../ROLLOUT_PLAN.md) § Phase 3
- Allowlist / critical keys: `webapp/scripts/upload_to_s3/constants.py` (`CRITICAL_S3_KEYS`, `ALLOWED_UPLOAD_KEYS`) — **do not edit key strings**
- CWD convention: Step 3 (CWD=`webapp/`, `SOURCE_PUBLIC_DIR=Path("public")`, staging under `webapp/s3_upload/`)

## Prerequisite

- Step 4 stimuli copy should already have placed `webapp/public/img/flips_scaled_2026_06_18.csv` (required for critical key presence).
- Full staging currently validates `config.js` against live API Gateway and may require AWS credentials.

## Files to inspect

| Path | Why |
|------|-----|
| `webapp/scripts/upload_to_s3/stage_public_for_s3.py` | Entry |
| `webapp/scripts/upload_to_s3/constants.py` | `SOURCE_PUBLIC_DIR`, key lists |
| `webapp/public/` | Source tree |
| `webapp/s3_upload/<timestamp>/manifest.json` | After successful stage |

## Files allowed to change

- Local only: contents under `webapp/s3_upload/` (generated staging artifacts; gitignored)
- No tracked source edits in this step unless Step 3 left a path bug — then fix only the path contract and re-run (do not expand scope)

## Files forbidden to change

- `CRITICAL_S3_KEYS` / `ALLOWED_UPLOAD_KEYS` values
- `webapp/public/config.js` URLs
- Production S3 objects (do not upload)
- Terraform state / apply

## Exact commands

```bash
cd /Users/mark/src/work/mirrorView-task

# Path-resolution proof (always required; no AWS needed)
python3 - <<'PY'
from pathlib import Path
p = Path("webapp/public")
assert p.is_dir(), p
assert (p / "config.js").is_file()
assert (p / "index.html").is_file()
csv = p / "img" / "flips_scaled_2026_06_18.csv"
assert csv.is_file() and csv.stat().st_size > 0, csv
print("OK path resolution", p.resolve())
PY

# Staging under frozen convention
cd webapp
PYTHONPATH=. uv run python scripts/upload_to_s3/stage_public_for_s3.py
# Expect exit 0 when AWS creds + API reachable
# If Unable to locate credentials / similar: see Fail table — still keep path proof above

# Inspect latest staging dir (CWD still webapp/)
ls -la s3_upload/
LATEST=$(ls -1d s3_upload/*T*Z | sort | tail -1)
echo "LATEST=$LATEST"
test -f "$LATEST/manifest.json"
test -f "$LATEST/index.html"
test -f "$LATEST/config.js"
test -f "$LATEST/img/flips_scaled_2026_06_18.csv"

python3 - <<'PY'
import json, pathlib
latest = sorted(pathlib.Path("s3_upload").glob("*T*Z"))[-1]
m = json.loads((latest / "manifest.json").read_text())
keys = m["files"]
assert "index.html" in keys
assert "config.js" in keys
assert "img/flips_scaled_2026_06_18.csv" in keys
assert not any(k.startswith("webapp/") for k in keys), keys
assert not any(k.startswith("public/") for k in keys), keys
print("OK: staged key count", len(keys), "bucket", m.get("bucket"))
print("sample keys:", keys[:5], "...", keys[-3:])
PY
cd ..
```

### Explicitly do not run

```bash
# GATED — mutates S3; forbidden in this step
bash webapp/scripts/upload_to_s3/run_upload.sh
cd webapp && PYTHONPATH=. uv run python scripts/upload_to_s3/upload_public_to_s3.py
```

## Pass / fail

### Pass (full)

1. Stage exits 0.
2. Manifest keys are bucket-root relative (assertions above).
3. Critical keys present including stimuli CSV.
4. No upload performed.

### Pass (credentials-blocked, still acceptable for merge gate)

1. Path-resolution proof printed `OK path resolution`.
2. Failure message is clearly credentials / AWS auth (e.g. `Unable to locate credentials`), **not** `Missing source directory: public`.
3. Document in the PR/commit notes: “Step 5 full stage blocked on AWS credentials; path resolution proven.”
4. Do **not** treat missing-directory errors as a credentials skip.

### Fail

| Symptom | Action |
|---------|--------|
| `Missing source directory: public` | Wrong CWD or Step 3 convention broken — fix before merge |
| `Missing allowlisted file ... img/flips_...` | Re-run Step 4 CSV copy |
| `config.js does not match deployed API URLs` | Restore URLs in config.js; do not change Terraform to match a wrong local URL |
| Manifest keys like `webapp/public/index.html` | **Hard fail** — fix staging relative paths; never upload |
| Upload was run | Treat as incident; do not continue; restore from prior release if objects changed |

## Rollback

Delete local `webapp/s3_upload/<timestamp>/` only. No S3 changes if upload was not run.

## Done when

Either full stage pass with bucket-root keys, or credentials-blocked pass with path-resolution proof documented; then proceed to Step 6.
