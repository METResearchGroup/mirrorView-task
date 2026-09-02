# Step 5: Drop curated file maps and update in-repo readers

## Goal

New curated metadata omits `files`. Up-to-date checks and in-repo experiment scripts recompute the export path from the curation config filename (Step 2 already set `output.filename`). Remove `CuratePlatformSpec.record_noun`. Logs print the export filename. Do not migrate old curated JSON.

## Caller / unit of work

**Main caller:** `data_platform/curate/runner.py` `build_curate_metadata` / `run_curation`, and `data_platform/curate/curate_bluesky.py` `_is_up_to_date`.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run pytest tests/data_platform/curate -q
```

Expected: exit 0.

**In scope:** Curate metadata writer, Bluesky skip-if-fresh path, curate platform specs, experiment scripts that index `metadata["files"]["export"]`, curate tests, runbook curated notes if any.

**Out of scope:** Storage API; preprocess metadata; raw `sync_timestamp`; rewriting historical curated JSON.

## Decision (locked)

- Curated metadata keeps `dataset_id`, `name`, `rules_hash`, `source_preprocessed_runs`, `row_counts`, `filter_results`. No `files`.
- `_is_up_to_date` joins the latest curated run dir with `rules.output.filename` (full name). If that file is missing, treat as not up to date. Do not read `files.export`.
- `sample_data_to_mirror.py` and `count_missing_flips.py` open `metadata.json`’s parent joined with the yaml filename (same `mirrorview.csv` literal the configs use). Do not dual-read `files`.
- Delete `record_noun` from `CuratePlatformSpec` and platform CLIs.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/data_platform/curate/runner.py` | `files.export`, `record_noun` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/curate/curate_bluesky.py` | `_is_up_to_date` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/curate/curate_reddit.py` | `record_noun` |
| `/Users/mark/src/work/mirrorview-wt/data_platform/curate/curate_twitter.py` | `record_noun` |
| `/Users/mark/src/work/mirrorview-wt/tests/data_platform/curate/test_curate_bluesky.py` | Seeds `files.export` |
| `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` | `metadata["files"]["export"]` |
| `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py` | same |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/runner.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/curate_bluesky.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/curate_reddit.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/curate/curate_twitter.py`
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/curate/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py`
- `/Users/mark/src/work/mirrorview-wt/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` (curation bullets if they mention `files`)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py`
- Historical curated `metadata.json` under experiments (readers ignore extra keys; they must not require `files`)

## Implementation

`build_curate_metadata`: drop `export_filename` argument and the `files` key.

`_is_up_to_date`: `output_path = run_dirs[-1] / rules.output.filename` after resolving `run_dirs[-1]` the same way Step 2 storage does (package-relative dir). Compare `source_preprocessed_runs` and `rules_hash` as today.

Experiment scripts: use `mirrorview.csv` (import `POSTS_FILE` is wrong — export name is the yaml filename). Prefer loading the same `OutputConfig` / a module-level `CURATED_EXPORT_FILE = "mirrorview.csv"` constant in the experiment only if you refuse to parse yaml; the curated yaml filename is `mirrorview.csv` on all three platforms today. Do not read `metadata["files"]`.

Tests that write a fake latest curated metadata for the skip path must omit `files`. Assert `"files" not in metadata` on a real `run_curation` result.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/curate -q
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Exit 0.

If experiment scripts have no tests, `python -m py_compile` both experiment files:

```bash
PYTHONPATH=. uv run python -m py_compile \
  experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py \
  experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py
```

Exit 0.

## Must not happen

- Writing `files` “so old readers work”.
- `latest_meta.get("files", {}).get("export")` remaining anywhere under `data_platform/` or those two experiment files.
- Changing `source_preprocessed_runs` semantics (still all preprocessed dirs; package-relative from Step 2).
