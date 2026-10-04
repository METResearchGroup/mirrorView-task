# Step 5: Score every pair

## Proposal sections implemented

- "Cross-cutting concerns: Model and request limits"
- "Step 4: Score the pairs", the full-run half
- "Expected results", the 13,992 prediction count

## Goal

Score all 13,992 prepared pairs under run id `study2-jev-optimized-prompt-2026-10-04`. Resume the same run until the manifest is complete. Record the measured runtime and token totals in `RESULTS.md`.

The production run adds no Python. If the Step 4 smoke contract is incomplete, stop and return to Step 4.

Run every command from `/workspace` with `PYTHONPATH=.`.

## Scope

- **Main caller:** `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step2_inference/main.py`, already created in Step 4.
- **Happy path:** one production run writes 13,992 valid predictions and no unresolved failures, and a second call skips every completed post id.
- **Unit of work:** the live production run and its measured record.
- **Out of scope:** new Python, analysis tables, unit tests, and checked-in smoke scripts.

## Files to inspect

- `/workspace/docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/steps/step4.md`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/SETUP.md`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/RESULTS.md`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step2_inference/main.py`
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py`, function `_print_summary`

## Files allowed to change

- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/RESULTS.md`

## Files forbidden to change

- Every Python file. A production defect goes back to the step that added that code.
- `/workspace/shared/models/jev/**`
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/**`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/**`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/README.md`
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/SETUP.md`
- Every `tests/` directory, every `test_*.py` file, and every checked-in smoke script
- The zero-shot Jev prefix and the completed few-shot Jev prefix

## Contracts

Use Jev 1.13.0, `OPTIMIZED_VARIANT`, batch size 500, and 8 workers. Pass no `--limit`. The run id is `study2-jev-optimized-prompt-2026-10-04`. Each manifest stores:

- experiment name `few_shot_jev_optimized_prompt_2026_10_04`
- prompt name `optimized_study_prompt`
- prompt SHA-256 `178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f`
- instructions SHA-256 `1929e49a31c20488ff25a134d53d9e267d7214ca723575042ef6d7a19f23cb5e`
- input SHA-256 `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`
- schema version `study2-optimized-prompt-jev-run-v1`

An interrupted run uses the same command again. Completed post ids are skipped. A change of limit, batch size, worker count, input digest, or prompt digest must fail before scoring.

## Run

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
PROD_LOG=/tmp/optimized-jev-production.log
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step2_inference.main --run-id study2-jev-optimized-prompt-2026-10-04 --batch-size 500 --max-workers 8; } >"$PROD_LOG" 2>&1
rg -n "run_id=study2-jev-optimized-prompt-2026-10-04 model_folder=jev_1_13_0 model_id=jev-1.13.0 expected=13992 .* unique_valid_predictions=13992 unresolved_failures=0 status=complete" "$PROD_LOG"
```

The command exits 0. On a fresh run the summary has `skipped=0` and `new_predictions=13992`. If you resume after an interruption, `skipped` plus `new_predictions` equals 13,992, `new_failures` is 0, and `unique_valid_predictions` is 13,992. `input_tokens` is a measured positive integer. `output_tokens` is a measured nonnegative integer. The proposal estimate of 25,765,384 input tokens is not a pass condition.

After the manifest is complete, run the same command once more:

```bash
cd /workspace
RESUME_LOG=/tmp/optimized-jev-production-resume.log
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step2_inference.main --run-id study2-jev-optimized-prompt-2026-10-04 --batch-size 500 --max-workers 8; } >"$RESUME_LOG" 2>&1
rg -n "expected=13992 skipped=13992 new_predictions=0 new_failures=0 unique_valid_predictions=13992 unresolved_failures=0 status=complete" "$RESUME_LOG"
```

The resume call exits 0 and adds no prediction batch and no failure batch.

Write the production run id, the measured `real` seconds, `input_tokens`, `output_tokens`, and the cost into `RESULTS.md`. Cost is `input_tokens * 0.042 / 1000000`, rounded to 6 decimal places, because output tokens are priced at 0. Keep the Step 4 smoke measurement in the file.

## Pass and fail

- Pass: the complete manifest has 13,992 predictions and 0 unresolved failures, the resume call skips all 13,992, and `RESULTS.md` records the measured production totals.
- Fail: any unresolved failure, a resume call that scores a new pair, a Python edit, or a write outside the new experiment prefix.
