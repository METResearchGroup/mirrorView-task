# Step 5: Production run on 500 and write RESULTS.md

## Goal

Only after **explicit user approval** of Step-4 smoke: run both prompt arms on the **full** frozen 500-row subset, score both runs, and write `experiments/llm_prompt_engineering_2026_08_05/RESULTS.md` with the exact two-row metrics table frozen in Step 3.

## Approval gate (mandatory)

**Do not execute any command in this step until Step 4 smoke was approved by the user in conversation.**

If approval is missing: stop immediately. Do not run the classifier without `--limit`. Do not write `RESULTS.md`.

## Caller / unit of work

**Production sizes (exact):**

| Flag | Production value |
|------|------------------|
| `--arm` | `both` |
| `--limit` | omitted (all 500 rows) |
| `--model` | `gpt-5.4-nano` |
| `--subset` | `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` |

**In scope:** full dual-arm classify; evaluate both run dirs; write `RESULTS.md`; README note of production artifact paths.

**Out of scope:** changing prompts/schemas; resampling the subset; re-running smoke; editing `shared/**`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| Step-4 smoke run dirs + user approval message | Gate evidence |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/run_classifier.py` | Production CLI |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/evaluate.py` | Dual-arm markdown helper |
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-08-05_llm_prompt_engineering_cba3e0/steps/step3.md` | Exact RESULTS.md table shape |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` | n=500 |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/RESULTS.md` (create/overwrite with production metrics)
- Runtime artifacts under `experiments/llm_prompt_engineering_2026_08_05/outputs/**` (production runs)
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/README.md` (link to RESULTS + production commands only)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` (must remain the frozen Step-1 sample)
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- Do not `git commit` unless the user asks

## Production procedure (exact)

Requires `OPENAI_API_KEY` in repo-root `.env`.

```bash
cd /Users/mark/src/work/mirrorView-task

# GATE: only after explicit user approval of Step 4 smoke
test -f experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv

PYTHONPATH=. uv run python -c "
import pandas as pd
df = pd.read_csv('experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv')
assert len(df) == 500
print('subset n=500 OK')
"

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/run_classifier.py \
  --arm both --model gpt-5.4-nano
# Record:
#   CONTROL_RUN=.../outputs/control/outputs/<TS>
#   TUNED_RUN=.../outputs/tuned/outputs/<TS>
# Expect: 500 prediction JSON files per arm

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/evaluate.py \
  --control-run-dir "\$CONTROL_RUN" \
  --tuned-run-dir "\$TUNED_RUN" \
  --write-results experiments/llm_prompt_engineering_2026_08_05/RESULTS.md
```

If `--write-results` was not implemented as a flag, equivalently: call the dual-arm helper from a one-liner and write the returned markdown to `RESULTS.md` — the file contents must still match the Step-3 shape.

### RESULTS.md must include

1. Model id `gpt-5.4-nano`
2. Subset path + `n=500` + `seed=42`
3. Absolute or repo-relative control and tuned run dirs
4. Two-row table with columns: Arm, Accuracy, Precision, Recall, F1
5. Row labels exactly `control` and `prompt-tuned`
6. Metrics to 4 decimal places

## Exact verification commands

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python -c "
import json
from pathlib import Path
import os
import pandas as pd

for name in ('CONTROL_RUN', 'TUNED_RUN'):
    assert name in os.environ and os.environ[name], name

for run in (os.environ['CONTROL_RUN'], os.environ['TUNED_RUN']):
    p = Path(run)
    preds = [x for x in p.glob('*.json') if x.name != 'metadata.json']
    assert len(preds) == 500, (run, len(preds))

results = Path('experiments/llm_prompt_engineering_2026_08_05/RESULTS.md')
text = results.read_text()
assert 'gpt-5.4-nano' in text
assert 'control' in text.lower()
assert 'prompt-tuned' in text
for col in ('Accuracy', 'Precision', 'Recall', 'F1'):
    assert col in text, col
print('production RESULTS OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Gate | user approved Step 4 first | Production started without approval |
| Predictions | 500 JSON rows per arm | Partial / smoke-sized run used as production |
| Subset | still the Step-1 frozen CSV (n=500, seed 42) | Resampled mid-flight |
| RESULTS.md | two-row table with four metrics + provenance | Missing arm / wrong columns |
| Schema/prompts | untouched under `shared/` and existing prompt files | Prompt redesign |

## Done when

1. Explicit Step-4 approval was recorded before this step ran.
2. Both arms completed on all 500 subset rows.
3. `experiments/llm_prompt_engineering_2026_08_05/RESULTS.md` exists with the Step-3 table shape filled with production metrics.
4. README points at RESULTS and the production commands.
5. No changes to `shared/schemas.py`, `shared/data/`, or the prompt template files.
