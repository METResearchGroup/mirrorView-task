# Step 1: Switch ingest persist and session setup to the explicit skip-set loads

## Goal

Bluesky, Twitter, and Reddit ingest pick one skip-set load from YAML policy, then exclude, persist, and extend. `StorageManager.append_deduped_records` calls `exclude_seen_ids` and `add_seen_ids`. Ingest stops passing `include_prior_runs` on `DedupeConfig`. Preprocess still calls `warm`.

## Caller / unit of work

**Main caller:** `run_sync_tasks` in `/workspace/data_platform/ingestion/sync_bluesky.py`. The same session-setup shape is used in `/workspace/data_platform/ingestion/sync_twitter.py` `run_sync_tasks` and `/workspace/data_platform/ingestion/sync_reddit.py` `_open_reddit_dedupe_sessions`.

**Slice:** construct `DedupeSession` without `include_prior_runs`, call exactly one load, then `append_deduped_records` uses exclude then add.

**Out of scope:** preprocess runner; deleting `warm` / `include_prior_runs` / `filter_rows` / `note_appended`; runbook; YAML token meanings; feature generation; sibling GitHub issues #70 and #71. Do not edit `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/**` or `/workspace/docs/plans/2026-09-02_explicit_skip_set_load_helpers_c4e91a/**`.

**Depends on:** GitHub issue #68 helpers already on the stack base (`load_seen_ids`, `load_seen_ids_from_all_runs`, `exclude_seen_ids`, `add_seen_ids`, `policy_includes_prior_runs`).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/steps/step2.md` | Source contracts for this slice (do not edit) |
| `/workspace/data_platform/utils/deduplication.py` | `policy_includes_prior_runs` and the new load/exclude/add methods |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | `run_sync_tasks` session setup |
| `/workspace/data_platform/ingestion/sync_twitter.py` | `run_sync_tasks` session setup |
| `/workspace/data_platform/ingestion/sync_reddit.py` | `_open_reddit_dedupe_sessions` comments vs posts policies |
| `/workspace/data_platform/utils/storage.py` | `append_deduped_records` currently calls `filter_rows` / `note_appended` |
| `/workspace/tests/data_platform/utils/test_storage.py` | persist tests that currently call `warm` |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | `test_append_deduped_records_skips_seen_ids` |
| `/workspace/data_platform/preprocessing/runner.py` | Confirm `warm` stays. Do not edit. |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/utils/storage.py` (`append_deduped_records` only)
- `/workspace/tests/data_platform/utils/test_storage.py`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`

Plan package files under `/workspace/docs/plans/2026-09-02_switch_ingest_to_explicit_skip_set_loads_a74c89/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/utils/deduplication.py` (do not delete compatibility methods)
- `/workspace/docs/runbooks/**`
- `/workspace/data_platform/generate_features/**`
- YAML config files / `dedupe_policy` token strings
- `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/plan.md`
- `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/steps/*.md`
- `/workspace/docs/plans/2026-09-02_explicit_skip_set_load_helpers_c4e91a/**`

## Contracts to lock

Ingest session setup (Bluesky and Twitter once; Reddit repeats per comments session and per posts session):

```text
session = DedupeSession(DedupeConfig(id_column=..., filename=...))
  # do not pass include_prior_runs

if policy_includes_prior_runs(policy):
    session.load_seen_ids_from_all_runs(storage)
else:
    session.load_seen_ids(storage, output_dir)

# then existing append_deduped_records(...)
```

Do not extract a shared load helper. Repeat this branch at each ingest session setup. Do not call both load methods on one ingest session.

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

Do not call `add_seen_ids` when `kept_rows` is empty. Do not rename `append_deduped_records`. Do not migrate YAML tokens. `policy_includes_prior_runs` stays the branch.

## Test design

given a current-run CSV already containing id "1"
when the test session calls load_seen_ids (not warm) then append_deduped_records with ["1", "2"]
then kept == 1, skipped == 1, disk ids == {"1", "2"}

given a prior run dir with uri X and include-prior policy
when the test session calls load_seen_ids_from_all_runs then append_deduped_records with [X, new]
then skipped == 1, kept == 1

given two dataset ids
when session B loads only B's run
then id present only in A is not skipped

Rewrite persist tests in `/workspace/tests/data_platform/utils/test_storage.py` and `test_append_deduped_records_skips_seen_ids` in `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` so they call `load_seen_ids` or `load_seen_ids_from_all_runs` instead of `warm` plus `include_prior_runs=True`. Do not delete those tests.

`/workspace/tests/data_platform/utils/test_deduplication.py` warm tests stay. They still prove compatibility for preprocess.

The persist tests will stay green after the load-method swap, because the load methods already exist. The rewritten tests still lock the public setup the persist path will use. Do not add spies on `filter_rows` or `note_appended`.

## Implementation notes (implement-from-spec)

Files already exist. There are no new modules. Phase 2 scaffold and Phase 3 contracts do not add files or stub existing callers, because stubbing persist or ingest would break current tests before the rewrite. If a phase does not change the repo, skip that commit. Full auto. Do not wait for Phase 3 approval.

Phase 4 then Phase 5, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 4 test design. Rewrite the persist tests listed above so they call `load_seen_ids` or `load_seen_ids_from_all_runs`. Do not implement product-code changes in this commit.
3. Phase 5 units, in this order, one commit each:
   1. `append_deduped_records` uses `exclude_seen_ids` then persist then `add_seen_ids` only when `kept_rows` is non-empty
   2. Bluesky `run_sync_tasks` session setup
   3. Twitter `run_sync_tasks` session setup
   4. Reddit `_open_reddit_dedupe_sessions` for comments and for posts
4. Phase 6. Run the must-pass commands. Confirm preprocess still calls `warm`. Confirm ingest has no `include_prior_runs=` and no `.warm(`.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_storage.py tests/data_platform/utils/test_deduplication.py tests/data_platform/ingestion -q
```

Expected: exit 0.

```bash
rg -n "include_prior_runs|\.warm\(" data_platform/ingestion
```

Expected: no matches.

```bash
rg -n "\.warm\(" data_platform/preprocessing
```

Expected: at least one match. Preprocess still using `warm` is required.

## Must fail / not happen

- Preprocess migrated off `warm`.
- `warm` removed from `DedupeSession`.
- Both load methods called on one ingest session.
- `dedupe_policy` YAML token strings changed.
- A shared helper extracted for the ingest load branch.
- `add_seen_ids` called when `kept_rows` is empty.
