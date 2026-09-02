# Step 1: Omit the files map and recompute the export name

## Goal

New curated `metadata.json` has no `files` key. Bluesky skip-if-fresh joins the latest curated run directory with the yaml export file name. The two experiment scripts recompute that name from `mirrorview.yaml` and do not read `files.export`. Curation specs drop `record_noun`. Historical JSON is not migrated.

## Caller / unit of work

**Main caller:** `run_curation` in `/workspace/data_platform/curate/runner.py` (writes metadata), plus `_is_up_to_date` in `/workspace/data_platform/curate/curate_bluesky.py` (skip-if-fresh).

**Slice:** write new curated metadata without `files`; skip when the latest run dir already has `{config_path.stem}.csv`; experiment scripts load that same derived name; specs print "records" instead of a per-platform noun.

**Out of scope:** rewriting JSON already on disk; a reader that still looks up `metadata["files"]["export"]`; changing yaml `output.filename` or how `run_curation` writes the csv; changing preprocess or raw metadata; S3 upload manifests that use a different `files` list.

## Decision (locked)

Pick the option that most literally matches Done-when.

1. `build_curate_metadata` in `/workspace/data_platform/curate/runner.py` does not include a `files` key. Remove the `export_filename` parameter. Do not write the key on any other path.
2. `run_curation` still writes `f"{relative_run_dir}/{rules.output.filename}"`. Do not change `OutputConfig.filename` or production yaml. Every production yaml already has `output.filename` equal to `{config stem}.csv`.
3. Bluesky `_is_up_to_date` does not read `latest_meta["files"]`. Pass `config_path: Path`. The yaml export file name is `f"{config_path.stem}.csv"`. Join `run_dirs[-1] / f"{config_path.stem}.csv"`. If that path does not exist, return `None` and rerun. Do not call `load_rules_config` in the skip path. Do not fall back to `files.export` when old JSON still has it.
4. `curate` in `/workspace/data_platform/curate/curate_bluesky.py` passes `config_path` into `_is_up_to_date`.
5. Drop `record_noun` from `CuratePlatformSpec`. Drop `record_noun=` from `BLUESKY_CURATE_SPEC`, `TWITTER_CURATE_SPEC`, and `REDDIT_CURATE_SPEC`. The print in `run_curation` uses the word `records` instead of `spec.record_noun`.
6. `sample_data_to_mirror.py` and `count_missing_flips.py` still glob `*/curated/*/metadata.json` to find run directories. They join `metadata_fp.parent / f"{Path('mirrorview.yaml').stem}.csv"`. They do not `json.loads` metadata for the export name. They do not read `files` or `files.export`. If `json` is then unused in that file, remove the import.
7. Do not strip `files` from metadata loaded on disk. Flush is not in play here. Old JSON that still has the key stays on disk. New JSON must not grow the key.
8. Do not add a helper module. Inline `f"{config_path.stem}.csv"` at the skip site. Inline `f"{Path('mirrorview.yaml').stem}.csv"` in each experiment script. Do not add a named helper.
9. Update the Curated row in `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` under `### metadata.json at each stage` so Main fields no longer names `files.export`. Replace the sentence that says curate writes export paths into metadata for `sample_data_to_mirror.py`. Update the sample-stage paragraph and `/workspace/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md` handoff sentence so they say the script globs metadata.json to find run directories and loads `{stem of mirrorview.yaml}.csv`. Do not edit JSON under `experiments/`.

No new modules. Phases 2 and 3 have no new files. Do not stub `build_curate_metadata`, `run_curation`, or `_is_up_to_date`. Unattended: skip Phase 3 approval.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-02_drop_curated_file_maps_c9f3a1/plan.md` | Parent plan |
| `/workspace/data_platform/curate/runner.py` | Writer and spec log noun |
| `/workspace/data_platform/curate/curate_bluesky.py` | Skip-if-fresh reads `files.export` |
| `/workspace/data_platform/curate/curate_twitter.py` | Spec still has `record_noun` |
| `/workspace/data_platform/curate/curate_reddit.py` | Spec still has `record_noun` |
| `/workspace/data_platform/curate/apply_rules.py` | `OutputConfig.filename` stays |
| `/workspace/tests/data_platform/curate/test_curate_bluesky.py` | Skip fixtures seed `files.export` |
| `/workspace/tests/data_platform/curate/test_curate_twitter.py` | Asserts `metadata["files"]["export"]` |
| `/workspace/tests/data_platform/curate/test_curate_reddit.py` | Asserts `metadata["files"]["export"]` |
| `/workspace/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` | Reads `files.export` |
| `/workspace/experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py` | Reads `files.export` |
| `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Curated metadata fields row |
| `/workspace/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md` | Handoff still says the script reads metadata for the export |

## Files allowed to change

