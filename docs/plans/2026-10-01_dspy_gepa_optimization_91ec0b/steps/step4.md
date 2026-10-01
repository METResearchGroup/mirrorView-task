# Step 4: Run the baseline and 30-call smoke

## Outcome

This step records the original program's development result and runs GEPA with a 30 metric-call limit. It proves the paid optimization path, reconciles W&B and local usage, estimates the 1,000-call pilot, and stops for user approval.

## Caller and happy path

The caller is `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --smoke --max-metric-calls 30`.

The command creates a smoke run ID and initializes Weave before it scores the seed program on all 61 development rows. It runs the limited optimizer, saves its checkpoint, and uploads the run artifacts. A second run confirms checkpoint resume. The first run prints measured cost and runtime ranges and exits with `awaiting_user_approval`. It must not offer or start a pilot continuation in the same process.

## Files

### Inspect

- All shared modules created in Steps 1 to 3
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md`
- W&B traces from Step 1
- The S3 split manifest from Step 2

### Allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/evaluation.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/artifacts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/telemetry.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md`

### Forbidden to change

- The prompt, demonstrations, exclusion IDs, split membership, and metric definition
- The uploaded input objects
- Any test file or test directory
- The test split contents or test artifacts
- The 1,000-call pilot budget

## Smoke run contracts

1. Create an immutable run configuration before the first paid call. Include the run ID, mode, commit SHA, dirty-worktree status, model settings, seed, split hashes, threshold, positive class, package versions, and W&B project.
2. Tag every trace with the run ID, `mode=smoke`, stage, candidate ID when applicable, model ID, split hash, and post ID.
3. Score the original program on the complete 61-row development split once. Save predictions and metrics under `runs/RUN_ID/baseline/`.
4. Give GEPA exactly 30 task metric calls. Count reflection calls separately and include them in cost and runtime accounting.
5. Require at least one proposed candidate, one scored candidate, and one accepted valid candidate. Exercise at least one proposal rejection and record its reason.
6. Save optimizer state after each accepted candidate. Restart the caller with the same smoke run ID and confirm that it resumes from that state without duplicating completed work.
7. Reconcile completed task calls, reflection calls, errors, retries, input tokens, output tokens, and latency between the local usage record and W&B after flushing the client.
8. Derive low, median, and high pilot estimates from measured smoke usage. Report the measured assumptions alongside the estimates, and compare them with the preliminary $6, $9, and $18 ranges and 10-minute, 30-minute, and 2-hour runtimes.
9. Upload `config.json`, `telemetry.json`, baseline artifacts, optimizer state, candidate records, prompt files, rejection records, and `usage.json` to the smoke run folder.
10. End in `awaiting_user_approval`. A pilot command must require both a new pilot run ID and `--approved-smoke-run-id` that points to this completed smoke run.

## Implementation sequence

1. Add run ID generation and immutable run configuration writing before telemetry initialization.
2. Add baseline development evaluation with bounded concurrency and retry accounting. Reuse the same prediction and metric functions that later steps use.
3. Add the smoke optimizer path with a hard 30-call limit and the Step 3 sampler, validation subset, and proposal checks.
4. Upload each accepted candidate, rejection record, usage update, and optimizer checkpoint before continuing.
5. Add a resume path keyed by run ID. Confirm configuration and split hashes before loading a checkpoint.
6. Flush Weave, wait for completed trace records to become visible, and compare W&B counts with the local ledger. Treat a difference above 1% as failure after the allowed flush period.
7. Calculate estimates from observed task and reflection token counts, latency percentiles, concurrency, retry rate, and projected call counts. Include W&B trace storage as an excluded cost unless the account exposes a usable amount.
8. Write the smoke summary and W&B URLs to `RESULTS.md`, mark it as awaiting approval, and exit zero without reading test data.

## Smoke verification

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --smoke --max-metric-calls 30
```

Expected output. The command prints the smoke run ID, W&B project, trace URLs, and S3 run URI. It reports 61 baseline development results, exactly 30 task metric calls, separate reflection calls, and at least one valid candidate. It also prints measured low, median, and high estimates. Its final status is `awaiting_user_approval`.

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --smoke --max-metric-calls 30 --run-id SMOKE_RUN_ID
```

Expected output. The command confirms the same configuration and hashes, then resumes the completed checkpoint. It makes no duplicate task metric call and returns the same summary.

## W&B review before approval

Filter the Weave Calls view to the smoke run ID, then check the following items:

1. Setup, baseline, optimizer, reflection, metric, and checkpoint operations share one run ID, and their child calls appear under the correct stage.
2. W&B and `usage.json` agree on calls, errors, retries, tokens, and latency after the client flush.
3. At least one correct keep prediction and one correct remove prediction have valid probabilities. Any contract failure has a score of 0.
4. Every trace has the model ID, split hash, post ID, stage, candidate ID when applicable, and smoke mode. No trace contains a secret.
5. Observed token counts, latency, retries, and reflection frequency support the reported cost and runtime ranges.

## Pass and stop conditions

Pass only when the baseline artifacts are complete, the optimizer reaches exactly 30 task metric calls, a valid candidate exists, resume makes no duplicate call, W&B reconciliation is within 1%, S3 read-after-write checks pass, and the command stops for approval.

Stop if the projected pilot cost exceeds the preliminary high estimate, the recent paid-call error rate exceeds 5%, a checkpoint cannot resume, five consecutive proposals fail for the same reason, W&B misses more than 1% of completed calls after flushing, or any test row is loaded. Report the low, median, and high estimates even when another stop condition ends the smoke.

## Commit

Suggested commit message. `experiment: add baseline and GEPA smoke run`
