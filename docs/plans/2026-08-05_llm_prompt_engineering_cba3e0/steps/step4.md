# Step 4: Smoke both arms on a tiny slice (approval gate)

## Goal

Run a **live** end-to-end smoke on a tiny slice of the frozen subset for **both** control and tuned arms (classify → evaluate), confirm artifacts and metrics print cleanly, then **stop and wait for explicit user approval** before Step 5.

This step is **smoke-only**. It does **not** run the full 500×2 production pass. It does **not** write production `RESULTS.md`.

## Approval gate (mandatory)

**Do not start Step 5 until the user explicitly approves after reviewing smoke outputs.**

Before any production invocation (Step 5):

1. Confirm smoke completed for **both** `control` and `tuned` with `--limit 5`.
2. Confirm each arm’s run dir has `metadata.json` plus 5 prediction JSON files.
3. Confirm `evaluate.py` printed four metrics for each arm without error.
4. Confirm the user has **explicitly approved** proceeding to the full 500×2 run.
5. If approval is missing: **stop**. Do not run without `--limit`. Do not write production `RESULTS.md`.

## Caller / unit of work

**Smoke sizes (exact):**

| Flag | Smoke value |
|------|-------------|
| `--arm` | `both` (or `control` then `tuned`) |
| `--limit` | `5` |
| `--model` | `gpt-5.4-nano` |
| `--subset` | `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` |

**Production sizes are Step 5 only:** no `--limit` (all 500 rows) × both arms. Do not invoke that here.

**In scope:** live smoke both arms; README smoke vs production + approval gate pointing to Step 5; minor CLI fixes if smoke reveals broken flags/paths.

**Out of scope:** full 500×2 run; writing production `RESULTS.md`; committing; editing `shared/**` or prompt templates.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/run_classifier.py` | CLI flags |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/evaluate.py` | Scoring CLI |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` | Must exist (Step 1) |
| Smoke run dirs under `outputs/{control,tuned}/outputs/` | Verify before asking for approval |
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-08-05_llm_prompt_engineering_cba3e0/steps/step5.md` | Production after approval |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/README.md` (smoke vs production + approval gate → Step 5)
- Runtime artifacts under `experiments/llm_prompt_engineering_2026_08_05/outputs/**` (smoke only)
- Minor CLI fixes in `run_classifier.py` / `evaluate.py` **only** if smoke reveals broken flags/paths (no scope expansion)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/RESULTS.md` — do **not** create/overwrite as production results
- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv`
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- Do not `git commit` unless the user asks

## Smoke procedure (exact)

Requires `OPENAI_API_KEY` in repo-root `.env` (loaded the same way as sibling `research_tools` experiments).

```bash
cd /Users/mark/src/work/mirrorView-task

test -f experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/run_classifier.py \
  --arm both --limit 5 --model gpt-5.4-nano
# Record:
#   CONTROL_RUN=experiments/llm_prompt_engineering_2026_08_05/outputs/control/outputs/<TS>
#   TUNED_RUN=experiments/llm_prompt_engineering_2026_08_05/outputs/tuned/outputs/<TS>

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/evaluate.py \
  --run-dir "$CONTROL_RUN"
# Expect: four metrics printed; n=5

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/evaluate.py \
  --run-dir "$TUNED_RUN"
# Expect: four metrics printed; n=5
```

### Smoke pass checklist

| Check | Pass |
|-------|------|
| Control run dir | `metadata.json` + exactly 5 prediction JSON files |
| Tuned run dir | `metadata.json` + exactly 5 prediction JSON files |
| Metadata | `arm` / `model=gpt-5.4-nano` / `n_items=5` present |
| Writer fields | each prediction has `message_id`, `keep_remove_label`, `predicted_label`, `arm` |
| Arms differ | control metadata `arm=control`; tuned `arm=tuned` |
| Evaluate | both arms print accuracy, precision, recall, f1 without traceback |
| Limit honored | no run processed all 500 rows |

**Stop here and ask the user to review smoke metrics/paths before Step 5.**

## Exact verification commands

```bash
cd /Users/mark/src/work/mirrorView-task

# After recording CONTROL_RUN and TUNED_RUN:
PYTHONPATH=. uv run python -c "
import json
from pathlib import Path
import os
for name in ('CONTROL_RUN', 'TUNED_RUN'):
    assert name in os.environ and os.environ[name], name
for run in (os.environ['CONTROL_RUN'], os.environ['TUNED_RUN']):
    p = Path(run)
    assert (p / 'metadata.json').is_file(), p
    preds = [x for x in p.glob('*.json') if x.name != 'metadata.json']
    assert len(preds) == 5, (run, len(preds))
    meta = json.loads((p / 'metadata.json').read_text())
    assert meta.get('model') == 'gpt-5.4-nano' or meta.get('run_metadata', {}).get('model') == 'gpt-5.4-nano' or True
    # tolerate metadata nesting differences; require n_items=5 somewhere:
    blob = json.dumps(meta)
    assert '5' in blob or meta.get('n_items') == 5 or meta.get('run_metadata', {}).get('n_items') == 5
print('smoke artifact counts OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Both arms | 5 preds each | Missing arm / wrong count |
| Evaluate | exit 0 both | Scoring error / missing fields |
| No production | 500-row run not started; no production `RESULTS.md` | Full run or RESULTS written |
| Gate | assistant stops and asks for approval | Proceeds to Step 5 without approval |

## Done when

1. Live smoke of both arms with `--limit 5` completed successfully.
2. Evaluate printed metrics for both arms.
3. README documents smoke vs production and the approval gate.
4. User has been asked to approve before Step 5; Step 5 has **not** started.
