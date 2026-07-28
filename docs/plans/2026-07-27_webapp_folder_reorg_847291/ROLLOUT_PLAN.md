# Rollout plan: MirrorView web app → `webapp/`

**Date:** 2026-07-27  
**Status:** Prep only — do not implement until this plan is approved.  
**Goal:** Relocate the participant-facing website stack under `webapp/` with reversible, gated steps. Live S3 object keys and API Gateway URLs must remain unchanged.

## Non-negotiables

| Constraint | Detail |
|---|---|
| S3 keys unchanged | Upload allowlist still maps to bucket-root keys (`index.html`, `config.js`, `img/flips_scaled_2026_06_18.csv`, …). Only the *local* source tree moves. |
| Live API URLs unchanged | `POST_ASSIGNMENTS_URL` / `SAVE_DATA_URL` in `config.js` stay as-is (currently `https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/...`). |
| No dependence on `npm run dev` / `start` | Those scripts point at missing `server-local.js`. Verify with static serve only. |
| “Done” does **not** require `terraform apply` | Path-correct `terraform plan` + local/staging gates are enough to merge. Apply is explicitly optional and gated. |
| Prefer git-friendly moves | Use `git mv` so history follows; one commit (or stacked commits) per phase where practical. |

## Target layout (proposed)

```text
webapp/
  public/                 # was ./public/
  infra/                  # was ./infra/
  lambda-get-post-assignments.mjs
  lambda-save-jspsych-data.mjs
  package.json
  package-lock.json
  scripts/upload_to_s3/   # preferred; see decision note below
  testing/smoke_tests/    # preferred; stub only today
```

Repo root keeps Python/ML tooling (`pyproject.toml`, `scripts/` except upload, `jobs/`, `lib/`, `experiments/`, `docs/`).

### Decision: where `upload_to_s3` lives

Scripts today import as `scripts.upload_to_s3.*` and resolve paths relative to **repo-root CWD** (`SOURCE_PUBLIC_DIR = Path("public")`, `STAGING_ROOT = Path("s3_upload")`, `run_upload.sh` cds to repo root).

| Option | Pros | Cons |
|---|---|---|
| **A (preferred):** move under `webapp/scripts/upload_to_s3/` | Web stack co-located | Must fix imports / `PYTHONPATH` / `run_upload.sh` root detection; docs commands change |
| **B (safer minimal):** keep `scripts/upload_to_s3/` at repo root; set `SOURCE_PUBLIC_DIR = Path("webapp/public")` | Fewer Python packaging changes | Upload tooling remains outside `webapp/` |

Pick **A or B before Phase 1**. Plan text below assumes **A** with callouts for **B**.

---

## Preflight (before any move)

### Commands

```bash
cd /Users/mark/src/work/mirrorView-task
git status
git branch --show-current   # use a dedicated branch, e.g. chore/webapp-reorg

# Baseline inventory (paths that must move or be updated)
ls -la public lambda-*.mjs infra package.json package-lock.json
ls scripts/upload_to_s3 testing/smoke_tests

# Confirm broken npm scripts (expected)
grep -n server-local package.json README.md || true
test ! -f server-local.js && echo "OK: server-local.js absent"

# Capture current Terraform archive path shape (siblings of infra/)
rg -n 'file\("\$\{path\.module\}' infra/main.tf
```

### Pass

- Clean working tree (or only unrelated known untracked files).
- Dedicated branch checked out.
- Inventory matches expected roots: `public/`, two `lambda-*.mjs`, `infra/main.tf`, npm package files, upload scripts, smoke-test stub.

### Fail / abort

- Unexpected dirty changes in lambda/infra/public — stash or commit elsewhere first.
- Do not start the move on `main` without a branch.

### Rollback

No changes yet — nothing to roll back.

---

## Phase 1 — Move files + update path refs (no AWS apply)

**Intent:** Physical reorg + code/config path fixes so the tree is consistent. Do **not** run `terraform apply` or S3 upload.

### 1.1 Git moves

```bash
mkdir -p webapp
git mv public webapp/public
git mv infra webapp/infra
git mv lambda-get-post-assignments.mjs webapp/
git mv lambda-save-jspsych-data.mjs webapp/
git mv package.json package-lock.json webapp/

# Option A
mkdir -p webapp/scripts webapp/testing
git mv scripts/upload_to_s3 webapp/scripts/upload_to_s3
git mv testing/smoke_tests webapp/testing/smoke_tests

# Option B: skip the two git mv lines above; only edit SOURCE_PUBLIC_DIR later
```

