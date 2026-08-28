# Step 4: Port unit tests and run the ingest test suite

## Goal

Copy the lab `tests/data_platform` suite into this repository and run the offline subset to green. Cover the Step 2 durability-gate behavior with tests that fail if Twitter/Reddit completion metadata omits `s3_upload_status: true` or if Bluesky uploads without opt-in.

## Caller / unit of work

**Main caller:**

```bash
cd /Users/mark/src/work/mirrorview-wt2
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: all collected tests pass (or an explicitly documented skip list for live-API / live-AWS tests only).

**In scope:** Copy tests, fix import/path assumptions for wt2 layout, add/adjust tests for local durability and Bluesky opt-in, run pytest.

**Out of scope:** Live API integration tests against Bluesky/Twitter/Reddit; live S3 uploads; sample script e2e with 10k rows; webapp tests.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt2/docs/plans/2026-08-06_migrate_data_ingestion_486894/plan.md` | Parent plan |
| `/Users/mark/src/work/lab_data_integrations_interface/tests/data_platform/` | Source suite (~34 test modules) |
| `/Users/mark/src/work/lab_data_integrations_interface/tests/data_platform/conftest.py` | Shared fixtures |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/sync_twitter.py` | Completion metadata after Step 2 |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/sync_bluesky.py` | Opt-in helper after Step 2 |

## Files allowed to change

- Create `/Users/mark/src/work/mirrorview-wt2/tests/data_platform/` (rsync from lab)
- Any file under that test tree (path fixes, new tests for Step 2)
- `/Users/mark/src/work/mirrorview-wt2/pyproject.toml` only if pytest config paths need a note (prefer not; default discovery should find `tests/`)
- Production code under `/Users/mark/src/work/mirrorview-wt2/data_platform/**` only to fix failures caused by the land (import errors, missing `__init__`), not feature creep

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt2/experiments/**`
- `/Users/mark/src/work/mirrorview-wt2/webapp/**`
- `/Users/mark/src/work/lab_data_integrations_interface/**`
- Do not delete or rewrite unrelated existing tests outside `tests/data_platform/`

## Exact copy command

```bash
cd /Users/mark/src/work/mirrorview-wt2
mkdir -p tests
rsync -a --exclude '__pycache__/' --exclude '*.pyc' \
  /Users/mark/src/work/lab_data_integrations_interface/tests/data_platform/ \
  /Users/mark/src/work/mirrorview-wt2/tests/data_platform/
```

## Required new / adjusted tests

1. **Twitter (or Reddit) local durability:** After the sync completion helper/path that Step 2 changed, metadata for a completed run includes `s3_upload_status is True`. Prefer testing a small extracted helper if sync CLIs are hard to unit-test; otherwise assert via the same metadata writer the sync uses.

2. **Bluesky opt-in default:** With `DATA_PLATFORM_BLUESKY_S3_UPLOAD` unset, the upload-enabled predicate is false.

3. **Bluesky opt-in on:** With env set to `1`, the predicate is true.

4. Keep existing preprocess tests that already stub `s3_upload_status: true` for Twitter/Reddit; they should still pass.

If Prefect- or AWS-live tests exist and cannot run offline, mark them `pytest.mark.skip` with a reason string naming the missing credential or service, and list those skips in the step completion notes. Do not silently delete them.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt2
PYTHONPATH=. uv run pytest tests/data_platform -q --tb=short
```

Expected: exit 0. If skips are used, print summary still shows failures = 0.

Optional narrower loop while fixing:

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q --tb=short
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_gate_checks.py -q --tb=short
```

## Pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Copy | `tests/data_platform/` exists with modules | Missing suite |
| Offline suite | `pytest tests/data_platform` exit 0 | Failures or collection errors |
| Step 2 coverage | New tests for local durability + Bluesky opt-in exist and pass | Behavior untested |
| Skips | Only live-API/AWS tests skipped, with reasons | Broad skips hiding land bugs |

## Out of scope reminders

- Do not run live sync against production APIs as a gate for this step.
- Do not update runbooks here (Step 5).
