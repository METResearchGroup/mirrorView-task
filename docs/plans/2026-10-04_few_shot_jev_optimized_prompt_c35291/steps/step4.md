# Step 4: Smoke the scoring path

## Proposal sections implemented

- "Cross-cutting concerns: Model and request limits"
- "Schema and key interfaces"
- "Step 4: Score the pairs", the five-row smoke half
- "Expected results", the sentence that the smoke run replaces the estimates

## Goal

Score the first five prepared pairs with Jev 1.13.0, then repeat the same command and confirm those five pairs are skipped. Record the measured tokens, cost, and runtime in `RESULTS.md`. Do not start the 13,992-pair run in this step.

Run every command from `/workspace` with `PYTHONPATH=.`.

## Scope

- **Main caller:** `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step2_inference/main.py`, function `main`.
- **Happy path:** `main` calls `run_inference_cli` with `OPTIMIZED_VARIANT` and `build_optimized_remove_request`.
- **Unit of work:** one thin command file, then one live five-row smoke run and one resume check.
- **Out of scope:** the production run, analysis, changes to `run_inference`, unit tests, and checked-in smoke scripts.

## Files to inspect

- `/workspace/docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/steps/step2.md`
- `/workspace/docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/steps/step3.md`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/main.py`
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py`, function `run_inference_cli`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/config.py`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/jev.py`

## Files allowed to change

- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step2_inference/main.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/RESULTS.md`

## Files forbidden to change

- `/workspace/shared/models/jev/**`
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/**`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/**`
- Every new-experiment file not listed under files allowed to change
- `/workspace/pyproject.toml` and `/workspace/uv.lock`
- Every `tests/` directory, every `test_*.py` file, and every checked-in smoke script
- The production run prefix `s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_optimized_prompt_2026_10_04/runs/study2-jev-optimized-prompt-2026-10-04/`

## Contracts

`main` contains no argument parsing, AWS setup, scorer construction, or storage code. It calls:

```python
run_inference_cli(
    OPTIMIZED_VARIANT,
    build_optimized_remove_request,
    description="Run resumable optimized-prompt Jev inference.",
)
```

The shared CLI keeps `--run-id`, `--limit`, `--batch-size`, and `--max-workers`. `--help` exits before it creates an S3 client or a Jev scorer.

The smoke run id is `study2-jev-optimized-prompt-2026-10-04-smoke`. Use limit 5, batch size 5, and 1 worker. Write only under:

```text
s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_optimized_prompt_2026_10_04/runs/study2-jev-optimized-prompt-2026-10-04-smoke/jev_1_13_0/
```

The stored manifest uses prompt name `optimized_study_prompt`, prompt SHA-256 `178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f`, and instructions SHA-256 `1929e49a31c20488ff25a134d53d9e267d7214ca723575042ef6d7a19f23cb5e`. Each prediction has `p_remove` from 0 to 1 inclusive, and `is_remove` is true only when `p_remove >= 0.5`. The five stored post ids equal the first five prepared post ids. Any unresolved failure stops the step.

## Checks

Run this before `main.py` exists. It must fail with `ModuleNotFoundError`. After wiring, it must print `optimized-jev-inference-import-ok`, and `--help` must exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT
from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.jev import (
    build_optimized_remove_request,
)
from experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step2_inference.main import main

assert callable(main)
assert callable(build_optimized_remove_request)
assert OPTIMIZED_VARIANT.prompt_name == "optimized_study_prompt"
print("optimized-jev-inference-import-ok")
PY
PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step2_inference.main --help >/dev/null
```

## Live five-row smoke

Run only after Step 3 passes.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
aws sts get-caller-identity --output json
export SMOKE_RUN_ID=study2-jev-optimized-prompt-2026-10-04-smoke
SMOKE_LOG=/tmp/optimized-jev-smoke.log
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --limit 5 --batch-size 5 --max-workers 1; } >"$SMOKE_LOG" 2>&1
rg -n "expected=5 skipped=0 new_predictions=5 new_failures=0 unique_valid_predictions=5 unresolved_failures=0 status=complete" "$SMOKE_LOG"
```

The command exits 0. The summary line contains:

```text
run_id=study2-jev-optimized-prompt-2026-10-04-smoke model_folder=jev_1_13_0 model_id=jev-1.13.0 expected=5 skipped=0 new_predictions=5 new_failures=0 unique_valid_predictions=5 unresolved_failures=0
```

The same line has positive `input_tokens`, nonnegative `output_tokens`, and `status=complete`. The log ends with `real`, `user`, and `sys` lines. Copy the measured `real` value, token totals, and cost into `RESULTS.md` as the smoke measurement. Cost is `input_tokens * 0.042 / 1000000`, because `JEV_USD_PER_MILLION_OUTPUT` is `0.0`. Do not treat the five-row sample as a forecast of the full run.

## Resume check

```bash
cd /workspace
RESUME_LOG=/tmp/optimized-jev-smoke-resume.log
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --limit 5 --batch-size 5 --max-workers 1; } >"$RESUME_LOG" 2>&1
rg -n "expected=5 skipped=5 new_predictions=0 new_failures=0 unique_valid_predictions=5 unresolved_failures=0 status=complete" "$RESUME_LOG"
```

The resume call exits 0. It must not append a prediction batch or a failure batch. A second call with `--limit 4` must exit nonzero before it scores a pair.

## Pass and fail

- Pass: the first smoke summary has five new predictions and no failures, the resume summary skips all five, and `RESULTS.md` records the measured smoke tokens, cost, and `real` seconds.
- Fail: any unresolved failure, a resume call that creates a prediction, a help command that contacts AWS, or a write under the production run id.