### 1.2 Code / config path updates (checklist)

| File | Change |
|---|---|
| `webapp/infra/main.tf` | Keep `${path.module}/../lambda-*.mjs` **if** lambdas remain siblings of `infra/` under `webapp/` (no path change). If lambdas sit elsewhere, update `file(...)` accordingly. |
| `webapp/scripts/upload_to_s3/constants.py` (A) | `SOURCE_PUBLIC_DIR = Path("public")` only works if CWD is `webapp/`. Prefer repo-root–relative: `Path("webapp/public")` and keep `run_upload.sh` cd’ing to **repo root**, **or** document “run from `webapp/`”. Pick one convention and apply everywhere. |
| `scripts/upload_to_s3/constants.py` (B) | `SOURCE_PUBLIC_DIR = Path("webapp/public")`. |
| `webapp/scripts/upload_to_s3/run_upload.sh` (A) | Fix `REPO_ROOT` (`../..` from old location → likely `../../..` to repo root, or `..` if CWD is `webapp/`). Ensure `PYTHONPATH` still imports the package. |
| Import paths (A) | Today: `from scripts.upload_to_s3...`. After move, either (1) keep invoking via a thin wrapper at old path, (2) use `PYTHONPATH=webapp` + `from scripts.upload_to_s3...` under `webapp/`, or (3) rename package. Do not leave broken imports. |
| `.gitignore` | Update `public/img/...` → `webapp/public/img/...`; `infra/*.zip` → `webapp/infra/*.zip`. Keep `s3_upload/` at repo root (or document new location). |
| Docs / AGENTS / README / job YAML comments | Defer bulk edits to Phase 6, but fix any **executable** path that would break Phase 2–4. |

### 1.3 Sanity checks (no network required)

```bash
# Tree
test -d webapp/public && test -f webapp/infra/main.tf
test -f webapp/lambda-get-post-assignments.mjs
test -f webapp/lambda-save-jspsych-data.mjs
test ! -e public && test ! -e infra   # no leftover roots (important)

# Terraform path strings still resolve relative to module
rg -n 'lambda-.*\.mjs' webapp/infra/main.tf
# Expect: file("${path.module}/../lambda-....mjs")

# SOURCE_PUBLIC_DIR points at real tree
rg -n 'SOURCE_PUBLIC_DIR' webapp/scripts/upload_to_s3/constants.py   # or scripts/... for B
python3 -c "from pathlib import Path; p=Path('webapp/public'); assert p.is_dir(); assert (p/'config.js').is_file(); print('OK', p.resolve())"
```

### Pass

- `git status` shows renames (not delete+untracked add) for moved trees.
- No `./public` or `./infra` left at repo root.
- Terraform `file()` relative paths match actual lambda locations.
- `SOURCE_PUBLIC_DIR` resolves to `webapp/public` (or `public` under agreed CWD).
- Import / `run_upload.sh` convention documented in the commit message.

### Fail

- Leftover `public/` at root (agents/humans will serve the wrong tree).
- Terraform still points at `${path.module}/../lambda-...` but lambdas are not siblings.
- `SOURCE_PUBLIC_DIR` still `Path("public")` with CWD=repo root → staging will exit `Missing source directory: public`.
- Python `ModuleNotFoundError: scripts.upload_to_s3` after Option A without import fix.

### Rollback

```bash
git reset --hard HEAD   # if uncommitted
# or
git revert <phase1-commit>   # if committed
# or reverse git mv back to roots
```

Do not touch AWS.

---

## Phase 2 — Local static serve verification

**Intent:** Confirm the experiment still runs against **live** assignment API + **local** stimulus CSV, using the new directory.

### Commands

```bash
cd /Users/mark/src/work/mirrorView-task

# Stimuli (gitignored CSV; required for post-assignment mapping)
mkdir -p webapp/public/img
cp jobs/mirrorview_scaled_2026_06_18/flips.csv \
  webapp/public/img/flips_scaled_2026_06_18.csv
test -s webapp/public/img/flips_scaled_2026_06_18.csv && echo "OK: local catalog present"

# Static server — note path change vs AGENTS.md today
python3 -m http.server 3000 --directory webapp/public
# Open: http://localhost:3000/index.html?PROLIFIC_PID=TEST123
```

Browser / Network checks:

