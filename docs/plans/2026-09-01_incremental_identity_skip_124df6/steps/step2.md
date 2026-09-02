# Step 2: Switch ingest to the explicit skip-set loads

## Goal

Bluesky, Twitter, and Reddit ingest pick one skip-set load from YAML policy, then exclude → persist → extend. `StorageManager.append_deduped_records` calls `exclude_seen_ids` and `add_seen_ids`. Ingest stops passing `include_prior_runs` on `DedupeConfig`.

## Caller / unit of work

**Main caller:** `run_sync_tasks` in `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_bluesky.py` (same shape in `sync_twitter.py` and `_open_reddit_dedupe_sessions` in `sync_reddit.py`).

**Slice:** construct `DedupeSession` without `include_prior_runs` → one load → `append_deduped_records` uses exclude then add.

**Out of scope:** preprocess runner; deleting `warm` / `include_prior_runs` / `filter_rows` / `note_appended` (preprocess still uses `warm`); runbook; YAML token meanings; feature generation.

**Depends on:** Step 1 (new methods exist). Parallel with Step 3.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-09-01_incremental_identity_skip_124df6/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/deduplication.py` | `policy_includes_prior_runs`, new load/exclude/add methods |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_bluesky.py` | `run_sync_tasks` session setup around lines 236–245 |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_twitter.py` | same around lines 119–128 |
| `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_reddit.py` | `_open_reddit_dedupe_sessions` around lines 381–406; comments vs posts policies |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py` | `append_deduped_records` currently calls `filter_rows` / `note_appended` |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_storage.py` | persist tests that currently call `warm` |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/ingestion/test_sync_checkpoint.py` | `test_append_deduped_records_skips_seen_ids` |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_bluesky.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_twitter.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_reddit.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py` (`append_deduped_records` only)
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_storage.py`
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/ingestion/test_sync_checkpoint.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/deduplication.py` (do not delete compatibility methods here)
- `/Users/mark/src/work/mirrorview-wt/docs/runbooks/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/**`
- YAML config files / `dedupe_policy` token strings

## Contracts to lock

Ingest session setup (Bluesky/Twitter; Reddit repeats per comments/posts session):

```text
session = DedupeSession(DedupeConfig(id_column=..., filename=...))
  # do not pass include_prior_runs

if policy_includes_prior_runs(policy):
    session.load_seen_ids_from_all_runs(storage)
else:
    session.load_seen_ids(storage, output_dir)

# then existing append_deduped_records(...)
```

Policy sources (unchanged keys):

- Bluesky/Twitter: `ingestion_params.get("dedupe_policy")`
- Reddit comments: `ingestion_params.get("comments_dedupe_policy")`
- Reddit posts: `ingestion_params.get("posts_dedupe_policy")`

`append_deduped_records`:

```text
kept_rows, skipped = dedupe_session.exclude_seen_ids(rows)
if kept_rows:
    append_records(...)
    dedupe_session.add_seen_ids(kept_rows)
return AppendResult(kept=len(kept_rows), skipped=skipped)
```

Do not call `add_seen_ids` when `kept_rows` is empty (same as today's `note_appended` guard).

Do not rename `append_deduped_records`. Do not migrate YAML tokens. `policy_includes_prior_runs` stays the branch.

## Test design

given a current-run CSV already containing id "1"
when the test session calls load_seen_ids (not warm) then append_deduped_records with ["1", "2"]
then kept == 1, skipped == 1, disk ids == {"1", "2"}

given a prior run dir with uri X and include-prior policy
when the test session calls load_seen_ids_from_all_runs then append_deduped_records with [X, new]
then skipped == 1, kept == 1

given two dataset ids
when session B loads only B's run
then id present only in A is not skipped (existing cross-dataset test)

Rewrite `test_storage.py` and `test_sync_checkpoint.py` persist tests to call `load_seen_ids` or `load_seen_ids_from_all_runs` instead of `warm` + `include_prior_runs=True`. Do not delete those tests.

`test_deduplication.py` warm tests stay; they still prove compatibility for preprocess.

## Implementation notes

Follow implement-from-spec in this packet. Flesh in order: `append_deduped_records` → Bluesky `run_sync_tasks` → Twitter `run_sync_tasks` → Reddit `_open_reddit_dedupe_sessions`. Tests first for the storage persist path.

Do not call both load methods on one ingest session.

## Must pass

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_storage.py tests/data_platform/utils/test_deduplication.py tests/data_platform/ingestion -q
```

Expected: exit 0.

Grep in ingest files must show no `include_prior_runs=` and no `.warm(`:

```bash
rg -n "include_prior_runs|\.warm\(" data_platform/ingestion
```

Expected: no matches.

## Must fail / not happen

- Preprocess still using `warm` is **required** (do not migrate it here).
- Calling both load methods in one ingest session.
- Changing `dedupe_policy` YAML token strings.
- Removing `warm` from `DedupeSession`.
