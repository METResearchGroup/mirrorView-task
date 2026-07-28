# Runbook / docs updates for `webapp/` folder reorg

**Date:** 2026-07-27  
**Scope:** Documentation and path-comment updates only (not the reorg itself).  
**Assumption:** Website/app assets move under `webapp/` (`public/`, `lambda-*.mjs`, `infra/`, npm package files; likely `scripts/upload_to_s3/` and `testing/smoke_tests/`). Jobs/experiments/Python analysis stay at repo root. **S3 object keys and API Gateway URLs are unchanged** — only local repo paths change.

**Path rewrite rule (local only):**

| Old (repo root) | New |
|---|---|
| `public/...` | `webapp/public/...` |
| `lambda-*.mjs` | `webapp/lambda-*.mjs` |
| `infra/...` | `webapp/infra/...` |
| `package.json` / `package-lock.json` | `webapp/package.json` / `webapp/package-lock.json` |
| `scripts/upload_to_s3/...` | `webapp/scripts/upload_to_s3/...` *(if moved; confirm in reorg PR)* |
| `testing/smoke_tests/...` | `webapp/testing/smoke_tests/...` *(if moved; confirm in reorg PR)* |

**Do not rewrite:**

- S3 keys / browser-relative paths: `img/flips_scaled_2026_06_18.csv`, `data/prolific/`, etc.
- Job source-of-record: `jobs/mirrorview_scaled_2026_06_18/flips.csv`
- YAML study config under `jobs/config/` (file location stays; only *comments* that point at app files need path prefixes)
- Live API URLs in `config.js`

---

## Agent / dev bootstrap (`AGENTS.md`)

**Priority: must-update**

After reorg, Cursor Cloud / agent local-serve instructions must use `webapp/` paths. Suggested replacement block for “Running the web experiment locally”:

```markdown
1. **jsPsych web experiment** (`webapp/public/`, `webapp/lambda-*.mjs`, `webapp/infra/`) — ...
...
- Serve static assets, e.g.:
  `python3 -m http.server 3000 --directory webapp/public`
  then open `http://localhost:3000/index.html?PROLIFIC_PID=TEST123`.
- Live API Gateway URLs live in `webapp/public/config.js`.
- Local stimulus catalog:
  `mkdir -p webapp/public/img && cp jobs/mirrorview_scaled_2026_06_18/flips.csv webapp/public/img/flips_scaled_2026_06_18.csv`
