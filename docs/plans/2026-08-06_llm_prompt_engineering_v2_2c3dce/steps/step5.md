# Step 5: Production run on 1,000 and write RESULTS.md

## Goal

Only after **explicit user approval** of Step-4 smoke: run both prompt arms on the **full** frozen balanced 1000-row subset with **`qwen/qwen3.6-plus`**, score both runs, and write `experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md` with the exact two-row metrics table frozen in Step 3.

## Approval gate (mandatory)

**Do not execute any command in this step until Step 4 smoke was approved by the user in conversation.**

If approval is missing: stop immediately. Do not run the classifier without `--limit`. Do not write `RESULTS.md`.

## Caller / unit of work

**Production sizes (exact):**

| Flag | Production value |
|------|------------------|
| `--arm` | `both` |
| `--limit` | omitted (all 1000 rows) |
| `--model` | `qwen/qwen3.6-plus` |
| `--subset` | `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` |

**In scope:** full dual-arm classify; evaluate both run dirs; write `RESULTS.md`; README note of production artifact paths.

**Out of scope:** changing prompts/schemas; resampling the subset; re-running smoke; editing `shared/**` or the v1 tree.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| Step-4 smoke run dirs + user approval message | Gate evidence |
| `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py` | Production CLI |
| `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py` | Dual-arm markdown helper |
| `/workspace/docs/plans/2026-08-06_llm_prompt_engineering_v2_2c3dce/steps/step3.md` | Exact RESULTS.md table shape |
| `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` | n=1000, 500/500 |

## Files allowed to change

- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md` (create/overwrite with production metrics)
- Runtime artifacts under `experiments/llm_prompt_engineering_v2_2026_08_05/outputs/**` (production runs)
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/README.md` (link to RESULTS + production commands only)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/**`
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` (must remain the frozen Step-1 balanced sample)
- `/workspace/pyproject.toml`
- Do not `git commit` unless the user asks

## Credentials (exact)

Same as Step 4 (Bedrock):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

## Production procedure (exact)

```bash
cd /workspace

# GATE: only after explicit user approval of Step 4 smoke
test -f experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
import pandas as pd
df = pd.read_csv('experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv')
assert len(df) == 1000
dec = df['decision'].astype(str).str.lower().str.strip()
assert (dec == 'keep').sum() == 500
assert (dec == 'remove').sum() == 500
print('subset n=1000 balanced OK')
"

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py \
  --arm both --model qwen/qwen3.6-plus
# Record:
#   CONTROL_RUN=.../outputs/control/outputs/<TS>
#   TUNED_RUN=.../outputs/tuned/outputs/<TS>
# Expect: 1000 predictions per arm

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \
  --control-run-dir "\$CONTROL_RUN" \
  --tuned-run-dir "\$TUNED_RUN" \
  --model qwen/qwen3.6-plus \
  --write-results experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md
```

### RESULTS.md must include

1. Model id `qwen/qwen3.6-plus`
2. Subset path + `n=1000` + `seed=42` + balanced 500/500 note
3. Control and tuned run dirs
4. Two-row table with columns: Arm, Accuracy, Precision, Recall, F1
5. Row labels exactly `control` and `prompt-tuned`
6. Metrics to 4 decimal places

## Exact verification commands

```bash
cd /workspace

PYTHONPATH=. uv run python -c "
import json
from pathlib import Path
import os

for name in ('CONTROL_RUN', 'TUNED_RUN'):
    assert name in os.environ and os.environ[name], name

for run in (os.environ['CONTROL_RUN'], os.environ['TUNED_RUN']):
    p = Path(run)
    jsonl = p / 'predictions.jsonl'
    if jsonl.is_file():
        n = sum(1 for line in jsonl.read_text().splitlines() if line.strip())
    else:
        n = len([x for x in p.glob('*.json') if x.name != 'metadata.json'])
    assert n == 1000, (run, n)

results = Path('experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md')
text = results.read_text()
assert 'qwen/qwen3.6-plus' in text
assert 'n=1000' in text
assert 'control' in text.lower()
assert 'prompt-tuned' in text
for col in ('Accuracy', 'Precision', 'Recall', 'F1'):
    assert col in text, col
print('v2 production RESULTS OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Gate | user approved Step 4 first | Production started without approval |
| Predictions | 1000 rows per arm | Partial / smoke-sized run used as production |
| Subset | still Step-1 frozen CSV (n=1000, 500/500, seed 42) | Resampled mid-flight |
| RESULTS.md | two-row table + Qwen + n=1000 provenance | Missing arm / wrong model / n=500 |
| v1 / shared | untouched | Edits to import sources |

## Done when

1. Explicit Step-4 approval was recorded before this step ran.
2. Both arms completed on all 1000 subset rows with `qwen/qwen3.6-plus`.
3. `experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md` exists with the Step-3 table shape filled with production metrics.
4. README points at RESULTS and the production commands.
5. No changes to `shared/schemas.py`, `shared/data/`, the v1 experiment tree, or prompt template files.
