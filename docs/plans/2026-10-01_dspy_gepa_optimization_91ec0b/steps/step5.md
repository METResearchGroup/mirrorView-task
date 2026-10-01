# Step 5: Run the approved pilot and select one prompt

## Outcome

This step runs the 1,000-call GEPA pilot after the user approves a completed smoke run. It selects one prompt by balanced GEPA validation accuracy, records the selected program, and reports development metrics without changing the selection.

## Caller and happy path

Do not begin this step until the user approves the smoke run's measured cost and runtime estimates.

The caller is `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --run-id RUN_ID --approved-smoke-run-id SMOKE_RUN_ID --max-metric-calls 1000`.

The caller verifies the completed smoke record before it creates a separate pilot run. It runs or resumes GEPA to the call limit, then locks the selected candidate. After selection is locked, it scores that candidate on development data and uploads the selection artifacts. It never loads the test split.

## Files

### Inspect

- The approved smoke run's configuration, usage, estimates, candidates, rejection records, checkpoints, and W&B traces
- The S3 split manifest and Step 3 contract output
- All shared optimization modules and the optimizer caller

### Allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/evaluation.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/artifacts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/telemetry.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md`

### Forbidden to change

- The prompt examples, demonstrations, exclusion IDs, input splits, metric, threshold, positive class, and balanced validation subset
- The approved smoke artifacts
- The 1,000 task metric-call limit
- Any test file or test directory
- The test split contents or test artifacts

## Pilot contracts

1. Reject the command unless `--approved-smoke-run-id` names a completed smoke run with status `awaiting_user_approval` and the operator has supplied the approved run ID after user approval.
2. Copy the approved smoke estimates, baseline development artifacts, and configuration hashes into the pilot run. Record the smoke run ID as their source. Fail if the model, prompt, data, metric, package, or telemetry contracts differ.
3. Give GEPA at most 1,000 task metric calls. Count reflection and retry calls separately, and include all provider usage in cost reporting.
4. Use the deterministic one-keep and one-remove reflection batches and the fixed 10-row balanced GEPA validation set from Step 3.
5. Apply proposal checks before scoring. Save every accepted instruction and every rejection reason.
6. Save a checkpoint after every accepted candidate. Resume only when the run configuration and input hashes match exactly.
7. Pause if projected cost exceeds the user-approved high estimate. Also pause when the most recent 50 paid calls have an error rate above 5% or five consecutive proposals fail for the same reason.
8. Select the candidate with the highest balanced validation accuracy. Break an exact tie by shorter instruction length, then earlier candidate index.
9. Confirm the selected prompt passes the output contract, 40-character copy check, and 125% length limit again before locking it.
10. Write the selected program and prompt before loading development data. Score all 61 development rows at threshold 0.5, but do not reselect a candidate from development F1.
11. Include `selection_status=locked` and the selected prompt hash in `selected_program.json`. Upload `candidate_metrics.jsonl`, `selected_program.json`, `optimized_prompt.txt`, `development_predictions.parquet`, and `development_metrics.json` under `selection/`.

## Implementation sequence

1. Add approval and smoke compatibility checks before creating a language model or loading optimization data.
2. Create the pilot run configuration and initialize Weave with `mode=pilot`.
3. Start or resume GEPA with the exact 1,000-call limit. Reconcile W&B and local usage after each accepted candidate.
4. Apply the health and spending pause conditions continuously. Upload current state before a controlled pause.
5. At completion, recompute every candidate's stored balanced validation result from its prediction records. Select one candidate with the documented tie rules.
6. Recheck the selected prompt guards, then write the compiled program and plain text prompt. Copy the approved baseline development artifacts into this run without making another baseline call.
7. Load the development split and score the selected program once. Report accuracy, precision, recall, and F1 with remove as positive and threshold 0.5.
8. Upload the selection and development artifacts, flush Weave, reconcile usage, and record direct W&B and S3 links in `RESULTS.md`.
9. Exit with `selection_locked` and an explicit statement that the test split was not loaded.

## Verification

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --run-id RUN_ID --approved-smoke-run-id SMOKE_RUN_ID --max-metric-calls 1000
```

Expected output. The command verifies the approval record and reaches at most 1,000 task metric calls. It prints separate reflection and retry usage, then selects one candidate. It reports metrics for 61 development rows and copies the approved baseline development artifacts. After it uploads the selection artifacts, it exits with `selection_locked` and states that it did not load a test row.

Run the command again with the same IDs.

Expected output. The command validates the existing checkpoint and locked selection. It makes no duplicate completed call and returns the same selected candidate and development metrics.

## W&B review during the pilot

Filter by the pilot run ID and review these signals while the command runs:

1. Compare cumulative task and reflection calls, tokens, retries, and projected cost with the approved range. Pause if the projection crosses the approved high estimate.
2. Compare balanced validation accuracy by candidate and iteration. Inspect accepted prompt changes for copied post text, lost output requirements, and excess length.
3. Review remove false negatives before false positives, and note repeated wording or rule failures across candidates.
4. Watch latency outliers, provider errors, invalid probabilities, malformed responses, and retry clusters.
5. Compare W&B counts with the checkpoint and `usage.json` after each accepted candidate. Pause when missing completed calls remain above 1% after flushing.

Do not open test traces or test artifacts. W&B may inform an operational pause, but it may not change the metric, splits, threshold, candidate choice rule, or prompt guards.

## Pass and stop conditions

Pass only when the approval reference is valid, every accepted and rejected proposal has a record, usage stays within the approved range, the selected candidate follows the balanced validation rule, selection artifacts pass read-after-write checks, development metrics are complete, and no test row was loaded.

Stop and preserve a resumable checkpoint when a spending or health limit fires. Stop without selecting when usage records disagree by more than 1%, a split or configuration hash changes, or candidate scores cannot be reconstructed. Never use development results to replace the selected candidate.

## Commit

Suggested commit message. `experiment: run approved GEPA pilot and lock selection`
