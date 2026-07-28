# FILES_MOVED — `webapp/` folder reorg

Prep only; no moves executed. Scope = full deployable jsPsych unit (static site + Lambdas + Terraform + S3 upload tooling + smoke stubs).

## Summary: from → to

| From | To |
|------|-----|
| `public/` | `webapp/public/` |
| `lambda-get-post-assignments.mjs` | `webapp/lambdas/lambda-get-post-assignments.mjs` |
| `lambda-save-jspsych-data.mjs` | `webapp/lambdas/lambda-save-jspsych-data.mjs` |
| `infra/` | `webapp/infra/` |
| `package.json` | `webapp/package.json` |
| `package-lock.json` | `webapp/package-lock.json` |
| `scripts/upload_to_s3/` | `webapp/scripts/upload_to_s3/` |
| `testing/smoke_tests/` | `webapp/testing/smoke_tests/` |

New dirs created by the move: `webapp/`, `webapp/lambdas/`, `webapp/scripts/` (upload only), `webapp/testing/`.

## Explicit non-moves

| Path | Why |
|------|-----|
| `jobs/` | Study/stimuli pipeline; not runtime webapp |
| `experiments/` | Offline ML/analysis |
| `lib/` | Shared Python (`REPO_ROOT`, env loaders) for analysis |
| `scripts/export_study_results.py` | S3 results export (analysis), no `upload_to_s3` imports |
| `scripts/postprocess_mirrorview_data.py` | Analysis postprocess |
| `scripts/deprecated/` | Dead helpers; leave at root |
| `scripts/__init__.py` | Keeps root `scripts.` package for remaining scripts |
| `pyproject.toml`, `uv.lock` | Python monorepo tooling |
| `docs/`, `AGENTS.md`, `README.md` | Docs updated later, not relocated |
| `img/` | See recommendations |
| `local_data/` | See recommendations |
| `testing/README.md` | Orphan stub at root after smoke_tests move |

## Open decisions / recommendations

### `scripts/upload_to_s3/` — **move into `webapp/`**

- Only consumers of `from scripts.upload_to_s3...` are files inside that package (no `lib/`, export, or experiment imports).
- Paths are CWD-relative (`Path("public")`, `Path("s3_upload")`); intended to run from the webapp root after move.
- After move: add `webapp/scripts/__init__.py`, run with `cd webapp && PYTHONPATH=. uv run python scripts/upload_to_s3/...` (or rewrite imports to `__file__`-relative and drop the package name). Do not leave at repo root — it is deploy-only for `public/`.

### `img/` — **keep at repo root**

- Tracked content: `img/all_mirrors_claude.csv` only.
- Used by `experiments/mirrors_content_analysis_2026_04_24/analysis/*/...` via `PROJECT_ROOT / "img" / "all_mirrors_claude.csv"`.
- Not part of the S3 allowlist deploy set (catalog is `public/img/flips_scaled_2026_06_18.csv`). Staging fallback `public/<rel>` **or** repo-root `<rel>` does not require moving this analysis CSV into `webapp/`.

### `local_data/` — **keep at root; candidate delete later**

- No `.py`/`.js`/`.mjs` references found.
- README-only remnant of missing `server-local.js` local save path.
- Contents are old `post_assignments.json` fixtures — not the live Lambda/S3 path. Do not move into `webapp/`.

## Mechanical path updates (code/config — not docs)

Required for the move to work:

| File | Change |
|------|--------|
| `webapp/infra/main.tf` | `file("${path.module}/../lambda-*.mjs")` → `file("${path.module}/../lambdas/lambda-*.mjs")` |
| `webapp/scripts/upload_to_s3/constants.py` | Keep `SOURCE_PUBLIC_DIR = Path("public")` if CWD=`webapp/`; else point at `webapp/public` |
| `webapp/scripts/upload_to_s3/stage_public_for_s3.py` | Import path / error strings if package root changes; allowlist resolve still `public/` then CWD fallback |
| `webapp/scripts/upload_to_s3/upload_public_to_s3.py` | `from scripts.upload_to_s3...` (same package under `webapp/` + `PYTHONPATH=webapp`) |
| `webapp/scripts/upload_to_s3/verify_s3_upload.py` | Same import + error path string |
| `webapp/scripts/upload_to_s3/run_upload.sh` | CWD note + `scripts/upload_to_s3/...` invocations under `webapp/` |
| `webapp/scripts/upload_to_s3/verify_s3_object_matches_local.sh` | Example `--local` path → `public/img/...` relative to `webapp/` |
| `.gitignore` | `public/img/...` → `webapp/public/img/...`; `infra/*.zip` → `webapp/infra/*.zip`; comment for upload staging |

Optional / comment-only (not runtime):

| File | Note |
|------|------|
| `jobs/config/mirrorview_default_2026_04_24.yaml` | Header comments cite old `public/`, `lambda-*.mjs`, `infra/`, `scripts/upload_to_s3/` paths |
| `webapp/public/main.js` | Comments name root `lambda-*.mjs` filenames (not filesystem loads) |
| `scripts/deprecated/*.py` | Hardcoded `public/` / upload paths; leave or ignore |

Docs to update later (not listed as mechanical code): `AGENTS.md`, `README.md`, `docs/runbooks/AWS_DEPLOYMENT_GUIDE.md`, `docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md`, `docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md`, `testing/smoke_tests/README.md` (after move).

## Coupling notes (investigation)

- Root `package.json` only references missing `server-local.js`; no other packages depend on it.
- `testing/` contains only `smoke_tests/` (+ empty `testing/README.md`); nothing else under `testing/` is webapp-only beyond that.
- Remaining `scripts/` (`export_*`, `postprocess_*`, `deprecated/`) do not import `upload_to_s3`.
