# Step 3: Score predictions and define the RESULTS table shape

## Goal

Add `experiments/llm_prompt_engineering_2026_08_05/evaluate.py` that reads one arm’s timestamped runner output directory, joins predictions to gold `keep_remove_label`, and reports **accuracy, precision, recall, F1** (positive class = remove / label `1`). Freeze the exact two-row `RESULTS.md` markdown shape for Step 5 to fill after production.

Do **not** run the LLM in this step. Do **not** write production `RESULTS.md` yet (may print a dry markdown table to stdout only).

## Caller / unit of work

**Main caller:** `evaluate.py` CLI:

1. Take `--run-dir` pointing at a runner folder: `.../outputs/{arm}/outputs/{timestamp}/`.
2. Load all per-item `*.json` files (skip `metadata.json`).
3. Build parallel `y_true` / `y_pred` from `keep_remove_label` and `predicted_label`.
4. Compute the four metrics with `sklearn.metrics` (`zero_division=0`).
5. Print a one-row summary; optionally print the markdown table fragment for that arm.

Also expose a pure function usable by Step 5:

`compute_metrics(y_true, y_pred) -> dict[str, float]` with keys `accuracy`, `precision`, `recall`, `f1`.

**In scope:** `evaluate.py` + README evaluate command + RESULTS table contract below.

**Out of scope:** live LLM, production dual-arm run, committing, editing prompts/schemas.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/runner.py` | `_hard_label_metrics` — same four metrics, positive = remove |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/README.md` | Two-row RESULTS table requirement |
| `/Users/mark/src/work/mirrorView-task/shared/schemas.py` | `is_remove` → predicted_label mapping (Step 2) |
| Step 2 writer row contract | Fields present on each JSON prediction |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/evaluate.py` (create)
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/README.md` (append evaluate + RESULTS shape notes)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/run_classifier.py` (unless a missing writer field blocks evaluate — then add only the missing field)
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/RESULTS.md` — do **not** create as production results in this step
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`

## Contracts to freeze

### Metric definitions

Match `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/runner.py` `_hard_label_metrics`:

| Metric | Call |
|--------|------|
| accuracy | `accuracy_score(y_true, y_pred)` |
| precision | `precision_score(..., zero_division=0)` |
| recall | `recall_score(..., zero_division=0)` |
| f1 | `f1_score(..., zero_division=0)` |

- Labels are integers: `0` = keep, `1` = remove.
- Positive class for precision/recall/F1 is **remove** (`1`), sklearn default for binary.

### Loading predictions from a run dir

1. Require `run_dir / "metadata.json"` exists.
2. For every `*.json` in `run_dir` except `metadata.json`, load JSON and require keys: `message_id`, `keep_remove_label`, `predicted_label`, `arm`.
3. Raise `ValueError` if zero prediction files found.
4. Raise `ValueError` if any `message_id` duplicates appear in the run.
5. Return a `pd.DataFrame` plus the metrics dict.

### Dual-arm helper (for Step 5)

Provide something equivalent to:

`evaluate_two_arms(control_run_dir, tuned_run_dir) -> str`

that returns the exact markdown table body below with numeric cells filled (4 decimal places).

### RESULTS.md table shape (exact)

Step 5 will write this file. Step 3 freezes the shape:

```markdown
# Prompt engineering keep/remove classifier results

- Model: `gpt-5.4-nano`
- Subset: `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` (n=500, seed=42)
- Response schema: `shared.schemas.IsRemoveResult`
- Positive class for precision / recall / F1: remove (`keep_remove_label=1`)
- Control run dir: `<path>`
- Tuned run dir: `<path>`

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| control | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| prompt-tuned | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
```

Row labels are exactly `control` and `prompt-tuned` (second row maps to `--arm tuned`).

### CLI

```text
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/evaluate.py \
  --run-dir experiments/llm_prompt_engineering_2026_08_05/outputs/control/outputs/<TS>
```

Optional: `--control-run-dir` + `--tuned-run-dir` to print the full two-row markdown table to stdout (still no file write of `RESULTS.md` in this step unless `--write-results` is explicitly passed — default off; Step 5 owns writing the file).

## Exact commands

Without a live run dir yet, unit-check the pure metrics helper:

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python -c "
from experiments.llm_prompt_engineering_2026_08_05.evaluate import compute_metrics
m = compute_metrics([0, 1, 1, 0], [0, 1, 0, 0])
assert set(m) == {'accuracy', 'precision', 'recall', 'f1'}
assert abs(m['accuracy'] - 0.75) < 1e-9
# TP=1, FP=0, FN=1 → precision=1.0, recall=0.5, f1=2/3
assert abs(m['precision'] - 1.0) < 1e-9
assert abs(m['recall'] - 0.5) < 1e-9
print('compute_metrics OK', m)
"

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/evaluate.py --help
```

If a Step-4 smoke run dir already exists, also:

```bash
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/evaluate.py \
  --run-dir experiments/llm_prompt_engineering_2026_08_05/outputs/control/outputs/<TS>
# expect: printed accuracy/precision/recall/f1; exit 0
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| `compute_metrics` | known toy labels match expected floats | Wrong positive class / missing metric |
| CLI help | exits 0 | Import / argparse failure |
| RESULTS shape | README or module docstring shows the exact two-row table | Vague / extra metric columns |
| No production RESULTS file | `RESULTS.md` absent or untouched | Premature production RESULTS write |

## Done when

1. `evaluate.py` exposes `compute_metrics` and can score a runner run dir.
2. Metrics match the api_baselines hard-label definitions (remove = positive).
3. The two-row RESULTS markdown shape is documented exactly as above.
4. No production `RESULTS.md` written as the Step-5 deliverable.
5. No LLM calls in this step.
