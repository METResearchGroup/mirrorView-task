# Step 4: Smoke test and run full inference

## Goal

Confirm live Jev behavior on a small sample, measure tokens and latency, then score all 13,992 prepared pairs under one production run ID. Accept the run only when its manifest reports 13,992 unique valid predictions and no unresolved failures.

All paths are relative to the repository root. Run every command from the repository root.

## Scope

- **Main caller:** `experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py::main`
- **Repository changes:** none. The commands write only to `s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/`.
- **Out of scope:** changing code, schemas, prompts, or constants, calculating metrics, writing documentation, and trying other Jev model IDs.

## Files to inspect

- `experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/constants.py`
- `shared/models/jev/constants.py`

## Files allowed to change

None.

## Files forbidden to change

Every repository file.

## Preconditions

1. Step 2's prepare command printed `rows=13992 ... sha256_matches_source=true`.
2. Step 3's `--help` check passed.
3. AWS credentials can read the `jev-typesafe-api-key` secret in `us-east-2` and write to the experiment S3 prefix. Alternatively, `TYPESAFE_API_KEY` is set.

## Phases

### Phase 1: Smoke run

```bash
RUN_ID=study2-jev-zero-shot-2026-10-01
SMOKE_RUN_ID="${RUN_ID}-smoke"
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run --run-id "$SMOKE_RUN_ID" --limit 5
```

The command should exit 0 and print one summary line with `expected=5 unique_valid_predictions=5 unresolved_failures=0 status=complete`.

If the command raises `ValueError: expected model jev-1.13.0, got ...`, Jev answered with a different model than the pinned one. Stop and return to plan review without changing the pin.

Read the smoke predictions to measure usage:

```bash
aws s3 cp "s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/runs/$SMOKE_RUN_ID/jev_1_13_0/predictions/batch-000000.jsonl" - | PYTHONPATH=. uv run python -c 'import json, sys; rows=[json.loads(line) for line in sys.stdin if line.strip()]; tokens=[row["usage"]["input_tokens"] for row in rows]; mean=sum(tokens)/len(tokens); print(f"rows={len(rows)} mean_input_tokens={mean:.1f} est_full_input_tokens={mean*13992:.0f} est_full_usd={mean*13992*0.042/1e6:.4f}")'
```

The command should print `rows=5` and a `mean_input_tokens` value. The plan's estimates range from 530 to 1,000 tokens per request, which would make `est_full_usd` between 0.31 and 0.59, with a median of 0.41. Record the printed line for `RESULTS.md`. If `est_full_usd` is above 5.00, stop and ask the reviewer before the full run.

The smoke run passes when all five predictions are valid, each `p_remove` is in [0, 1], and each label follows the 0.5 rule.

The smoke run fails on any failure row, model mismatch, or write outside `runs/$SMOKE_RUN_ID/`. If it fails, do not start the full run.

### Phase 2: Full run

```bash
mkdir -p /tmp/mirrorview-jev-logs
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run --run-id "$RUN_ID" > /tmp/mirrorview-jev-logs/full.log 2>&1
tail -n 1 /tmp/mirrorview-jev-logs/full.log
```

The command should exit 0, and the last log line should contain `expected=13992 unique_valid_predictions=13992 unresolved_failures=0 status=complete`. Because of the rate limit of 1,000 requests per minute, the full run takes at least 14 minutes. Logs stay in `/tmp`, and artifacts go only to S3.

### Phase 3: Resume until complete

If the process exits nonzero or reports `status=incomplete`, rerun the same command with the same `RUN_ID`. Do not create a new run ID or delete any object.

```bash
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run --run-id "$RUN_ID"
```

In the summary line, `skipped` should equal the number of previously completed IDs. Only pending or unresolved IDs are scored. If a post still fails after three reruns, stop and report its `post_id` and exception type from the failure objects.

### Phase 4: Completion check

Run the same command once more after a complete run.

The command should exit 0 and print `skipped=13992 new_predictions=0 new_failures=0 unique_valid_predictions=13992 unresolved_failures=0 status=complete`, and it should make no Jev calls.

## Pass

- The smoke run passes and its measured usage is recorded.
- The production run folder holds exactly 13,992 unique valid predictions with no unresolved failures.
- A rerun after completion makes no Jev calls.
- No repository file changes: `git status --short` matches its output before this step.

## Fail

- Any model mismatch, unresolved failure after three reruns, or count other than 13,992.
- A rerun scores a completed ID again or changes an existing object.
- Smoke artifacts appear under the production run ID.
