# Step 3: Smoke-check both registry loads from the migrated call sites

## Goal

Prove the Step 1 and Step 2 migrations: both registry datasets load with expected shapes, and one representative caller from each batch no longer depends on the old hardcoded path constants.

## Caller / unit of work

**Main callers for verification:**

- Part 1 batch: `experiments.mirrors_content_analysis_2026_04_24.dataloader.Dataloader.get_latest_mirrorview_run_data`
- Part 2 batch: `experiments.scaled_mirrors_generation_2026_06_02.validate_mirrors_equal_lengths` (module load path) **or** a one-liner that imports the truncate/match-lengths helper added in Step 2

**In scope:** Read-only smoke commands; optional tiny doc fix inside an already-migrated file if a print string still claims `scripts/` or `combined_flips` incorrectly.

**Out of scope:** Implementing Step 1/2 file edits (must already be done); Phase 2/3 migrations; adding unit test packages; changing registry/loader.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| All Step 1 + Step 2 allowed files | Confirm no leftover old path constants |
| `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` | Resolve paths for assertions |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-07-31_migrate_dataloader_dropins_013142/plan.md` | Done criteria |

## Files allowed to change

- None required. Only touch a Step 1/2 allowed file if smoke reveals a leftover path string that was meant to be removed in that step.

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/raw/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/basic_summary_stats_2026_04_27/total_attrition.py`
- Phase 2/3 items in `strategy_planning/migrate_to_single_dataloader_2026_07_31/migration_plan.md`

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

# 1) Grep gate: migrated files must not retain old default path literals
rg -n "scripts/mirrorview_pilot_data|PINNED_EXPORT_PATH|combined_flips/flips\.csv" \
  experiments/free_response_analysis_2026_04_28/main.py \
  experiments/mirrors_content_analysis_2026_04_24/dataloader.py \
  experiments/basic_summary_stats_2026_04_27/summary_stats.py \
  experiments/basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py \
  experiments/predict_keep_remove_2026_05_07/generate_dataset_metrics.py \
  experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths.py \
  experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths_v2.py \
  experiments/match_lengths_original_mirrors_2026_06_19/run_ablations.py \
  experiments/truncate_posts_2026_06_19/truncate_flips.py \
  experiments/truncate_posts_2026_06_19/truncate_flips_v2.py \
  experiments/truncate_posts_2026_06_19/truncate_flips_v3.py \
  experiments/truncate_posts_2026_06_19/truncation_v5/generate_flips.py \
  experiments/scaled_mirrors_generation_2026_06_02/validate_mirrors_equal_lengths.py \
  && echo "UNEXPECTED_MATCHES" || echo "GREP_CLEAN"

# 2) End-to-end load smoke for both datasets + one caller each
PYTHONPATH=. uv run python - <<'PY'
from shared.data.dataloader import load_dataset
from shared.data import registry
from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader

pilot = load_dataset(registry.STUDY_PHASE_2_PART_1_RESULTS_PILOT)
stim = load_dataset(registry.STUDY_PHASE_2_PART_2_STIMULI)
raw = Dataloader().get_latest_mirrorview_run_data()

assert len(pilot) == len(raw)
assert len(stim) == 10000
assert "mirrored_text" in stim.columns
print("SMOKE_PILOT", len(pilot))
print("SMOKE_STIM", len(stim))
print("SMOKE_MIRRORS_CALLER", len(raw))
print("STEP3_OK")
PY
```

### Expected outputs (pass signals)

```text
GREP_CLEAN
SMOKE_PILOT 8985
SMOKE_STIM 10000
SMOKE_MIRRORS_CALLER 8985
STEP3_OK
```

(`8985` is the current local pilot row count; if the on-disk pilot differs, both `SMOKE_PILOT` and `SMOKE_MIRRORS_CALLER` must still match each other and the file.)

**Fail signals:**

- `UNEXPECTED_MATCHES` from the grep (any hit in the listed files).
- `FileNotFoundError` / `KeyError` from `load_dataset`.
- Mirrors caller still reading a missing pinned export under the experiment directory.

## Pass / fail

**Pass:** Grep is clean on all thirteen Phase 1 files; smoke script prints `STEP3_OK`; pilot and stimuli shapes match expectations; mirrors caller equals pilot row count.

**Fail:** Any Phase 1 file still hardcodes the old paths; smoke fails; or this step is used to start Phase 2/3 work.