1. `config.js` loads; `POST_ASSIGNMENTS_URL` / `SAVE_DATA_URL` unchanged.
2. Assignment POST to live API Gateway succeeds (2xx).
3. Fetch of `img/flips_scaled_2026_06_18.csv` returns 200 from **local** server.
4. After political-affiliation step, no “Assignment Error” / “unknown post IDs”.
5. Moderation trials render.

Optional quick curl (server running):

```bash
curl -sI "http://localhost:3000/index.html" | head -1   # expect HTTP/1.0 200
curl -sI "http://localhost:3000/img/flips_scaled_2026_06_18.csv" | head -1
curl -s "http://localhost:3000/config.js" | rg "POST_ASSIGNMENTS_URL|SAVE_DATA_URL"
```

### Pass

- Local HTML/JS/CSS/CSV served from `webapp/public`.
- Live assignment call works; catalog maps IDs; core flow progresses past affiliation.
- Do **not** treat save-to-S3 completion as required for this gate.

### Fail

| Symptom | Likely cause |
|---|---|
| Serving empty / wrong site | Still using `--directory public` or leftover root `public/` |
| Assignment Error: unknown post IDs | Forgot CSV copy to `webapp/public/img/...` |
| CORS / network failure on assignment | Unrelated to move; check VPN/credentials not required for public API — confirm URL still production |
| 404 on `/img/...` | File not under `webapp/public/img/` |

### Rollback

Stop the server; revert Phase 1 if paths are wrong. Local CSV under `webapp/public/img/` is disposable (gitignored).

---

## Phase 3 — Staging / upload dry-run (prefer no upload)

**Intent:** Prove staging finds files at the new path and builds a manifest whose **keys** match today’s bucket-root layout. Prefer stopping before `upload_public_to_s3.py`.

### Prerequisite

- AWS credentials that can read API Gateway (staging validates `config.js` against live `jspsych-scroll-api`).
- Without credentials: skip AWS assertion by temporarily documenting limitation, or run only the path-resolution portion (see fail notes). Full staging script currently **requires** AWS.

### Commands (no upload)

```bash
cd /Users/mark/src/work/mirrorView-task

# Option A example (adjust if you standardized on webapp CWD)
PYTHONPATH=.  # or PYTHONPATH=webapp — match Phase 1 convention
uv run python webapp/scripts/upload_to_s3/stage_public_for_s3.py
# Option B:
# PYTHONPATH=. uv run python scripts/upload_to_s3/stage_public_for_s3.py

# Inspect latest staging dir
ls -la s3_upload/
LATEST=$(ls -1d s3_upload/*T*Z | sort | tail -1)
echo "LATEST=$LATEST"
test -f "$LATEST/manifest.json"
test -f "$LATEST/index.html"
test -f "$LATEST/config.js"
test -f "$LATEST/img/flips_scaled_2026_06_18.csv"

python3 - <<'PY'
import json, pathlib, os
latest = sorted(pathlib.Path("s3_upload").glob("*T*Z"))[-1]
m = json.loads((latest / "manifest.json").read_text())
keys = m["files"]
assert "index.html" in keys
assert "img/flips_scaled_2026_06_18.csv" in keys
assert not any(k.startswith("webapp/") for k in keys), keys
assert not any(k.startswith("public/") for k in keys), keys
print("OK: staged key count", len(keys), "bucket", m.get("bucket"))
print("sample keys:", keys[:5], "...", keys[-3:])
PY
```

**Do not run** unless explicitly approving a prod write:

```bash
# GATED — mutates S3
# bash webapp/scripts/upload_to_s3/run_upload.sh
```

### Pass

- Stage exits 0; `config.js` matches live API URLs.
- Manifest keys are bucket-root relative (no `webapp/` prefix).
- Critical keys from `CRITICAL_S3_KEYS` / `ALLOWED_UPLOAD_KEYS` are present, including stimuli CSV if present locally (or repo-root fallback still works if you rely on it).
- No upload performed for this gate.

### Fail

| Symptom | Likely cause / fix |
|---|---|
| `Missing source directory: public` | Wrong `SOURCE_PUBLIC_DIR` or wrong CWD |
| `Missing allowlisted file ... img/flips_...` | CSV not at `webapp/public/img/...` and no repo-root fallback |
| `config.js does not match deployed API URLs` | Accidental URL edit — **restore URLs**; do not “fix” by changing Terraform |
| `Unable to locate credentials` | Expected without AWS — do not treat as path-regression; defer this gate or obtain read-only creds |
| Manifest keys like `webapp/public/index.html` | Staging copied wrong relative paths — **hard fail**; fix before any upload |

