# Step 6: Evaluate the locked programs and write the report

## Outcome

This step reads the untouched test split after selection is locked, evaluates the original and selected programs on the same 61 rows, and completes `RESULTS.md`. A completed run is idempotent, so running the command again makes no new test call.

## Caller and happy path

The caller is `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step3_evaluate/main.py --run-id RUN_ID`.

The command verifies the locked selection before it loads the test split. It scores and uploads the original arm, then scores and uploads the selected arm. After both uploads pass their checks, it calculates paired metrics and completes the report. It also checks every referenced S3 object. If complete test artifacts already exist and match their hashes, the command returns them without calling the model.

## Files

### Inspect

- The locked pilot configuration and selection artifacts
- The S3 split manifest and test split hash
- Baseline development artifacts, optimized development artifacts, usage records, and W&B traces
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md`

### Allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/evaluation.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/artifacts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/telemetry.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step3_evaluate/main.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md`

### Forbidden to change

- The original prompt, selected prompt, compiled programs, demonstrations, exclusions, splits, metric, threshold, positive class, candidate records, and selection rule
- Optimization checkpoints and approved smoke artifacts
- Any test file or test directory
- Any prompt or candidate decision after a test prediction exists

## Evaluation and report contracts

1. Refuse to run unless `selected_program.json` has `selection_status=locked`, the selected program and prompt hashes match, and complete development metrics exist.
2. Confirm the test split hash against the input manifest before reading labels. Do not expose test inputs, labels, predictions, or metrics to optimization or selection code.
3. Evaluate the original program and selected program on the same ordered 61 test rows with the same model settings, concurrency, retry policy, threshold 0.5, and remove-positive metric functions.
4. Upload the complete baseline prediction Parquet before starting the selected arm. Upload the complete selected prediction Parquet before calculating the final comparison.
5. Write each row's post ID, gold label, returned Boolean, reported probability, derived prediction, contract status, latency, retries, token counts, and trace reference.
6. Report F1, accuracy, recall, and precision for each arm. Report absolute changes, but do not claim statistical reliability from five remove rows.
7. Preserve the 1,244 planned task metric-call accounting as 1,000 GEPA calls, 61 baseline development calls, 61 selected development calls, and 122 test calls. Report observed reflection, retry, and failed-call usage separately.
8. `RESULTS.md` must include the split audit, original and optimized prompts, optimizer summary, selection rule, development metrics, test metrics, cost and runtime, package and model settings, W&B links, S3 links, and limitations.
9. State that each missed remove in development or test changes recall by 20 percentage points because each split has five remove rows.
10. Once both prediction files and `metrics.json` exist with matching hashes, a second command run must make zero provider calls.

## Implementation sequence

1. Add the evaluation caller with selection status and hash checks before initializing a language model.
2. Check for complete test artifacts. Return the existing result if all expected objects and hashes match.
3. Load and validate the 61-row test split only after selection checks pass.
4. Initialize Weave with the pilot run ID and `stage=test`. Use trace metadata for upload health and later review, never for changing the prompt.
5. Score the original program, upload `baseline_predictions.parquet`, and perform an S3 read-after-write check.
6. Score the selected program on the identical ordered rows, upload `optimized_predictions.parquet`, and perform the same check.
7. Calculate both metric sets with the shared function. Upload `metrics.json` with artifact hashes and final usage totals.
8. Complete `RESULTS.md` from saved artifacts. Use tables for split counts, prompt comparison, development and test metrics, and usage.
9. Verify each S3 link and W&B trace reference in the report. Confirm the report's numbers by loading the final JSON and Parquet files rather than copying terminal output.
10. Run the caller again and confirm it returns the existing result with zero new calls.

## Verification

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step3_evaluate/main.py --run-id RUN_ID
```

Expected output. The command reports one locked candidate, 61 baseline test predictions, and 61 selected test predictions. It prints both metric sets at threshold 0.5, final task and provider usage, W&B references, and the completed S3 run URI.

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step3_evaluate/main.py --run-id RUN_ID
```

Expected output. The command validates existing object hashes and reports the same metrics. It states that it made zero new provider calls and exits zero.

## W&B review after evaluation

Use W&B only after the selected program and development result are locked. Confirm that both test arms use the same model settings and ordered post IDs, all 122 task traces are present after flushing, and W&B usage agrees with the final local and S3 records. You may inspect baseline and selected errors to support the written limitations, but no test trace may cause a prompt, threshold, split, or candidate change.

## Pass and stop conditions

Pass only when both arms cover the same 61 test IDs, every row has a valid trace and usage record, metric calculations reproduce from uploaded predictions, all report links resolve, the second run makes zero calls, and `RESULTS.md` states the small remove count limitation.

Stop before the first test call if selection is not locked or a hash differs. After a partial provider failure, preserve the completed arm and do not compute final metrics until both arms are complete. Stop if the two arms differ in rows, settings, or threshold, and never repair the mismatch by changing a locked input.

## Commit

Suggested commit message. `experiment: evaluate selected prompt and report results`
