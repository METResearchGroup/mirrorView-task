# Step 3: Wire evaluation / RESULTS shape for v2 (n=1000, Qwen header)

## Goal

Add `experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py` that **imports** scoring helpers from v1 (`compute_metrics`, `load_predictions`, `score_run_dir`, `format_metrics_row`) and emits the same two-row RESULTS markdown shape with v2 provenance: model `qwen/qwen3.6-plus`, subset path under the v2 tree, **`n=1000`**, seed 42.

Do **not** run the LLM. Do **not** write production `RESULTS.md` yet (stdout / optional `--write-results` off by default).

## Caller / unit of work

**Main caller:** v2 `evaluate.py` CLI (same flag surface as v1):

1. `--run-dir` → print one-arm metrics via imported `score_run_dir`.
2. `--control-run-dir` + `--tuned-run-dir` → build two-row markdown; optional `--write-results PATH`.
3. Local `evaluate_two_arms(...)` must hardcode header `n=1000` (v1’s helper hardcodes `n=500` — **do not** edit v1; reimplement only the markdown assembly in v2 while importing metric loaders).

**In scope:** v2 `evaluate.py` + README evaluate command + RESULTS table contract below.

**Out of scope:** live LLM, production dual-arm run, committing, editing v1 / `shared/**` / prompts.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/evaluate.py` | Import `compute_metrics`, `load_predictions`, `score_run_dir`, `format_metrics_row`; note hardcoded `n=500` in v1 `evaluate_two_arms` |
| `/workspace/docs/plans/2026-08-05_llm_prompt_engineering_cba3e0/steps/step3.md` | Table shape lineage |
| `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` | n=1000 provenance |

## Files allowed to change

- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py` (create)
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/README.md` (append evaluate + RESULTS shape notes)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/**`
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv`
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md` — do **not** create as production results in this step
- `/workspace/pyproject.toml`

## Contracts to freeze

### Metric definitions

Reuse v1 `compute_metrics` unchanged (remove = positive class / label `1`).

### RESULTS.md table shape (exact)

Step 5 will write this file. Step 3 freezes the shape:

```markdown
# Prompt engineering keep/remove classifier results

- Model: `qwen/qwen3.6-plus`
- Subset: `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` (n=1000, seed=42, balanced 500 keep / 500 remove)
- Response schema: `shared.schemas.IsRemoveResult`
- Positive class for precision / recall / F1: remove (`keep_remove_label=1`)
- Control run dir: `<path>`
- Tuned run dir: `<path>`

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| control | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| prompt-tuned | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
```

Row labels are exactly `control` and `prompt-tuned`.

### Defaults

| Name | Value |
|------|-------|
| `DEFAULT_MODEL` | `qwen/qwen3.6-plus` |
| `DEFAULT_SUBSET_PATH` | `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` |

### CLI

```text
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \
  --run-dir experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control/outputs/<TS>

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \
  --control-run-dir <CONTROL_TS> --tuned-run-dir <TUNED_TS> \
  [--model qwen/qwen3.6-plus] \
  [--write-results experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md]
```

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run python -c "
from experiments.llm_prompt_engineering_v2_2026_08_05.evaluate import compute_metrics, evaluate_two_arms, DEFAULT_MODEL
from pathlib import Path
assert DEFAULT_MODEL == 'qwen/qwen3.6-plus'
m = compute_metrics([0, 1, 1, 0], [0, 1, 0, 0])
assert set(m) == {'accuracy', 'precision', 'recall', 'f1'}
assert abs(m['accuracy'] - 0.75) < 1e-9
# dry markdown assembly without real run dirs: inspect source / docstring for n=1000
import inspect
from experiments.llm_prompt_engineering_v2_2026_08_05 import evaluate as ev
src = inspect.getsource(ev.evaluate_two_arms)
assert 'n=1000' in src
assert 'n=500' not in src
print('v2 evaluate contracts OK', m)
"

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py --help
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| `compute_metrics` | imported from v1; toy labels match | Local reimplementation drift |
| Header | `n=1000` + Qwen model id | Still says `n=500` / `gpt-5.4-nano` |
| CLI help | exits 0 | Import / argparse failure |
| No production RESULTS file | `RESULTS.md` absent or untouched | Premature production RESULTS write |
| v1 untouched | no edits under v1 evaluate | Patched v1 to accept n |

## Done when

1. v2 `evaluate.py` imports v1 scorers and exposes v2 `evaluate_two_arms` with `n=1000` + Qwen defaults.
2. RESULTS markdown shape is documented exactly as above.
3. No production `RESULTS.md` written as the Step-5 deliverable.
4. No LLM calls; no edits to v1 or `shared/`.