### Rollback

Delete local `s3_upload/<timestamp>/` only. No S3 changes if upload was not run. If upload was run accidentally, restore prior objects from last known-good release / versioning (out of scope here — avoid upload in this phase).

---

## Phase 4 — `terraform plan` (path-only; credentials may be required)

**Intent:** Confirm archive `file()` paths pack lambdas correctly and plan shows **no unintended infra drift**. Prefer plan-only.

### Commands

```bash
cd /Users/mark/src/work/mirrorView-task/webapp/infra

# Optional: confirm zip inputs resolve before plan
python3 - <<'PY'
from pathlib import Path
mod = Path(".").resolve()
for name in ("lambda-get-post-assignments.mjs", "lambda-save-jspsych-data.mjs"):
    p = mod / ".." / name
    assert p.is_file(), p
    print("OK", p.resolve())
PY

terraform init -input=false   # if not already initialized; may need backend creds
terraform plan -input=false -no-color | tee /tmp/webapp-reorg-tf.plan.txt
```

Inspect plan for:

- Lambda `source_code_hash` / zip rebuild **only if** file contents changed (pure move should be content-identical → often no function code change, or hash refresh with identical source).
- **No** accidental replacement of API Gateway, custom domains, bucket destroy/recreate.
- No changes to route paths `/get-post-assignments`, `/save-jspsych-data`.

### Pass

- `terraform plan` completes (or fails only with a clear credentials/backend message — see below).
- With credentials: plan is empty **or** limited to expected hash/zip metadata with identical lambda source; no destroy of `aws_s3_bucket.site` / API.
- Without credentials: document blocker; path existence check above still passes. Phase 4 is then “blocked on creds,” not “failed reorg.”

### Fail

| Symptom | Action |
|---|---|
| `Invalid value for "path" ... file does not exist` | Broken `file("${path.module}/../lambda-...")` — fix paths; do not apply |
| Plan wants to replace API / bucket | Stop; compare state vs config; **do not apply** |
| Plan updates Lambda env that changes study behavior | Unrelated drift — review separately from reorg |

### Rollback

No apply → no cloud rollback. Fix paths locally; re-plan.

**Warn:** `terraform apply` is **not** part of this phase.

---

## Phase 5 — Optional `terraform apply` / prod smoke (explicitly gated)

**Not required for reorg “done.”** Run only with explicit human approval.

### Gate checklist (all must be true)

- [ ] Phases 1–3 passed; Phase 4 plan reviewed and understood.
- [ ] Someone acknowledges prod Lambda/API may refresh.
- [ ] Rollback owner identified (prior zip / previous commit known).

### Commands (gated)

```bash
cd /Users/mark/src/work/mirrorView-task/webapp/infra
terraform apply -input=false   # ONLY after plan review

# Optional: hit live assignment URL (same URL as config.js — must not change)
curl -sS -X POST \
  'https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments' \
  -H 'content-type: application/json' \
  -d '{"prolificId":"TEST_SMOKE","partyGroup":"democrat","studyId":"mirrorview","studyIterationId":"mirrorview_scaled_2026_06_18"}' \
  | head -c 500; echo
```

Smoke stub note: `webapp/testing/smoke_tests/` is still a stub (`LAMBDA_URL = ""`, `main` is `pass`). Do not treat `pytest` there as coverage. Prefer curl / browser against prod URLs already in `config.js`.

Browser: open the **deployed S3 website** (not only localhost) only if you also uploaded assets; a pure Terraform lambda apply does not require re-upload if `public/` bytes unchanged.

### Pass

- Apply succeeds; assignment endpoint still returns expected shape.
- `config.js` URLs still match API (re-run stage URL assertion if desired).
- S3 website keys unchanged if no upload.

### Fail / rollback

```bash
cd webapp/infra
# Prefer: redeploy previous lambda zip from prior git revision via terraform
git checkout <pre-reorg-sha> -- ../lambda-*.mjs   # careful; coordinate with tree layout
terraform apply
# Or revert the merge commit and apply from known-good tree
```

If apply changed only packaging paths with identical source, rollback is usually unnecessary.

---

## Phase 6 — Docs / runbook updates

**Intent:** Point humans and agents at `webapp/` without changing operational URLs/keys.

### Files to update (at minimum)

