# Step 5: Switch curation configs and callers to full export names

## Goal

Curation configs use a full export file name. The curator writes that file through a package-relative path. Newly written `source_preprocessed_runs` values are package-relative directories. The curated `files` map stays.

## Caller / unit of work

**Main caller:** `run_curation` in `/workspace/data_platform/curate/runner.py`, plus `_is_up_to_date` in `/workspace/data_platform/curate/curate_bluesky.py`.

**Slice:** load preprocessed `posts.csv` or `comments.csv` from every preprocess run; write `mirrorview.csv` (or the config's full name) under a new curated run; store source-run lists as package-relative directories.

**Out of scope:** dropping the curated `files` map (issue #85). Keep `files: {export: <full file name>}`. Do not slim other curated metadata keys.

## Decision (locked)

Change `OutputConfig.stem` to `OutputConfig.filename` in `/workspace/data_platform/curate/apply_rules.py`. The value is the full file name, e.g. `mirrorview.csv`. Delete `filename_for`. Write with `f"{relative_run_dir}/{rules.output.filename}"`.

Update production YAML:

- `/workspace/data_platform/curate/configs/bluesky/mirrorview.yaml` → `filename: mirrorview.csv`
- `/workspace/data_platform/curate/configs/bluesky/trump_econ_iran.yaml` → `filename: trump_econ_iran.csv`
- `/workspace/data_platform/curate/configs/reddit/mirrorview.yaml` → `filename: mirrorview.csv`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml` → `filename: mirrorview.csv`

Replace the `output.stem` key. Do not keep `stem` as an alias.

Preprocessed glob currently uses `records_filename`. Use `POSTS_FILENAME` or `COMMENTS_FILENAME` from constants according to the platform spec (Reddit comments, Bluesky/Twitter posts).

`source_preprocessed_runs` uses `to_package_relative` on each preprocess run directory.

Bluesky `_is_up_to_date` compares those package-relative strings to feature metadata and curated metadata. Tests that seed `preprocessed/2026_01_01-00:00:00` must seed `data/bluesky/{dataset_id}/preprocessed/2026_01_01-00:00:00` instead. No dual-key reader.

After this step, if `relative_run_path` has no remaining production callers, delete it from `/workspace/data_platform/utils/dataset.py`. That is the only allowed dataset.py edit in this step.

Also update `/workspace/tests/data_platform/utils/test_gate_checks.py` and `/workspace/tests/data_platform/utils/conftest.py` if they still treat `create_new_run_dir` as a `Path`. `write_stage_metadata` should resolve the relative run directory with `resolve_package_path` before writing `metadata.json`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/curate/apply_rules.py` | `OutputConfig.stem` |
| `/workspace/data_platform/curate/runner.py` | glob, filename_for, relative_run_path |
| `/workspace/data_platform/curate/curate_bluesky.py` | up-to-date check uses short source-run strings |
| `/workspace/data_platform/curate/configs/**/*.yaml` | stem values |
| `/workspace/tests/data_platform/curate/` | inline YAML and metadata assertions |
| `/workspace/tests/data_platform/utils/test_gate_checks.py` | create_new_run_dir as Path |

## Files allowed to change

- `/workspace/data_platform/curate/apply_rules.py`
- `/workspace/data_platform/curate/runner.py`
- `/workspace/data_platform/curate/curate_bluesky.py`
- `/workspace/data_platform/curate/curate_reddit.py` (only if old storage API remains)
- `/workspace/data_platform/curate/curate_twitter.py` (same)
- `/workspace/data_platform/curate/configs/bluesky/mirrorview.yaml`
- `/workspace/data_platform/curate/configs/bluesky/trump_econ_iran.yaml`
- `/workspace/data_platform/curate/configs/reddit/mirrorview.yaml`
- `/workspace/data_platform/curate/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/utils/dataset.py` (delete `relative_run_path` only if unused)
- `/workspace/tests/data_platform/curate/test_apply_rules.py`
- `/workspace/tests/data_platform/curate/test_curate_bluesky.py`
- `/workspace/tests/data_platform/curate/test_curate_reddit.py`
- `/workspace/tests/data_platform/curate/test_curate_twitter.py`
- `/workspace/tests/data_platform/utils/test_gate_checks.py`
- `/workspace/tests/data_platform/utils/conftest.py`
- Any remaining `/workspace/tests/data_platform/**` files still failing on the old storage API

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py` except you must not revert step 1
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/generate_features/**` except you must not revert step 4
- Historical curated `metadata.json` on disk
- Do not drop the `files` map from newly written curated metadata

## Contracts to lock

```text
class OutputConfig(BaseModel):
  filename: str = "dataset.csv"

Curate YAML:
  output:
    filename: mirrorview.csv

run_curation writes:
  relative_file_path = f"{relative_run_dir}/{rules.output.filename}"
  write_dataframe(filtered_df, relative_file_path)

build_curate_metadata still includes files: {"export": rules.output.filename}
source_preprocessed_runs: to_package_relative directories

_is_up_to_date current_runs: to_package_relative of each preprocess run dir
output lookup may still use latest_meta["files"]["export"] joined onto the latest curated run
  (keeping the files map is required; issue #85 drops it later)
```

## Test design

given curate YAML with `output.filename: mirrorview.csv`
when run_curation
then the export file is `{relative_run_dir}/mirrorview.csv`
and metadata files.export == "mirrorview.csv"
and source_preprocessed_runs entries look like data/{platform}/{id}/preprocessed/{timestamp}

given Bluesky up-to-date tests
when they seed source_preprocessed_runs
then they use the package-relative directory strings, not preprocessed/{timestamp}

given YAML that still has `output.stem`
when load_rules_config
then validation fails (no alias)

## Implementation notes

Follow implement-from-spec. Unattended.

Phase 5 units of work:

1. `OutputConfig.filename` and YAML configs
2. `run_curation` paths and source-run lists
3. Bluesky `_is_up_to_date`
4. Remaining tests (`gate_checks`, utils conftest)
5. Delete `relative_run_path` if unused
6. Full `tests/data_platform` suite

After this step the whole child issue must be green.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: exit 0.

## Must fail / not happen

- Keeping `OutputConfig.stem` or YAML `stem:`.
- Dropping curated `files`.
- Writing source-run strings relative only to the dataset root.
- Rewriting historical JSON.
- Calling `filename_for` or `storage.records_filename`.
- Bundling preprocess metadata slimming or dropping raw `sync_timestamp`.
