# Step 1: Freeze the 500-post evaluation subset

## Goal

Load Study Phase 2 Part 2 keep/remove labels from the shared catalog, draw a **random** sample of exactly **500** rows with seed **42**, write `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv`, and leave that CSV ready to commit so control and tuned arms share one immutable eval set.

Do **not** call any LLM in this step.

## Caller / unit of work

**Main caller:** `experiments/llm_prompt_engineering_2026_08_05/build_subset.py` as a CLI:

1. Load `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via `shared.data.dataloader.load_dataset`.
2. Random-sample 500 rows with `random_state=42` (no stratification).
3. Write `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` with the same columns as the source CSV.
4. Print row count and path; exit 0.

**In scope:** `build_subset.py` + writing `subset_labels.csv`.

**Out of scope:** LLM calls, `run_classifier.py`, `evaluate.py`, `RESULTS.md`, edits to `shared/**`, prompt redesign, stratification.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/README.md` | Subset size = 500; git-track the CSV |
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-08-05_llm_prompt_engineering_cba3e0/plan.md` | Confirmed random sample |
| `/Users/mark/src/work/mirrorView-task/shared/data/dataloader.py` | `load_dataset(name)` |
| `/Users/mark/src/work/mirrorView-task/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| `/Users/mark/src/work/mirrorView-task/shared/data/transformed/study_phase_2_part_2/README.md` | Columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label` |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/paths.py` | Loader pattern to mirror (load + column checks) |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/build_subset.py` (create)
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` (create by running the script)
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/README.md` (append the exact build-subset command only)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py`
- Do **not** create `run_classifier.py`, `evaluate.py`, or `RESULTS.md` in this step
- Do not `git commit` unless the user asks

## Contracts to freeze

### Constants

| Name | Value |
|------|-------|
| Sample size | `500` |
| Seed | `42` |
| Output path | `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` |
| Source dataset | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |

### Sampling behavior

1. Load full frame with `load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)`.
2. Require columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`.
3. Assert `decision` values ⊆ `{"keep", "remove"}` after lowercase strip if needed.
4. Assert `len(df) >= 500` (full corpus ≈ 8791).
5. `df.sample(n=500, random_state=42).reset_index(drop=True)` — **simple random**, not stratified.
6. Write CSV with `index=False`, same column order as the loaded frame (or at least the five required columns above).
7. Raise `ValueError` if the output already exists and the caller did not pass `--force` (add `--force` to overwrite). Default without `--force`: refuse to clobber a committed subset.

### CLI

```text
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/build_subset.py [--force]
```

Defaults: `--sample-size 500`, `--seed 42` may be exposed as flags but production defaults must be exactly those values.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/build_subset.py

PYTHONPATH=. uv run python -c "
import pandas as pd
from pathlib import Path
p = Path('experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv')
assert p.is_file(), p
df = pd.read_csv(p)
assert len(df) == 500, len(df)
for col in ('message_id', 'original_text', 'mirror_text', 'decision', 'keep_remove_label'):
    assert col in df.columns, col
assert df['message_id'].is_unique
assert set(df['decision'].astype(str).str.lower().str.strip()) <= {'keep', 'remove'}
print('subset OK', len(df), 'keep', (df['decision'].str.lower()=='keep').sum(),
      'remove', (df['decision'].str.lower()=='remove').sum())
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Script exits | exit code 0 | Non-zero / traceback |
| Row count | exactly 500 | Any other count |
| Columns | five required columns present | Missing column |
| `message_id` | unique within subset | Duplicates |
| `decision` | only keep/remove | Other values |
| Sampling | deterministic under seed 42 (re-run with `--force` yields identical CSV) | Different rows on re-run with same seed |
| No LLM | no OpenAI / runner imports in `build_subset.py` | Runner or API key required |

## Done when

1. `build_subset.py` exists and is runnable from repo root with `PYTHONPATH=.`.
2. `subset_labels.csv` has exactly 500 rows and the required columns.
3. Re-running with `--force` and seed 42 reproduces the same `message_id` set.
4. README documents the build-subset command.
5. No LLM code and no changes under `shared/`.
