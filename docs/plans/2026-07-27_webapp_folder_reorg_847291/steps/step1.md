# Step 1: Preflight and branch

## Goal

Confirm a dedicated branch, a clean-enough working tree, and that the expected web roots still sit at the repo top before any move. Abort if unexpected edits touch the live site, Lambdas, or infra tree. No filesystem moves in this step.

## Caller / unit of work

**Main caller:** A human or agent starting the reorg, before any `git mv`.

**In scope:** Branch check, inventory of current roots, capture of baseline path strings, abort criteria.

**Out of scope:** Any `git mv`, path edits, Terraform, S3, docs rewrites.

## Prep references

- Move map (do not execute yet): [FILES_MOVED.md](../FILES_MOVED.md)
- Preflight commands (authoritative checklist): [ROLLOUT_PLAN.md](../ROLLOUT_PLAN.md) § Preflight

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/public/` | Must exist as move source |
| `/Users/mark/src/work/mirrorView-task/lambda-get-post-assignments.mjs` | Must exist at repo root |
| `/Users/mark/src/work/mirrorView-task/lambda-save-jspsych-data.mjs` | Must exist at repo root |
| `/Users/mark/src/work/mirrorView-task/infra/main.tf` | Must exist; capture `file("${path.module}/...")` lines |
| `/Users/mark/src/work/mirrorView-task/package.json` | Must exist at repo root |
| `/Users/mark/src/work/mirrorView-task/package-lock.json` | Must exist at repo root |
| `/Users/mark/src/work/mirrorView-task/scripts/upload_to_s3/` | Must exist (Option A move source) |
| `/Users/mark/src/work/mirrorView-task/testing/smoke_tests/` | Must exist (move source) |
| `/Users/mark/src/work/mirrorView-task/.gitignore` | Baseline ignore paths for Step 3 |
| `/Users/mark/src/work/mirrorView-task/public/config.js` | Confirm live API URLs unchanged later |

## Files allowed to change

- None required. Creating/checking out a git branch is allowed (ref only).
- Do **not** modify tracked file contents in this step.

## Files forbidden to change

Everything under the deployable unit and its contracts, including but not limited to:

- `public/**`, `infra/**`, `lambda-*.mjs`, `package.json`, `package-lock.json`
- `scripts/upload_to_s3/**`, `testing/smoke_tests/**`
- `webapp/**` (must not exist yet, or must be empty/unused)
- `AGENTS.md`, `README.md`, `docs/runbooks/**`, `jobs/**`, `experiments/**`, `lib/**`, `pyproject.toml`

## Exact commands

```bash
cd /Users/mark/src/work/mirrorView-task

git status
git branch --show-current
# Expect: not bare "main" for the move work, OR create a branch now:
# git checkout -b chore/webapp-reorg

# Inventory — every path must exist
ls -la public lambda-get-post-assignments.mjs lambda-save-jspsych-data.mjs infra package.json package-lock.json
ls scripts/upload_to_s3 testing/smoke_tests

# Confirm broken npm scripts (expected; do not "fix")
grep -n server-local package.json README.md || true
test ! -f server-local.js && echo "OK: server-local.js absent"

# Capture Terraform archive path shape (today: siblings of infra/)
rg -n 'file\("\$\{path\.module\}' infra/main.tf
# Expect lines containing:
#   file("${path.module}/../lambda-get-post-assignments.mjs")
#   file("${path.module}/../lambda-save-jspsych-data.mjs")

# Confirm webapp/ does not already hold a conflicting tree
test ! -e webapp && echo "OK: webapp/ absent" || ls -la webapp

# Record pre-move SHA for rollback notes
git rev-parse HEAD
```

### Expected outputs (pass signals)

- `git status`: clean, **or** only unrelated known untracked files (e.g. plan docs under `docs/plans/`, local DBs). No unexpected dirty edits under `public/`, `infra/`, `lambda-*.mjs`, `scripts/upload_to_s3/`.
- Dedicated branch name checked out (example: `chore/webapp-reorg`).
- Inventory `ls` succeeds for all listed roots.
- `OK: server-local.js absent`
- `rg` shows the two `file("${path.module}/../lambda-....mjs")` lines.
- `OK: webapp/ absent` (preferred). If `webapp/` exists, it must be empty of conflicting `public/`, `infra/`, or lambdas — otherwise abort.

## Pass / fail

### Pass

1. Dedicated branch is checked out.
2. Working tree is clean enough: no uncommitted edits to the live site, Lambdas, infra, npm package files, or upload/smoke trees.
3. All move sources listed in [FILES_MOVED.md](../FILES_MOVED.md) Summary table exist at the **From** paths.
4. Pre-move SHA recorded.

### Fail / abort (do not proceed to Step 2)

1. Unexpected dirty changes in `public/`, `infra/`, `lambda-*.mjs`, `package.json`, `scripts/upload_to_s3/`, or `testing/smoke_tests/` — stash or commit elsewhere first.
2. Attempting the move on `main` without creating a branch.
3. A pre-existing `webapp/` tree that already contains partial reorg leftovers (dual trees).
4. Missing any required From path from FILES_MOVED.md.

## Rollback

No content changes — nothing to roll back. Switch branch or discard the empty branch if created by mistake.

## Done when

Preflight checklist above is green and the implementer is ready to execute Step 2 git moves only.
