# Step 1: Switch preprocess to skip then collapse

## Goal

Preprocess loads the all-runs skip set before creating the new run directory, drops known IDs with pandas, then collapses remaining IDs last-wins in a named helper. Delete `_drop_already_preprocessed`. Do not convert the DataFrame to `list[dict]` to call `exclude_seen_ids`. Do not call `add_seen_ids`.

## Caller / unit of work

**Main caller:** `preprocess_records` in `/workspace/data_platform/preprocessing/runner.py`.

**Slice:** `load_seen_ids_from_all_runs` → pandas drop via `session.seen_ids` → `collapse_candidates_by_id(..., keep="last")` → existing transform/filter/save.

**Out of scope:** ingest callers; deleting `warm` from `DedupeSession`; runbook mermaid (GitHub issue #71); YAML tokens; feature generation; sibling GitHub issue #71. Do not edit `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/**`, `/workspace/docs/plans/2026-09-02_explicit_skip_set_load_helpers_c4e91a/**`, or `/workspace/docs/plans/2026-09-02_switch_ingest_to_explicit_skip_set_loads_a74c89/**`.

**Depends on:** GitHub issues #68 and #69 already on this stack branch (`load_seen_ids_from_all_runs` on `DedupeSession`).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/steps/step3.md` | Source contracts for this slice (do not edit) |
| `/workspace/data_platform/preprocessing/runner.py` | `preprocess_records`, `_drop_already_preprocessed`, `save_preprocessed` |
| `/workspace/data_platform/utils/storage.py` | `create_new_run_dir`, `load_seen_ids_from_all_runs` |
| `/workspace/data_platform/utils/deduplication.py` | `load_seen_ids_from_all_runs` already exists. Do not edit. |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py` | `test_second_preprocess_run_skips_already_preprocessed_ids` |

## Files allowed to change

- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py` (add collapse / skip-count coverage; keep existing re-run test)
- `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py` only if a test would otherwise break
- `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py` only if a test would otherwise break
- `/workspace/tests/data_platform/preprocessing/test_runner.py` only if a test needs to import runner helpers without a platform CLI

Plan package files under `/workspace/docs/plans/2026-09-02_switch_preprocess_to_skip_then_collapse_d2084b/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/utils/deduplication.py`
- `/workspace/data_platform/preprocessing/preprocess_bluesky.py` (still calls `preprocess_records`)
- `/workspace/data_platform/preprocessing/preprocess_twitter.py`
- `/workspace/data_platform/preprocessing/preprocess_reddit.py`
- `/workspace/docs/runbooks/**`
- `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/**`
- `/workspace/docs/plans/2026-09-02_explicit_skip_set_load_helpers_c4e91a/**`
- `/workspace/docs/plans/2026-09-02_switch_ingest_to_explicit_skip_set_loads_a74c89/**`

## Contracts to lock

`collapse_candidates_by_id` lives in `/workspace/data_platform/preprocessing/runner.py`, not on `DedupeSession`:

```text
collapse_candidates_by_id(df: pd.DataFrame, id_col: str, keep: str = "last") -> pd.DataFrame
  drop_duplicates(subset=[id_col], keep=keep).reset_index(drop=True)
  keep="last": later raw run wins
```

`preprocess_records` order after the raw-run gate:

```text
preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
session = DedupeSession(DedupeConfig(id_column=spec.columns.records_id_column))
session.load_seen_ids_from_all_runs(preprocessed_storage)
  # BEFORE save_preprocessed / create_new_run_dir
  # never pass preprocessed_storage.root_dir as a fake run directory
  # never pass include_prior_runs=True

records, source_raw_run_dirs = load_raw_records(...)
id_col = spec.columns.records_id_column
is_new = ~records[id_col].isin(list(session.seen_ids))
skipped = len(records) - int(is_new.sum())   # prior-run skips only
records = records.loc[is_new].reset_index(drop=True)
records = collapse_candidates_by_id(records, id_col, keep="last")

then apply_text_transform / filter_records / save_preprocessed as today
do not call add_seen_ids
do not call exclude_seen_ids
```

Print: skipped count is prior-run IDs only, wording **"already in a prior preprocessed run"** (not rows removed by collapse). Example shape:

```text
preprocess_records: kept {n} of {m} {noun} (skipped {skipped} already in a prior preprocessed run) -> {output_dir}
```

`m` remains `len(records)` after skip+collapse and before filters (today's `input_count` meaning). Do not change `row_counts.input` semantics.

Delete `_drop_already_preprocessed` entirely.

Keep `create_new_run_dir` inside `save_preprocessed`. Load the skip set before that call so the new empty run dir is not part of the all-runs scan.

## Test design

Keep `test_second_preprocess_run_skips_already_preprocessed_ids` green (second run `row_counts.input == 0`). Put new tests in `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py`. Do not add `test_runner.py` unless a twitter-module test cannot import the helper.

given df with ids [a, a] and different text, keep="last"
when collapse_candidates_by_id
then one row, the last text

given seen_ids {a} and df rows [a, b, b]
when pandas drop then collapse
then skipped == 1 (only a)
and surviving ids == [b] (one row)

given no prior preprocessed runs
when load_seen_ids_from_all_runs then preprocess
then skipped == 0 and create_new_run_dir still happens inside save (existing write-output tests)

given a second preprocess run of the same already-preprocessed id
when preprocess_records prints
then the line includes "already in a prior preprocessed run"
and the skipped count is 1, not a collapse count

Do not convert records to `list[dict]` in `preprocess_records` for skip.

## Implementation notes (implement-from-spec)

Files already exist. There are no new modules. Phase 2 scaffold and Phase 3 contracts do not add files or stub existing callers, because stubbing `preprocess_records` would break current tests before the rewrite. If a phase does not change the repo, skip that commit. Full auto. Do not wait for Phase 3 approval.

Phase 4 then Phase 5, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 4 test design. Add the collapse, skip-count, and print-wording tests listed above. Keep `test_second_preprocess_run_skips_already_preprocessed_ids`. Do not implement product-code changes in this commit.
3. Phase 5 units, in this order, one commit each:
   1. `collapse_candidates_by_id` on `runner.py` (not on `DedupeSession`)
   2. pandas drop in `preprocess_records` after `load_seen_ids_from_all_runs`, then call collapse with `keep="last"`. Stop calling `_drop_already_preprocessed`. Do not pass `include_prior_runs`. Do not call `warm`. Do not call `add_seen_ids` or `exclude_seen_ids`.
   3. Delete `_drop_already_preprocessed` entirely. Remove unused imports that only it needed.
   4. Print wording: `already in a prior preprocessed run`. Skip count stays prior-run only.
4. Phase 6. Run the must-pass commands.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing tests/data_platform/utils/test_deduplication.py -q
```

Expected: exit 0.

```bash
rg -n "_drop_already_preprocessed" data_platform tests
```

Expected: no matches.

```bash
rg -n "include_prior_runs|\.warm\(" data_platform/preprocessing
```

Expected: no matches.

## Must fail / not happen

- Passing the stage root as `run_dir` to any load method.
- Using `exclude_seen_ids` on preprocess rows.
- Calling `add_seen_ids` from preprocess.
- Putting `collapse_candidates_by_id` on `DedupeSession`.
- Skip count including collapse duplicates.
- Editing ingest files in this layer.
