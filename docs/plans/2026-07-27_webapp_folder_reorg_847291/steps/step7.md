# Step 7: Update operator and agent documentation

## Goal

Rewrite agent bootstrap, root README structure, deployment and stimuli runbooks, smoke README, and job-config comment pointers to the new local paths—without rewriting S3 keys, job source-of-record paths, or live API URLs. Follow the must-update set and order in the prep runbook doc.

## Caller / unit of work

**Main caller:** Next operator/agent reading `AGENTS.md` and runbooks after merge — they must serve `webapp/public`, not root `public/`.

**In scope:** Documentation and comment-only path rewrites listed as must-update in [RUNBOOK_UPDATES.md](../RUNBOOK_UPDATES.md).

**Out of scope:** Restoring `server-local.js`; changing S3 keys or API URLs; relocating more code; implementing real smoke tests.

## Path rewrite rule (local only)

Use [RUNBOOK_UPDATES.md](../RUNBOOK_UPDATES.md) as the exhaustive edit guide, with one correction vs that prep table:

| Prep table (stale) | Correct destination after FILES_MOVED |
|--------------------|----------------------------------------|
| `webapp/lambda-*.mjs` | `webapp/lambdas/lambda-*.mjs` |

All other From→To rows in RUNBOOK_UPDATES.md remain valid (`public/` → `webapp/public/`, `infra/` → `webapp/infra/`, upload/smoke under `webapp/`, etc.).

**Do not rewrite:**

- S3 / browser-relative keys: `img/flips_scaled_2026_06_18.csv`, `data/prolific/`, …
- Job SoT: `jobs/mirrorview_scaled_2026_06_18/flips.csv`
- YAML *values* under `jobs/config/` (only comments that cite app file paths)
- Live API URLs in `webapp/public/config.js`

## Must-update file list (execute in this order)

Exact change lists live in [RUNBOOK_UPDATES.md](../RUNBOOK_UPDATES.md) §§ Agent bootstrap + Per-document updates. Do not skip the must-update set:

1. `/Users/mark/src/work/mirrorView-task/AGENTS.md`
2. `/Users/mark/src/work/mirrorView-task/docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md`
3. `/Users/mark/src/work/mirrorView-task/docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md`
4. `/Users/mark/src/work/mirrorView-task/docs/runbooks/AWS_DEPLOYMENT_GUIDE.md`
5. `/Users/mark/src/work/mirrorView-task/jobs/config/mirrorview_default_2026_04_24.yaml` — **comments only**
6. `/Users/mark/src/work/mirrorView-task/webapp/public/main.js` — **comment path wording only**; do **not** change `postCatalogPath: 'img/flips_scaled_2026_06_18.csv'`
7. `/Users/mark/src/work/mirrorView-task/webapp/testing/smoke_tests/README.md`
8. `/Users/mark/src/work/mirrorView-task/README.md` — must-update structure tree; nice-to-have Quick Start align with AGENTS static serve

### Nice-to-have (optional in same commit if cheap)

- `jobs/config/mirrorview_scaled_2026_06_18.yaml` pointer comments
- `webapp/public/config.js` header clarity only

### Do not update (from RUNBOOK_UPDATES)

Historical plans under `docs/plans/**`, conceptual runbooks listed in “Docs that do not need path updates,” experiment READMEs citing job `flips.csv`.

## Files to inspect

| Path | Why |
|------|-----|
| [RUNBOOK_UPDATES.md](../RUNBOOK_UPDATES.md) | Exhaustive string tables |
| [FILES_MOVED.md](../FILES_MOVED.md) | Canonical destinations including `webapp/lambdas/` |
| Each must-update file above | Current stale root paths |

## Files allowed to change

Only the must-update (and optional nice-to-have) paths listed above. Prefer path-prefix rewrites; for README Quick Start, prefer pointing at:

```bash
python3 -m http.server 3000 --directory webapp/public
mkdir -p webapp/public/img && cp jobs/mirrorview_scaled_2026_06_18/flips.csv webapp/public/img/flips_scaled_2026_06_18.csv
```

rather than advertising broken `npm run dev`.

## Files forbidden to change

- `webapp/public/config.js` URL string values
- `postCatalogPath` / `stimuli.post_catalog_path` values (`img/...`)
- Upload allowlist key tuples
- Terraform resources / Lambda logic
- Prep packet historical content under older plan folders (leave as history)

## Exact verification commands

```bash
cd /Users/mark/src/work/mirrorView-task

# AGENTS must teach the new serve + copy paths
rg -n 'directory webapp/public|webapp/public/img/flips_scaled' AGENTS.md
# Expect hits for both serve and stimuli copy

# Stale root serve must be gone from AGENTS
rg -n -- '--directory public[^-]|mkdir -p public/img' AGENTS.md && echo "FAIL: stale AGENTS paths" || echo "OK: no stale AGENTS serve/copy"

# Lambda paths in docs should use lambdas/ folder
rg -n 'webapp/lambdas/lambda-get-post-assignments|webapp/lambdas/lambda-save-jspsych-data' \
  AGENTS.md README.md docs/runbooks jobs/config webapp/testing/smoke_tests/README.md

# Do not accidentally rewrite S3 key language into webapp-prefixed keys
rg -n 'webapp/public/img/flips_scaled_2026_06_18.csv' docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md
# Local path mentions OK; separately confirm S3 key still documented as img/flips_scaled_2026_06_18.csv:
rg -n 'S3|bucket|key' docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md | head -40
rg -n '`img/flips_scaled_2026_06_18.csv`' docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md

# Broader stale-root sweep (manual review of remaining hits)
rg -n '(`|/|^)public/|lambda-get-post-assignments\.mjs|scripts/upload_to_s3|infra/main\.tf|--directory public' \
  AGENTS.md README.md docs/runbooks jobs/config \
  --glob '!**/docs/plans/**'
# Remaining hits must be intentional: webapp/-prefixed paths, S3-relative img/..., or explicit historical notes
```

### Copy-paste AGENTS smoke (optional but preferred)

From a clean understanding of AGENTS.md, the documented serve + stimuli commands must match Step 4’s working commands.

## Pass / fail

### Pass

1. All must-update files rewritten per RUNBOOK_UPDATES (+ `webapp/lambdas/` correction).
2. `AGENTS.md` uses `--directory webapp/public` and CSV copy into `webapp/public/img/`.
3. No doc rewrote the **S3 key** `img/flips_scaled_2026_06_18.csv` into a `webapp/`-prefixed key.
4. Grep sweep: remaining root `public/` / root lambda hits are intentional or absent.
5. Upload docs reference `webapp/scripts/upload_to_s3/...` (Option A), not the old root path alone.

### Fail

1. Docs still say `python3 -m http.server ... --directory public`.
2. Docs still say `bash scripts/upload_to_s3/run_upload.sh` without `webapp/` after Option A move.
3. Lambda docs point at `webapp/lambda-*.mjs` (missing `lambdas/`) while code lives under `webapp/lambdas/`.
4. `postCatalogPath` or YAML `stimuli.post_catalog_path` values changed.
5. API URLs in config.js changed as part of “doc” work.

## Rollback

Revert the docs commit only; no prod impact.

## Done when

Must-update set is complete and verification greps pass. Mergeable reorg is complete without Step 8.