| Doc | What to change |
|---|---|
| `AGENTS.md` | `public/` → `webapp/public/`; lambda paths; static serve command; stimuli `cp` destination |
| `README.md` | Tree diagram; remove or clearly mark dead `server-local.js` / `main-local.js` |
| `docs/runbooks/AWS_DEPLOYMENT_GUIDE.md` | `public/` → `webapp/public/`; upload script paths; terraform working directory `webapp/infra` |
| `docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md` | Copy/verify paths under `webapp/public/img/` |
| `docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md` | Diagram + tables referencing `public/`, `infra/`, lambdas, upload scripts |
| `jobs/config/*.yaml` comments | Path pointers to `webapp/public/...`, `webapp/infra`, `webapp/lambda-*.mjs` |
| `webapp/testing/smoke_tests/README.md` | Updated file paths |

### Pass

- Grep for stale roots shows only intentional historical notes (or none):

```bash
rg -n '(^|[^/])public/|lambda-get-post-assignments|scripts/upload_to_s3|infra/main\.tf' \
  AGENTS.md README.md docs/runbooks jobs/config \
  --glob '!**/2026-07-27_webapp_folder_reorg_prep/**'
# Manually confirm remaining hits are updated or obsolete-by-design
```

- AGENTS.md local serve snippet uses `--directory webapp/public` and CSV copy into `webapp/public/img/`.

### Fail

- Docs still say `python3 -m http.server ... --directory public` → operators will miss the app.
- Upload docs still say `bash scripts/upload_to_s3/run_upload.sh` after Option A move without a wrapper.

### Rollback

Revert docs commit only; no prod impact.

---

## Suggested commit sequence (reversible)

1. `chore(webapp): move site stack under webapp/` — git mv only + path fixes (Phase 1).
2. `chore(webapp): update upload/terraform path refs` — if split from (1).
3. `docs(webapp): point runbooks and AGENTS at webapp/` — Phase 6.
4. Optional follow-up: gated apply notes in PR, not in “must merge” criteria.

Tag or note the pre-move SHA for easy revert.

---

## Risk register

| Risk | Why it hurts | Mitigation |
|---|---|---|
| Wrong `SOURCE_PUBLIC_DIR` | Stage/upload misses files or stages empty/wrong tree; worst case uploads incomplete site | Phase 3 manifest key assertions; never upload until keys look like today’s bucket root |
| Broken Terraform `file()` / zip paths | `terraform plan/apply` fails or packages empty/wrong lambda | Phase 1 sibling check; Phase 4 plan before any apply |
| Forgotten stimuli copy path | Local verify shows Assignment Error; operators copy to old `public/img/` | Phase 2 explicit `webapp/public/img/` copy; update AGENTS.md in Phase 6 |
| Leftover root `public/` | Silent dual trees; wrong server directory; confusing greps | Phase 1 pass criterion: `test ! -e public`; delete leftovers |
| Accidental S3 key prefix `webapp/` | Breaks production website paths | Manifest must not contain `webapp/`; allowlist stays basename/relative as today |
| Accidental API URL change in `config.js` | Clients hit wrong API | Phase 2/3 URL equality vs live API; treat URL edits as out of scope for reorg |
| Option A import / `PYTHONPATH` breakage | Upload tooling unusable | Decide CWD + package root in Phase 1; add one smoke stage command to CI notes |
| `.gitignore` still pointing at `public/` / `infra/*.zip` | Zips or large img dirs get committed or wrong paths ignored | Update ignore rules in same Phase 1 commit |
| Relying on `npm run dev` | False confidence / immediate failure | Explicitly out of verification path |

---

## Definition of done (mergeable without apply)

- [ ] Website stack lives under `webapp/`; no leftover root `public/` / `infra/` / root lambdas / root `package.json`.
- [ ] Path refs updated (`SOURCE_PUBLIC_DIR`, Terraform `file()`, upload runner, `.gitignore`).
- [ ] Phase 2 local static serve + stimuli copy succeeds.
- [ ] Phase 3 staging dry-run produces correct **bucket-root** keys (or documented AWS-cred skip with path-only proof).
- [ ] Phase 4: either clean/understood `terraform plan`, or path existence proven and plan blocked only on credentials.
- [ ] Phase 5 **not** required.
- [ ] Phase 6 docs/`AGENTS.md` updated so the next agent does not serve `./public`.

---

## Out of scope

- Fixing / restoring `server-local.js` and `npm run dev`.
- Changing S3 bucket name, API routes, study IDs, or stimulus catalog **filename**.
- Implementing real smoke tests under `testing/smoke_tests/`.
- Moving Python ML packages (`experiments/`, `lib/`, `jobs/`) into `webapp/`.
