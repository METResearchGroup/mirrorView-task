# Step 1: Slim the preprocess writer, tests, and runbook list

## Goal

New preprocess `metadata.json` contains only `dataset_id`, `source_raw_runs`, and `row_counts`. Tests and the stimuli runbook preprocess outputs list match that key set. Historical JSON is not migrated.

## Caller / unit of work

**Main caller:** `save_preprocessed` in `/workspace/data_platform/preprocessing/runner.py`, invoked by `preprocess_records` in the same file, which the platform entrypoints call.

**Slice:** write a preprocess run whose metadata dict has exactly those three keys; keep package-relative `source_raw_runs` and nested `row_counts` `input` / `output`; update tests and the runbook list.

**Out of scope:** dropping raw `sync_timestamp` (issue #84); dropping curated `files` (issue #85); rewriting JSON already on disk; dual-key compatibility readers; changing how records files are named or loaded.

## Decision (locked)

Pick the option that most literally matches Done-when.

1. The writer dict has exactly three top-level keys: `dataset_id`, `source_raw_runs`, `row_counts`. Do not keep `files`, `source_raw_run`, or `preprocess_timestamp` on any write path.
2. `source_raw_runs` stays a list of package-relative raw run directories, same strings as today (for example `data/twitter/{dataset_id}/raw/2026_05_31-11:00:00`). An empty list is `[]`. Do not write a singular fallback field.
3. `row_counts` stays `{"input": <int>, "output": <int>}`. Do not flatten those two numbers to top-level keys.
4. Keep metadata as a `dict`. Do not add a TypedDict, Pydantic model, or helper class for this slim-down.
5. Do not add a reader that accepts old keys. Downstream code does not read preprocess `files`, `source_raw_run`, or `preprocess_timestamp`.
6. Stimuli runbook: `/workspace/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md` is the operator runbook for the pipeline that produces stimuli. Add or update a preprocess outputs list so it names `dataset_id`, `source_raw_runs`, and `row_counts`. Also update the Preprocessed row in `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` under `### metadata.json at each stage` so Main fields is those three keys. Do not rewrite other runbook sections. Do not edit JSON under `experiments/`.

No new modules. Phases 2 and 3 have no new files. Do not stub `save_preprocessed`. Unattended: skip Phase 3 approval.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-02_slim_preprocess_metadata_61bee6/plan.md` | Parent plan |
| `/workspace/data_platform/preprocessing/runner.py` | `save_preprocessed` is the only writer of preprocess metadata |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py` | Asserts `files`, `source_raw_run`, `row_counts` |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py` | Asserts `files` |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py` | Gates only; change only if a test would otherwise break |
| `/workspace/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md` | Stimuli pipeline runbook |
| `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Preprocessed metadata fields row |

## Files allowed to change

- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_bluesky.py` (only if a test would otherwise break)
- `/workspace/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md`
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/generate_features/**`
- Historical preprocess `metadata.json` under `experiments/` or `data_platform/data/`
- Raw metadata writers (`sync_timestamp`)
- Curated metadata `files` map
- Plan files under `/workspace/docs/plans/2026-09-02_slim_preprocess_metadata_61bee6/` during implementation

## Contracts to lock

`save_preprocessed` in `/workspace/data_platform/preprocessing/runner.py` writes this metadata mapping and no other top-level keys:

```text
{
  "dataset_id": dataset_id,
  "source_raw_runs": list(source_raw_run_dirs),
  "row_counts": {
    "input": input_count,
    "output": len(records),
  },
}
```

Delete the local `source_raw_run` variable. Delete the `files` map. Delete `preprocess_timestamp`.

`source_raw_runs` values remain the package-relative directories already returned by `load_raw_records`.

Function signatures of `save_preprocessed`, `load_raw_records`, and `preprocess_records` stay the same.

## Test design

given a completed Twitter raw run with two rows, one of which fails validators
when preprocess_records
then metadata keys are exactly dataset_id, source_raw_runs, row_counts
and metadata["dataset_id"] equals the dataset id
and metadata["row_counts"]["input"] == 2
and metadata["row_counts"]["output"] == 1
and "files" not in metadata
and "source_raw_run" not in metadata
and "preprocess_timestamp" not in metadata

given two completed Twitter raw runs
when preprocess_records
then metadata["source_raw_runs"] has two package-relative directories under data/twitter/{id}/raw/
and "source_raw_run" is not a metadata key

given a completed Reddit raw run
when preprocess_records
then metadata keys are exactly dataset_id, source_raw_runs, row_counts
and "files" is not a metadata key

Update existing tests. Do not add a second writer test module.

## Implementation notes

Follow implement-from-spec. Unattended.

Phase 1: scope above.

Phase 2: no new files. Do not commit an empty scaffold.

Phase 3: contract is the dict above. Do not stub the live writer. Skip approval.

Phase 4: change the preprocess tests so they expect the three-key set. Commit. They must fail because the writer still emits the old keys.

Phase 5 units of work:

1. `save_preprocessed` writes only the three keys (designed tests go green)
2. Runbook preprocess outputs lists match the three keys

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing tests/data_platform -q
```

Expected: exit 0.

A newly written preprocess metadata file has `set(metadata.keys()) == {"dataset_id", "source_raw_runs", "row_counts"}`.

## Must fail / not happen

- Writing `files`, `source_raw_run`, or `preprocess_timestamp` in new preprocess metadata.
- A second write path that still emits the dropped keys.
- Reading old keys as aliases.
- Rewriting historical preprocess JSON under `experiments/` or `data_platform/data/`.
- Dropping raw `sync_timestamp` or curated `files`.
