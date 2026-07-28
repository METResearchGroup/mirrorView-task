# Step 2: Move the deployable unit under `webapp/`

## Goal

Relocate the static site, Lambda sources (under a dedicated `lambdas/` folder), Terraform module, npm package files, upload-to-S3 package, and smoke-test stubs into `webapp/` per the prep move map. Leave jobs, experiments, shared Python libs, analysis scripts, docs, root image analysis assets, and local_data fixtures at the repo root. Ensure no leftover root copies of the moved trees remain.

## Caller / unit of work

**Main caller:** Operator/agent executing `git mv` after Step 1 pass.

**In scope:** Physical moves + creating intermediate dirs (`webapp/`, `webapp/lambdas/`, `webapp/scripts/`, `webapp/testing/`). Optional: add empty `webapp/scripts/__init__.py` if needed for package recognition (preferred in Step 3 if not done here).

**Out of scope:** Editing Terraform `file()` paths, upload CWD/`PYTHONPATH`, `.gitignore`, docs, Terraform apply, S3 upload. Path *repairs* are Step 3.

## Prep references

- Authoritative from→to table: [FILES_MOVED.md](../FILES_MOVED.md) § Summary + Explicit non-moves
- Decision locked: **Option A** — move `scripts/upload_to_s3/` into `webapp/scripts/upload_to_s3/`
- Lambdas destination locked: `webapp/lambdas/` (not sibling-of-infra under `webapp/`). Ignore any ROLLOUT_PLAN target-layout sketch that omits the `lambdas/` directory — FILES_MOVED.md wins.

## Target tree after this step

```text
webapp/
  public/                                    # was ./public/
  infra/                                     # was ./infra/
  lambdas/
    lambda-get-post-assignments.mjs          # was ./lambda-get-post-assignments.mjs
    lambda-save-jspsych-data.mjs             # was ./lambda-save-jspsych-data.mjs
  package.json
  package-lock.json
  scripts/
    upload_to_s3/                            # was ./scripts/upload_to_s3/
  testing/
    smoke_tests/                             # was ./testing/smoke_tests/
```

Repo root **must still have:** `jobs/`, `experiments/`, `lib/`, `scripts/export_study_results.py`, `scripts/postprocess_mirrorview_data.py`, `scripts/deprecated/`, `scripts/__init__.py`, `pyproject.toml`, `uv.lock`, `docs/`, `AGENTS.md`, `README.md`, `img/`, `local_data/`, `testing/README.md` (orphan stub OK).

## Files to inspect (before/after)

| Path | Why |
|------|-----|
| All From/To rows in [FILES_MOVED.md](../FILES_MOVED.md) | Verify renames |
| `/Users/mark/src/work/mirrorView-task/scripts/` | Confirm upload gone; analysis scripts remain |
| `/Users/mark/src/work/mirrorView-task/testing/` | Confirm smoke_tests gone; README may remain |
| `git status` rename detection | Prefer rename, not delete+add |

## Files allowed to change

- Create: `webapp/`, `webapp/lambdas/`, `webapp/scripts/`, `webapp/testing/`
- `git mv` only for paths in the FILES_MOVED Summary table
- Optional stub: `webapp/scripts/__init__.py` (empty file) — may defer to Step 3

## Files forbidden to change

- File **contents** of moved trees (no edits to `.mjs`, `.tf`, `.py`, `public/**` in this step)
- Non-moves listed in FILES_MOVED.md (`jobs/`, `experiments/`, `lib/`, analysis scripts, `pyproject.toml`, `docs/`, `AGENTS.md`, `README.md`, `img/`, `local_data/`)
- Do not delete `testing/README.md` or `scripts/__init__.py` at repo root
- Do not create root wrappers that leave dual entrypoints for `public/` or `infra/`

## Exact commands

```bash
cd /Users/mark/src/work/mirrorView-task

# Preconditions (Step 1)
test ! -e webapp || { echo "FAIL: webapp/ already exists with content — abort"; exit 1; }
test -d public && test -d infra
test -f lambda-get-post-assignments.mjs && test -f lambda-save-jspsych-data.mjs

mkdir -p webapp/lambdas webapp/scripts webapp/testing

git mv public webapp/public
git mv infra webapp/infra
git mv lambda-get-post-assignments.mjs webapp/lambdas/lambda-get-post-assignments.mjs
git mv lambda-save-jspsych-data.mjs webapp/lambdas/lambda-save-jspsych-data.mjs
git mv package.json package-lock.json webapp/

# Option A
git mv scripts/upload_to_s3 webapp/scripts/upload_to_s3
git mv testing/smoke_tests webapp/testing/smoke_tests

# Sanity: no leftover roots
test ! -e public && test ! -e infra
test ! -e lambda-get-post-assignments.mjs
test ! -e lambda-save-jspsych-data.mjs
test ! -e package.json
test ! -d scripts/upload_to_s3
test ! -d testing/smoke_tests

# Presence checks
test -d webapp/public && test -f webapp/infra/main.tf
test -f webapp/lambdas/lambda-get-post-assignments.mjs
test -f webapp/lambdas/lambda-save-jspsych-data.mjs
test -f webapp/package.json && test -f webapp/package-lock.json
test -f webapp/scripts/upload_to_s3/constants.py
test -d webapp/testing/smoke_tests

# Non-moves still at root
test -d jobs && test -d experiments && test -d lib
test -f scripts/export_study_results.py
test -f scripts/__init__.py
test -d img && test -d local_data
test -f pyproject.toml

git status
```

### Expected outputs

- `git status` shows renames (R) for moved paths, not untracked copies of the same trees at both locations.
- All `test ! -e` leftover checks print nothing and exit 0.
- All presence and non-move `test` commands exit 0.

## Pass / fail

### Pass

1. Every FILES_MOVED Summary **To** path exists.
2. Every FILES_MOVED Summary **From** path is gone from repo root.
3. Explicit non-moves still at root.
4. No dual `public/` or `infra/` trees.

### Fail

1. Leftover `./public` or `./infra` at repo root.
2. Lambdas left at `webapp/lambda-*.mjs` instead of `webapp/lambdas/` (wrong layout vs FILES_MOVED).
3. `scripts/upload_to_s3/` still at repo root (Option A violated).
4. Accidental move of `jobs/`, `experiments/`, `lib/`, `img/`, or `local_data/`.
5. Content edits mixed into this step (belongs in Step 3).

## Rollback

```bash
cd /Users/mark/src/work/mirrorView-task
# If uncommitted:
git reset --hard HEAD
# If committed as its own commit:
# git revert <step2-commit>
# Or reverse git mv back to roots using the From column of FILES_MOVED.md
```

Do not touch AWS.

## Commit note (when committing)

Prefer a single commit for this step: `chore(webapp): move site stack under webapp/` — git mv only. Path repairs may be the next commit (Step 3).

## Done when

Tree matches Target tree above; leftover root checks pass; ready for Step 3 path contract repairs (Terraform currently still points at `${path.module}/../lambda-*.mjs` which will be **wrong** until Step 3 updates to `../lambdas/lambda-*.mjs`).
