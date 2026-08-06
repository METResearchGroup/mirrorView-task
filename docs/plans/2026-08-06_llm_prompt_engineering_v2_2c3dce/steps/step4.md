# Step 4: Smoke both arms on a tiny slice (approval gate)

## Goal

Run a **live** end-to-end smoke on a tiny slice of the v2 frozen subset for **both** control and tuned arms with **`qwen/qwen3.6-plus`**, confirm artifacts and metrics print cleanly, then **stop and wait for explicit user approval** before Step 5.

This step is **smoke-only**. It does **not** run the full 1000×2 production pass. It does **not** write production `RESULTS.md`.

## Approval gate (mandatory)

**Do not start Step 5 until the user explicitly approves after reviewing smoke outputs.**

Before any production invocation (Step 5):

1. Confirm smoke completed for **both** `control` and `tuned` with `--limit 5`.
2. Confirm each arm’s run dir has `metadata.json` plus 5 prediction JSON files (or consolidated `predictions.jsonl` with 5 rows).
3. Confirm v2 `evaluate.py` printed four metrics for each arm without error.
4. Confirm the user has **explicitly approved** proceeding to the full 1000×2 run.
5. If approval is missing: **stop**. Do not run without `--limit`. Do not write production `RESULTS.md`.

## Caller / unit of work

**Smoke sizes (exact):**

| Flag | Smoke value |
|------|-------------|
| `--arm` | `both` (or `control` then `tuned`) |
| `--limit` | `5` |
| `--model` | `qwen/qwen3.6-plus` |
| `--subset` | `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` |

**Production sizes are Step 5 only:** no `--limit` (all 1000 rows) × both arms. Do not invoke that here.

**In scope:** live smoke both arms; README smoke vs production + approval gate pointing to Step 5; minor CLI fixes if smoke reveals broken flags/paths.

**Out of scope:** full 1000×2 run; writing production `RESULTS.md`; committing; editing `shared/**`, v1 tree, or prompt templates.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py` | CLI flags |
| `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py` | Scoring CLI |
| `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` | Must exist (Step 1) |
| `/workspace/AGENTS.md` | Export `LAB_AWS_*` → `AWS_*` for Bedrock in cloud |
| Smoke run dirs under `outputs/{control,tuned}/outputs/` | Verify before asking for approval |

## Files allowed to change

- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/README.md` (smoke vs production + approval gate → Step 5)
- Runtime artifacts under `experiments/llm_prompt_engineering_v2_2026_08_05/outputs/**` (smoke only)
- Minor CLI fixes in v2 `run_classifier.py` / `evaluate.py` **only** if smoke reveals broken flags/paths (no scope expansion)

## Files forbidden to change

- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md` — do **not** create/overwrite as production results
- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/**`
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv`
- `/workspace/pyproject.toml`
- Do not `git commit` unless the user asks

## Credentials (exact)

Bedrock (research_tools routes `qwen/qwen3.6-plus` through Bedrock). In the Cursor Cloud Agent environment:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

Locally / outside that env: use the default AWS credential chain / `AWS_PROFILE` as documented in `/workspace/AGENTS.md`. Do **not** require `OPENAI_API_KEY` for this smoke.

## Smoke procedure (exact)

```bash
cd /workspace

test -f experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py \
  --arm both --limit 5 --model qwen/qwen3.6-plus
# Record:
#   CONTROL_RUN=experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control/outputs/<TS>
#   TUNED_RUN=experiments/llm_prompt_engineering_v2_2026_08_05/outputs/tuned/outputs/<TS>

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \
  --run-dir "$CONTROL_RUN"
# Expect: four metrics printed; n=5

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \
  --run-dir "$TUNED_RUN"
# Expect: four metrics printed; n=5
```

### Smoke pass checklist

| Check | Pass |
|-------|------|
| Control run dir | `metadata.json` + exactly 5 predictions (JSON files or jsonl rows) |
| Tuned run dir | `metadata.json` + exactly 5 predictions |
| Metadata | `arm` / model id includes `qwen/qwen3.6-plus` / `n_items=5` |
| Writer fields | each prediction has `message_id`, `keep_remove_label`, `predicted_label`, `arm` |
| Arms differ | control metadata `arm=control`; tuned `arm=tuned` |
| Evaluate | both arms print accuracy, precision, recall, f1 without traceback |
| Limit honored | no run processed all 1000 rows |

**Stop here and ask the user to review smoke metrics/paths before Step 5.**

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
    assert (p / 'metadata.json').is_file(), p
    jsonl = p / 'predictions.jsonl'
    if jsonl.is_file():
        n = sum(1 for line in jsonl.read_text().splitlines() if line.strip())
    else:
        n = len([x for x in p.glob('*.json') if x.name != 'metadata.json'])
    assert n == 5, (run, n)
    meta = json.loads((p / 'metadata.json').read_text())
    blob = json.dumps(meta)
    assert 'qwen/qwen3.6-plus' in blob
print('v2 smoke artifact counts OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Both arms | 5 preds each | Missing arm / wrong count |
| Model | Qwen 3.6 id in metadata | Still `gpt-5.4-nano` |
| Evaluate | exit 0 both | Scoring error / missing fields |
| No production | 1000-row run not started; no production `RESULTS.md` | Full run or RESULTS written |
| Gate | assistant stops and asks for approval | Proceeds to Step 5 without approval |

## Done when

1. Live smoke of both arms with `--limit 5` and `qwen/qwen3.6-plus` completed successfully.
2. Evaluate printed metrics for both arms.
3. README documents smoke vs production and the approval gate.
4. User has been asked to approve before Step 5; Step 5 has **not** started.