- `/workspace/data_platform/curate/runner.py`
- `/workspace/data_platform/curate/curate_bluesky.py`
- `/workspace/data_platform/curate/curate_twitter.py`
- `/workspace/data_platform/curate/curate_reddit.py`
- `/workspace/tests/data_platform/curate/test_curate_bluesky.py`
- `/workspace/tests/data_platform/curate/test_curate_twitter.py`
- `/workspace/tests/data_platform/curate/test_curate_reddit.py`
- `/workspace/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`
- `/workspace/experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py`
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`
- `/workspace/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md`

## Files forbidden to change

- `/workspace/data_platform/curate/apply_rules.py`
- `/workspace/data_platform/curate/configs/**`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/utils/storage.py`
- Historical `metadata.json` under `experiments/` or `data_platform/data/`
- Plan files under `/workspace/docs/plans/2026-09-02_drop_curated_file_maps_c9f3a1/` during implementation
- Webapp S3 scripts whose `files` key is a different manifest

## Contracts to lock

`build_curate_metadata` writes this mapping and does not include `files`:

```text
{
  "dataset_id": dataset_id,
  "name": rules_name,
  "rules_hash": rules_hash,
  "source_preprocessed_runs": source_preprocessed_runs,
  "row_counts": {
    "preprocessed": len(wide_df),
    "wide": len(wide_df),
    "after_filters": len(filtered_df),
  },
  "filter_results": [
    {
      **step.rule.model_dump(),
      "records_before": step.records_before,
      "records_passing": step.records_passing,
    }
    for step in rules_result.steps
  ],
}
```

Signature:

```text
def build_curate_metadata(
    *,
    dataset_id: str,
    rules_name: str,
    rules_hash: str,
    source_preprocessed_runs: list[str],
    wide_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    rules_result: ApplyRulesResult,
) -> dict[str, Any]
```

`CuratePlatformSpec`:

```text
@dataclass(frozen=True)
class CuratePlatformSpec:
    platform: str
    storage_cls: StorageManagerFactory
    columns: PlatformSpecificColumns
```

No `record_noun` field. The three platform specs pass only those three fields.

`_is_up_to_date` signature adds `config_path: Path`. After the existing hash and source-run checks, the skip path is:

```text
output_path = run_dirs[-1] / f"{config_path.stem}.csv"
if not output_path.exists():
    return None
return output_path
```

Do not read `latest_meta.get("files", ...)`.

Experiment export path:

```text
export_fp = metadata_fp.parent / f"{Path('mirrorview.yaml').stem}.csv"
```

`run_curation` print:

```text
f"curate_{spec.platform}: kept {len(filtered_df)} of {len(wide_df)} records -> {relative_run_dir}"
```

## Test design

given `run_curation` for Twitter and Reddit mirrorview yaml
when the function returns
then `"files" not in metadata`
and `Path(relative_output).name == "mirrorview.csv"`
and `source_preprocessed_runs` is unchanged

given Bluesky skip fixtures whose curated metadata has no `files` key
and the config path is `test.yaml` so the yaml export file name is `test.csv`
and `test.csv` exists in the latest run dir
when `curate` runs
then `run_curation` is not called
and the result is the existing run dir

given Bluesky skip fixtures with matching hash and source runs
and the config path is `test.yaml`
and `test.csv` is missing from the latest run dir
when `curate` runs
then `run_curation` is called once

given curated metadata that still contains `files.export` pointing at a different name than `{config_path.stem}.csv`
and `{config_path.stem}.csv` is missing
when skip-if-fresh runs
then it does not treat the old files map as the export name
and `run_curation` is called

Do not add a second test module. Update existing tests. `_write_curated_run` must stop writing a `files` key. Drop the `export_filename` parameter from that helper if nothing else uses it. After Phase 4, Twitter and Reddit assertions that read `metadata["files"]["export"]` become `"files" not in metadata`.

Experiment scripts have no pytest. After they stop reading `files.export`, grep of those two files must not match `files.export` or `metadata["files"]`.

## Implementation notes

Follow implement-from-spec. Unattended.

Phase 1: scope above.

Phase 2: no new files. Do not commit an empty scaffold.

Phase 3: contracts above. Do not stub the live writer. Skip approval.

Phase 4: change the tests listed above. Commit. They must fail because metadata still contains `files`, Bluesky skip still requires `files.export` in seeded metadata, and `_write_curated_run` no longer seeds that key.

Phase 5 units of work:

1. `build_curate_metadata` omits `files` and drops `export_filename`. `run_curation` stops passing that argument. Twitter and Reddit metadata tests go green.
2. `_is_up_to_date` takes `config_path` and joins `run_dirs[-1] / f"{config_path.stem}.csv"`. `curate` passes `config_path`. Bluesky skip tests go green.
3. Drop `record_noun` from `CuratePlatformSpec` and the three platform specs. Print uses `records`.
4. Experiment scripts join the run dir with `{Path('mirrorview.yaml').stem}.csv` and stop reading metadata for the export name.
5. Runbook Curated fields row and sample handoff sentences match the new readers.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/curate tests/data_platform -q
```

Expected: exit 0.

A newly written curated metadata mapping has `"files" not in metadata`.

Bluesky skip-if-fresh succeeds when `{config_path.stem}.csv` exists in the latest run dir, even if metadata has no `files` key.

```bash
rg -n 'files\.export|metadata\["files"\]' experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py data_platform/curate
```

Expected: no matches.

## Must fail / not happen

- Writing `files` in new curated metadata.
- Reading `latest_meta["files"]` or `metadata["files"]["export"]` as the export source.
- A second write path that still emits the dropped key.
- Falling back to `files.export` when old JSON still has it.
- Rewriting historical curated JSON under `experiments/` or `data_platform/data/`.
- Changing yaml `output.filename` or the `run_curation` write path.
- Keeping `record_noun` on `CuratePlatformSpec`.
