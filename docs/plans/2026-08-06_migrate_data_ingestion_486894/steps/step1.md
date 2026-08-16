# Step 1: Land the ingest package, tooling, deps, and env allowlist

## Goal

Copy the platform batch pipeline and its LLM helpers from the sibling lab repository into this repository so the package imports under `PYTHONPATH=.`. Merge platform API key names into the existing env loader. Add missing PyPI dependencies. Do not run a live sync in this step.

## Caller / unit of work

**Main caller:** import smoke from repo root:

```bash
cd /Users/mark/src/work/mirrorview-wt2
PYTHONPATH=. uv run python -c "import data_platform; import ml_tooling; print('IMPORT_OK')"
```

Expected stdout includes `IMPORT_OK` and exit code 0.

**In scope:** Copy trees, merge env allowlist keys, add dependencies, confirm imports resolve.

**Out of scope:** S3 durability gate fixes (Step 2); sample script discovery (Step 3); porting tests (Step 4); runbook edits (Step 5); live API sync; package rename to `data_ingestion/`.

## Decision (locked)

Land the batch package at `/Users/mark/src/work/mirrorview-wt2/data_platform/` so existing `from data_platform...` imports work without a rewrite. Do not rename the folder in this plan.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt2/strategy_planning/migrate_data_ingestion_pipeline.md` | Copy list and env keys |
| `/Users/mark/src/work/mirrorview-wt2/docs/plans/2026-08-06_migrate_data_ingestion_486894/plan.md` | Parent plan |
| `/Users/mark/src/work/lab_data_integrations_interface/data_platform/` | Source tree |
| `/Users/mark/src/work/lab_data_integrations_interface/ml_tooling/` | Source LLM + Perspective helpers |
| `/Users/mark/src/work/lab_data_integrations_interface/lib/load_env_vars.py` | Env keys to add |
| `/Users/mark/src/work/lab_data_integrations_interface/pyproject.toml` | Dep versions to pull |
| `/Users/mark/src/work/mirrorview-wt2/lib/load_env_vars.py` | Merge target |
| `/Users/mark/src/work/mirrorview-wt2/lib/constants.py` | Keep wt2 `REPO_ROOT` and Bedrock constants |
| `/Users/mark/src/work/mirrorview-wt2/lib/timestamp_utils.py` | Confirm API compatibility with lab callers |
| `/Users/mark/src/work/mirrorview-wt2/pyproject.toml` | Dep merge target |

## Files allowed to change

- Create `/Users/mark/src/work/mirrorview-wt2/data_platform/` (full package copy excluding `data/`)
- Create `/Users/mark/src/work/mirrorview-wt2/ml_tooling/` (full copy from lab)
- `/Users/mark/src/work/mirrorview-wt2/lib/load_env_vars.py` (add keys only)
- `/Users/mark/src/work/mirrorview-wt2/pyproject.toml` (add dependencies)
- `/Users/mark/src/work/mirrorview-wt2/uv.lock` (via `uv sync` / lock update)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt2/lib/constants.py` (do not overwrite with lab version)
- `/Users/mark/src/work/mirrorview-wt2/lib/timestamp_utils.py` unless a copied caller fails on the existing API; if change is required, only add compatibility, do not remove wt2 callers' behavior
- `/Users/mark/src/work/mirrorview-wt2/experiments/**`
- `/Users/mark/src/work/mirrorview-wt2/webapp/**`
- `/Users/mark/src/work/mirrorview-wt2/jobs/**`
- `/Users/mark/src/work/lab_data_integrations_interface/**` (source only; do not modify)
- Do not copy `/Users/mark/src/work/lab_data_integrations_interface/data_platform/data/`

## Exact copy commands

```bash
cd /Users/mark/src/work/mirrorview-wt2

# Package without local artifacts
rsync -a --exclude 'data/' --exclude '__pycache__/' --exclude '*.pyc' \
  /Users/mark/src/work/lab_data_integrations_interface/data_platform/ \
  /Users/mark/src/work/mirrorview-wt2/data_platform/

rsync -a --exclude '__pycache__/' --exclude '*.pyc' \
  /Users/mark/src/work/lab_data_integrations_interface/ml_tooling/ \
  /Users/mark/src/work/mirrorview-wt2/ml_tooling/

# Confirm no bulky data tree
test ! -d data_platform/data && echo NO_DATA_DIR_OK
du -sh data_platform ml_tooling
```

Expected: `NO_DATA_DIR_OK`; `data_platform` size is on the order of megabytes, not ~236MB.

## Env allowlist merge

In `/Users/mark/src/work/mirrorview-wt2/lib/load_env_vars.py`, add these keys to `ENV_VAR_TYPES` (keep existing `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `WANDB_API_KEY`):

- `BLUESKY_HANDLE`
- `BLUESKY_PASSWORD`
- `REDDIT_CLIENT_ID`
- `REDDIT_SECRET`
- `REDDIT_REDIRECT_URI`
- `REDDIT_USERNAME`
- `REDDIT_PASSWORD`
- `X_BEARER_TOKEN`
- `X_CONSUMER_KEY`
- `X_SECRET_KEY`

Do not change loader behavior beyond the allowlist.

## Dependencies to add to `pyproject.toml`

Add to `[project].dependencies` (versions at least as new as lab pins where listed):

- `atproto>=0.0.68`
- `tweepy>=4.14.0`
- `praw>=7.7.0`
- `duckdb>=1.0.0`
- `langdetect>=1.0.9`
- `tenacity` (match lab if pinned; otherwise leave unpinned minor or use lab's pin)
- `pyyaml>=6.0` if not already satisfied transitively for runtime (lab configs need YAML; prefer an explicit project dep if imports fail)

Do **not** add `prefect` in this step (orchestration optional; avoid pulling it until a later need).

Then:

```bash
cd /Users/mark/src/work/mirrorview-wt2
uv sync
```

Expected: exit 0; lockfile updated.

## `timestamp_utils` check

Lab and wt2 both expose `get_current_timestamp` with the same format string contract; wt2 uses `timezone.utc`, lab uses `UTC`. After copy, run:

```bash
PYTHONPATH=. uv run python - <<'PY'
from lib.timestamp_utils import get_current_timestamp
from data_platform.utils import dataset  # or any module that imports lib.timestamp_utils
print(get_current_timestamp())
print("TIMESTAMP_OK")
PY
```

If a copied module imports a lab-only symbol from `lib.timestamp_utils`, add only that symbol to wt2's file. Do not replace the whole file with the lab version.

## Pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Copy | `data_platform/` and `ml_tooling/` exist; no `data_platform/data/` | Missing trees or bulky `data/` copied |
| Env | New keys present in `ENV_VAR_TYPES` | Keys missing or loader rewritten unnecessarily |
| Deps | `uv sync` exit 0 | Sync fails on Python 3.12 or missing pins |
| Import | `IMPORT_OK` printed, exit 0 | ImportError / ModuleNotFoundError |

## Out of scope reminders

- Do not edit gate checks or sync upload behavior (Step 2).
- Do not edit `sample_data_to_mirror.py` (Step 3).
- Do not copy tests yet (Step 4).
- Do not edit runbooks (Step 5).