- `npm install` / broken `npm run dev` refer to `webapp/package.json` (still points at missing `server-local.js`).
- If upload/smoke tooling moves: `webapp/scripts/upload_to_s3/*`, `webapp/testing/smoke_tests/`.
```

Old → new (critical strings):

| Old | New |
|---|---|
| `` `public/`, `lambda-*.mjs` `` | `` `webapp/public/`, `webapp/lambda-*.mjs` `` |
| `python3 -m http.server 3000 --directory public` | `python3 -m http.server 3000 --directory webapp/public` |
| `` `public/config.js` `` | `` `webapp/public/config.js` `` |
| `` `public/img/flips_scaled_2026_06_18.csv` `` | `` `webapp/public/img/flips_scaled_2026_06_18.csv` `` |
| `mkdir -p public/img && cp ... public/img/...` | `mkdir -p webapp/public/img && cp ... webapp/public/img/...` |
| `` `testing/smoke_tests/` `` | `` `webapp/testing/smoke_tests/` `` *(if moved)* |
| `` `scripts/upload_to_s3/*` `` | `` `webapp/scripts/upload_to_s3/*` `` *(if moved)* |

Also: note that `npm install` should run from `webapp/` (or document a root workspace script), and that `uv sync` / Python tooling remain at repo root.

---

## Per-document updates

### 1. `AGENTS.md`

- **Why:** Primary agent bootstrap; wrong serve/copy paths break local experiment immediately.
- **Change:** Entire “two loosely-coupled parts” + local-serve + stimuli copy + smoke/upload path mentions (see bootstrap section above).
- **Priority:** must-update

### 2. `docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md`

- **Why:** Step-by-step stimuli staging uses local `public/` and lambda file paths heavily.
- **Specific changes:**
  - Header “Browser fetch path”: `public/main.js` → `webapp/public/main.js` (keep `postCatalogPath` = `img/flips_scaled_2026_06_18.csv` unchanged).
  - Upload allowlist path: if `constants.py` moves → `webapp/scripts/upload_to_s3/constants.py`.
  - “Check `public/main.js`” → `webapp/public/main.js`.
  - “uploaded under `public/`” → `webapp/public/`.
  - `lambda-get-post-assignments.mjs` → `webapp/lambda-get-post-assignments.mjs`.
  - Preferred copy commands:
    - `mkdir -p public/img` → `mkdir -p webapp/public/img`
    - `cp ... public/img/flips_scaled_2026_06_18.csv` → `cp ... webapp/public/img/flips_scaled_2026_06_18.csv`
  - Fallback wording `` `public/<relpath>` `` → `` `webapp/public/<relpath>` ``.
  - Validation one-liner: `pd.read_csv('public/img/...')` → `pd.read_csv('webapp/public/img/...')`.
  - Verify script `--local public/img/...` → `--local webapp/public/img/...`.
  - `bash scripts/upload_to_s3/run_upload.sh` → `bash webapp/scripts/upload_to_s3/run_upload.sh` *(if moved)*.
- **Unchanged:** Job source `jobs/mirrorview_scaled_2026_06_18/flips.csv`; S3 key `img/flips_scaled_2026_06_18.csv`.
- **Priority:** must-update

### 3. `docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md`

- **Why:** End-to-end new-run checklist maps YAML → local app files; nearly every path is repo-root today.
- **Specific changes:**
  - Mermaid / flow: `public/img/` → `webapp/public/img/`; `public/config.js` → `webapp/public/config.js`; “upload public/” → “upload webapp/public/”.
  - Mapping tables: prefix all of `public/*.js`, `lambda-*.mjs`, `infra/main.tf` with `webapp/`.
  - Stimuli copy: `cp ... public/img/...` → `cp ... webapp/public/img/...`.
  - Redeploy table: same path prefixes.
  - Step 7/8 headings and commands: `public/config.js` → `webapp/public/config.js`; stage language “stages `public/`” → “stages `webapp/public/`”.
  - Checklist / appendix stimuli row: `public/img/flips_...` → `webapp/public/img/flips_...`.
  - `scripts/upload_to_s3/...` → `webapp/scripts/...` *(if moved)*.
  - Clarify: `stimuli.post_catalog_path` remains site-root-relative (`img/...`), not `webapp/public/...`.
- **Priority:** must-update

### 4. `docs/runbooks/AWS_DEPLOYMENT_GUIDE.md`

- **Why:** Deploy operators follow lambda / infra / public paths and upload commands from this guide.
- **Specific changes:**
  - Lambda source list: `lambda-*.mjs` → `webapp/lambda-*.mjs`.
  - `infra/main.tf` → `webapp/infra/main.tf` (and “cd” / terraform working dir if documented as `infra/`).
  - All `public/config.js`, `public/index.html`, `public/main.js`, “upload `public/`” → `webapp/public/...`.
  - Upload section commands: if toolchain moves under `webapp/`, rewrite `scripts/upload_to_s3/...` and `bash scripts/upload_to_s3/run_upload.sh` accordingly; if toolchain stays at repo root but reads `webapp/public/`, only document the new *source* tree (code change is separate).
  - Manual Lambda “use contents from `lambda-*.mjs`” → `webapp/lambda-*.mjs`.
- **Unchanged:** API names, stage URLs, S3 bucket key layout, “no sync deletes under `data/`”.
- **Priority:** must-update

### 5. `README.md` (repo root)

- **Why:** Project structure and customization still describe root-level `public/`, `lambda-*.mjs`, `server-local.js`.
- **Specific changes:**
  - Tree: nest web assets under `webapp/` (`webapp/public/`, `webapp/lambda-*.mjs`, `webapp/infra/`, `webapp/package.json`).
  - Customization bullets: `public/main.js` → `webapp/public/main.js`, etc.; `lambda-get-post-assignments.mjs` → `webapp/lambda-...`.
  - Doc links: `AWS_DEPLOYMENT_GUIDE.md` → `docs/runbooks/AWS_DEPLOYMENT_GUIDE.md` *(nice-to-have path fix; already wrong relative to root)*.
- **Nice-to-have / cleanup:** Quick Start still advertises broken `npm run dev` / `index-local.html`. Prefer aligning with `AGENTS.md` (static `http.server` on `webapp/public`) rather than only prefixing broken paths. Call out that root README is stale vs production layout.
- **Priority:** must-update for path tree; nice-to-have to rewrite Quick Start to match AGENTS bootstrap

### 6. `testing/smoke_tests/README.md`

- **Why:** Lists core files by path; file itself may move under `webapp/`.
- **Specific changes:**
  - `lambda-get-post-assignments.mjs` → `webapp/lambda-get-post-assignments.mjs` (or relative `../lambda-...` if README lives under `webapp/testing/smoke_tests/`).
  - `public/main.js` → `webapp/public/main.js` (or `../../public/main.js` if co-located under `webapp/`).
- Prefer absolute-from-repo-root paths for consistency with other runbooks.
- **Priority:** must-update *(if smoke tests move or stay and still reference old paths)*

### 7. `jobs/config/mirrorview_default_2026_04_24.yaml` (header comments)

- **Why:** Comment block lists hardcoded sources with repo-root paths; YAML values themselves do not encode local `public/` paths.
- **Specific changes (comments only):**
  - `public/config.js` → `webapp/public/config.js`
  - `public/main.js` → `webapp/public/main.js`
  - `lambda-*.mjs` → `webapp/lambda-*.mjs`
  - `infra/main.tf` → `webapp/infra/main.tf`
  - `scripts/upload_to_s3/constants.py` → `webapp/scripts/...` *(if moved)*
  - Inline “Sources:” comments throughout the file (same prefixes).
  - Comment “Path relative to public/” → “Path relative to static site root (`webapp/public/` locally; S3 bucket root when deployed)”.
- **Unchanged:** `stimuli.post_catalog_path` value `img/...` if present; AWS URLs; bucket names.
- **Priority:** must-update (comments are operator source maps)

### 8. `jobs/config/mirrorview_scaled_2026_06_18.yaml`

- **Why:** Fewer path comments than the default YAML; still referenced as SoT from `config.js` / lambdas.
- **Specific changes:** No hard `public/`/`lambda-` path list in header today. Nice-to-have: add a short comment pointing operators at `webapp/public/config.js`, `webapp/public/main.js`, `webapp/lambda-*.mjs` for where values are copied. `stimuli.post_catalog_path: img/...` stays as-is.
- **Priority:** nice-to-have

### 9. `public/main.js` header / STUDY_SPEC comments (moves to `webapp/public/main.js`)

- **Why:** Comments name sibling files and “Path under public/”; after move, paths should stay accurate for humans/agents.
- **Specific changes:**
  - Cross-repo alignment bullets: `lambda-get-post-assignments.mjs` → `webapp/lambda-get-post-assignments.mjs` (or “sibling under `webapp/`”).
  - Repeated “Used only in public/main.js” → “Used only in this file” or `webapp/public/main.js`.
  - `/** Path under public/ for the stimulus catalog fetch */` → `/** Path relative to static site / S3 root (local file under webapp/public/) */`.
  - **Do not change** `postCatalogPath: 'img/flips_scaled_2026_06_18.csv'`.
- **Priority:** must-update for path wording; value unchanged

### 10. `public/config.js` header (moves with file)

- **Why:** Only points at `jobs/config/...` (stays valid). Optional clarity that this file lives under `webapp/public/`.
- **Priority:** nice-to-have

---

## Docs that do **not** need path updates for this reorg

| Path | Reason |
|---|---|
| `docs/runbooks/README.md` | Index stub; no filesystem paths |
| `docs/runbooks/CODING_GUIDES.md` | No `public/` / lambda / infra refs |
| `docs/runbooks/WHAT_IS_MIRRORVIEW.md` | Conceptual; no local deploy paths |
| `docs/runbooks/MANUAL_TESTING.md` | Mentions S3/DynamoDB only; no local tree paths |
| `docs/README.md` | Stub |
| Experiment READMEs under `experiments/**` citing `flips.csv` | Job/experiment outputs stay at root; not webapp assets |
| Older `docs/plans/*` | Historical plans; do not rewrite unless actively used |

---

## Adjacent non-doc reminders (out of scope for this file’s edits, but docs will be wrong until code matches)

These are **code** path updates the runbooks assume; flag so doc PRs land with or after the reorg:

1. **`infra/main.tf`** — today `file("${path.module}/../lambda-*.mjs")`; after move must become same-dir or `./lambda-*.mjs` under `webapp/infra/`.
2. **`scripts/upload_to_s3/*`** — staging looks for repo-root `public/`; must resolve `webapp/public/` (and update usage comments in `verify_s3_object_matches_local.sh`).
3. **`package.json`** — moves under `webapp/`; root `npm install` story in AGENTS must change.
4. **Upload allowlist “repo-root fallback”** docs in HOW_TO_REPLACE_STIMULI — redefine fallback root as `webapp/` or keep explicit dual roots.

---

## Suggested update order

1. **must-update together with reorg:** `AGENTS.md`, `HOW_TO_REPLACE_STIMULI_DATASET.md`, `SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md`, `AWS_DEPLOYMENT_GUIDE.md`, yaml comment headers, `main.js` comments, smoke README.
2. **must-update structure / nice-to-have rewrite:** root `README.md`.
3. **nice-to-have:** `mirrorview_scaled_*.yaml` pointer comments, `config.js` header clarity.

---

## Verification checklist (after doc edits)

- [ ] Grep docs for `` `public/ ``, `lambda-get-post-assignments`, `lambda-save-jspsych-data`, `` `infra/ ``, `--directory public`, `mkdir -p public` — remaining hits should be intentional (S3-relative language, historical plans, or “webapp/public”).
- [ ] Copy/paste AGENTS serve + stimuli commands from a clean checkout and confirm experiment loads past political affiliation.
- [ ] Confirm no doc rewrote `img/flips_scaled_2026_06_18.csv` into a `webapp/`-prefixed **S3 key**.
