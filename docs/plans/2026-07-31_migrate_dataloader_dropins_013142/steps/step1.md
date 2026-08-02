# Step 1: Point Part 1 pilot-results callers at the shared loader

## Goal

Replace hardcoded Part 1 pilot results CSV paths with `shared.data.dataloader.load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)`. Keep every post-load filter and transform that already exists in these files. No reshape of the raw frame beyond what each script already does.

## Caller / unit of work

**Main callers (in this step):**

1. `experiments/free_response_analysis_2026_04_28/main.py` — phase-1 free-response filter/export
2. `experiments/mirrors_content_analysis_2026_04_24/dataloader.py` — pinned pilot ingress for content analysis
3. `experiments/basic_summary_stats_2026_04_27/summary_stats.py` — party × condition tables
4. `experiments/basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py` — toxicity × party removal rates
5. `experiments/predict_keep_remove_2026_05_07/generate_dataset_metrics.py` — fallback export discovery when preferred dataloader fails

**In scope:** Swap ingress only to the registered Part 1 pilot results dataset. Remove `scripts/mirrorview_pilot_data_*.csv` discovery / pinned-path reads from these five files.

**Out of scope:** Part 2 stimuli migrations (Step 2); `total_attrition.py`; keep/remove slim CSV rebuild; `05_07` label joins redesign; registry/dataloader changes; deleting legacy CSVs.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py` | Target API: `load_dataset` |
| `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` | Constant `STUDY_PHASE_2_PART_1_RESULTS_PILOT` |
| `/Users/mark/src/work/mirrorview-wt/strategy_planning/migrate_to_single_dataloader_2026_07_31/migration_plan.md` | Phase 1 inventory |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-07-31_migrate_dataloader_dropins_013142/plan.md` | Parent plan |
| Each file in “Files allowed to change” | Current path / discovery logic |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/free_response_analysis_2026_04_28/main.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/mirrors_content_analysis_2026_04_24/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/basic_summary_stats_2026_04_27/summary_stats.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_05_07/generate_dataset_metrics.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/raw/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/basic_summary_stats_2026_04_27/total_attrition.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_05_07/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/**`
- Any Part 2 stimuli consumers listed in Step 2

## Per-file changes (exact)

### 1. `free_response_analysis_2026_04_28/main.py`

- Remove `SOURCE_CSV = PROJECT_ROOT / "scripts" / "mirrorview_pilot_data_2026_04_28-16:31:47.csv"`.
- Import `load_dataset` and `STUDY_PHASE_2_PART_1_RESULTS_PILOT`.
- Change `generate_filtered_dataframe` so it loads the pilot results via `load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)` instead of `pd.read_csv(source_csv)`. Keep the existing column checks and phase-1 reflection/influence filters. Keep writing `FILTERED_CSV`.
- If `source_csv: Path` remains as a parameter for tests/overrides, default it unused; preferred: drop the path parameter and always use the shared loader for the raw ingress.

### 2. `mirrors_content_analysis_2026_04_24/dataloader.py`

- In `get_latest_mirrorview_run_data`, replace `pd.read_csv(self.PINNED_EXPORT_PATH, low_memory=False)` with `load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)`.
- Remove `PINNED_EXPORT_FILENAME` / `PINNED_EXPORT_PATH` (or leave unused only if something external still references them — prefer delete).
- Keep `transform_latest_mirrorview_run_data` byte-for-byte in behavior.
- Update `last_loaded_export_path` if still useful: set it to `registry.resolve_path(STUDY_PHASE_2_PART_1_RESULTS_PILOT)` so prints still show a path.

### 3. `basic_summary_stats_2026_04_27/summary_stats.py`

- Delete `find_latest_export_csv` and `copy_latest_export_csv` and the `SCRIPTS_DIR` / `LOCAL_DATA_CSV` copy workflow.
- In `main`, load with `load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)` and print row / prolific counts as today.
- Do **not** switch to Part 1 full results in this step (product choice deferred to Phase 3 of the migration inventory).

### 4. `basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py`

- Stop importing / calling `find_latest_export_csv` from `summary_stats`.
- Load `STUDY_PHASE_2_PART_1_RESULTS_PILOT` via `load_dataset` in `main`.
- Keep `moderation_phase_frame` and all reporting logic unchanged.

### 5. `predict_keep_remove_2026_05_07/generate_dataset_metrics.py`

- Preferred path (`Dataloader().load_training_dataframe()`) stays.
- Fallback path: replace `_choose_latest_valid_export_csv(...)` + `pd.read_csv(export_path)` with `raw = load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)`, then keep `pilot.transform_latest_mirrorview_run_data(raw)` and the linked-fate / keep-remove filters.
- Delete `_choose_latest_valid_export_csv` and the `mirrorview_pilot_data_*.csv` regex helpers **if** nothing else in this file uses them after the swap.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

# Confirm pilot CSV present
test -f shared/data/raw/study_phase_2_part_1/results/pilot.csv && echo OK_PILOT

# Shared loader shape
PYTHONPATH=. uv run python - <<'PY'
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_1_RESULTS_PILOT
df = load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)
assert "prolific_id" in df.columns and "phase1_pair_reflection_text" in df.columns
print("PILOT_ROWS", len(df), "PILOT_COLS", len(df.columns))
PY

# Mirrors ingress (no transform write required)
PYTHONPATH=. uv run python - <<'PY'
from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader
raw = Dataloader().get_latest_mirrorview_run_data()
assert len(raw) > 0
print("MIRRORS_RAW_ROWS", len(raw))
PY
```

### Expected outputs (pass signals)

```text
OK_PILOT
PILOT_ROWS 8985 PILOT_COLS 41
MIRRORS_RAW_ROWS 8985
```

(Row count must match the on-disk pilot CSV; if the local file differs, print the actual count and assert it equals `len(pd.read_csv("shared/data/raw/study_phase_2_part_1/results/pilot.csv"))`.)

## Pass / fail

**Pass:**

- All five allowed files load Part 1 pilot results only through `load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)` (or via mirrors `get_latest_mirrorview_run_data` which itself uses that call).
- No remaining references in those five files to `scripts/mirrorview_pilot_data` path strings or `PINNED_EXPORT_PATH` reads.
- `transform_latest_mirrorview_run_data` and free-response / summary filters unchanged in behavior.
- Commands above succeed when the pilot CSV is present.

**Fail:**

- Any of the five files still glob `scripts/` for study results.
- Switching summary stats to Part 1 **full** results.
- Changing shared registry / loader code.
- Editing `total_attrition.py` or Phase 2 / 3 migration targets.
