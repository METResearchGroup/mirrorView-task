# Step 1: Add explicit skip-set load and row helpers next to the existing warmup API

## Goal

Add the agreed skip-set methods on `DedupeSession` without breaking existing callers. `warm`, `filter_rows`, `note_appended`, and `DedupeConfig.include_prior_runs` stay and delegate to the new methods. Ingest and preprocess callers are not migrated in this PR.

## Caller / unit of work

**Main caller:** unit tests in `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_deduplication.py` constructing a `DedupeSession` and calling the new methods.

**Slice:** new methods union into `seen_ids`; old methods keep working by delegating.

**Out of scope:** ingest callers (`sync_*.py`); `append_deduped_records`; preprocess runner; runbook; deleting `warm` / `include_prior_runs` / `filter_rows` / `note_appended`; YAML token migration; `FeatureLabelQuery`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-09-01_incremental_identity_skip_124df6/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/deduplication.py` | Current `warm` / `filter_rows` / `note_appended` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py` | `load_seen_ids_from_disk` and `load_seen_ids_from_all_runs` already exist |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_deduplication.py` | Existing warm/filter/note tests that must stay green |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/deduplication.py`
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_deduplication.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py`
- `/Users/mark/src/work/mirrorview-wt/docs/runbooks/**`
- `/Users/mark/src/work/mirrorview-wt/backlog.md`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/**`

## Contracts to lock

Keep `DedupeConfig(id_column, filename=None, include_prior_runs=False)` unchanged.

Keep `DedupeSession.config` and `DedupeSession.seen_ids`.

Add these methods. Each load **unions** into `seen_ids` (`|=`). Callers of the new API call **only one** load per session setup. `warm` is the compatibility path that may call both.

```text
load_seen_ids(self, storage: StorageManager, run_dir: Path) -> None
  storage.load_seen_ids_from_disk(run_dir, self.config.id_column, filename=self.config.filename)
  union into seen_ids

load_seen_ids_from_all_runs(self, storage: StorageManager) -> None
  storage.load_seen_ids_from_all_runs(self.config.id_column, filename=self.config.filename)
  union into seen_ids

exclude_seen_ids(self, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]
  same behavior as today's filter_rows (keep skipped-count tuple)

add_seen_ids(self, rows: list[dict[str, Any]]) -> None
  same behavior as today's note_appended
```

Compatibility (must remain until Step 4):

```text
warm(self, storage, output_dir) -> None
  load_seen_ids(storage, output_dir)
  if config.include_prior_runs: load_seen_ids_from_all_runs(storage)

filter_rows(...) -> exclude_seen_ids(...)
note_appended(...) -> add_seen_ids(...)
```

Do not rename `DedupeSession`, `DedupeConfig`, `append_deduped_records`, or `policy_includes_prior_runs`.

## Test design

Pseudocode then real tests. Prefer the public new methods. Existing `test_session_warm_*`, `test_session_filter_rows_skips_seen`, `test_note_appended_updates_seen_ids`, and `test_policy_includes_prior_runs` must stay and stay green.

given storage.load_seen_ids_from_disk returns {"uri-a"}
when session.load_seen_ids(storage, Path("/tmp/run"))
then seen_ids == {"uri-a"}
and load_seen_ids_from_all_runs is not called

given storage.load_seen_ids_from_all_runs returns {"uri-b"}
when session.load_seen_ids_from_all_runs(storage)
then seen_ids == {"uri-b"}
and load_seen_ids_from_disk is not called

given seen_ids already {"uri-a"} and disk returns {"uri-b"}
when load_seen_ids
then seen_ids == {"uri-a", "uri-b"}  (union, not replace)

given seen_ids == {"uri-a"}
when exclude_seen_ids([{"uri": "uri-a"}, {"uri": "uri-b"}])
then kept == [{"uri": "uri-b"}], skipped == 1

given seen_ids == {"uri-a"}
when add_seen_ids([{"uri": "uri-b"}])
then seen_ids == {"uri-a", "uri-b"}

given include_prior_runs=True
when warm(storage, run_dir)
then both disk and all-runs loads happen (old test still covers this)

## Implementation notes

Follow implement-from-spec phases in this packet: contracts on `DedupeSession`, failing tests for the new methods, then flesh `load_seen_ids` → `load_seen_ids_from_all_runs` → `exclude_seen_ids` → `add_seen_ids` → rewire `warm`/`filter_rows`/`note_appended` as delegates. One Git commit per phase / unit of work.

Do not convert `warm` into a no-op. Ingest and preprocess still call it after this PR.

## Must pass

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_deduplication.py tests/data_platform/utils/test_storage.py tests/data_platform/ingestion tests/data_platform/preprocessing -q
```

Expected: exit 0. Existing warm/filter/note tests still collected and passing. New tests for the four methods passing.

## Must fail / not happen

- Ingest or preprocess files changed in this PR.
- `include_prior_runs` or `warm` removed.
- `load_seen_ids` calling `load_seen_ids_from_all_runs` (or the reverse).
- Either load **replacing** `seen_ids` instead of unioning.
