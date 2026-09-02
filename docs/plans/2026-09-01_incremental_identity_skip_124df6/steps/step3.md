# Step 3: Switch preprocess to skip then collapse

## Goal

Preprocess loads the all-runs skip set **before** creating the new run directory, drops known IDs with pandas, then collapses remaining IDs last-wins in a named helper. Delete `_drop_already_preprocessed`. Do not convert the DataFrame to `list[dict]` to call `exclude_seen_ids`. Do not call `add_seen_ids` (write once at end).

## Caller / unit of work

**Main caller:** `preprocess_records` in `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/runner.py`.

**Slice:** `load_seen_ids_from_all_runs` → pandas drop via `session.seen_ids` → `collapse_candidates_by_id(..., keep="last")` → existing transform/filter/save.

**Out of scope:** ingest callers; deleting `warm` from `DedupeSession`; runbook mermaid (Step 4); YAML tokens; feature generation.

**Depends on:** Step 1. Parallel with Step 2.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-09-01_incremental_identity_skip_124df6/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/runner.py` | `preprocess_records`, `_drop_already_preprocessed`, `save_preprocessed` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py` | `create_new_run_dir`, `load_seen_ids_from_all_runs` |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/preprocessing/test_preprocess_twitter.py` | `test_second_preprocess_run_skips_already_preprocessed_ids` |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/runner.py`
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/preprocessing/test_preprocess_twitter.py` (add collapse / skip-count coverage; keep existing re-run test)
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/preprocessing/test_preprocess_bluesky.py` only if a test would otherwise break
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/preprocessing/test_preprocess_reddit.py` only if a test would otherwise break

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/deduplication.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/preprocess_bluesky.py` (still calls `preprocess_records`)
- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/preprocess_twitter.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/preprocess_reddit.py`
- `/Users/mark/src/work/mirrorview-wt/docs/runbooks/**`

## Contracts to lock

`collapse_candidates_by_id` lives in `runner.py`, **not** on `DedupeSession`:

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

## Test design

Keep `test_second_preprocess_run_skips_already_preprocessed_ids` green (second run `row_counts.input == 0`).

New unit tests in the twitter preprocess test module (or a small `test_runner.py` next to it if you need to import helpers without a full CLI):

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

Do not convert records to `list[dict]` in `preprocess_records` for skip.

## Implementation notes

Follow implement-from-spec. Flesh `collapse_candidates_by_id` first, then the pandas drop in `preprocess_records`, then delete `_drop_already_preprocessed`, then print wording.

`create_new_run_dir` is inside `save_preprocessed` today. Keep it there. Load the skip set before that call so the new empty run dir is not part of the all-runs scan.

## Must pass

```bash
cd /Users/mark/src/work/mirrorview-wt
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
