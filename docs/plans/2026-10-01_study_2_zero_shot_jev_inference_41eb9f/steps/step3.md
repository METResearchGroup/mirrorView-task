# Step 3: Add resumable Jev inference

## Goal

Build one inference command that scores the prepared input with Jev for one run ID. It writes immutable prediction and failure JSONL batches and a run manifest under the Jev run folder, and skips post IDs that already have valid predictions. The command follows issue 326 Step 2's rules for identity, resume, limits, and batches. It replaces Bedrock with `shared.models.jev` and drops the `--model` option, because only one model runs.

All paths are relative to the repository root. Run every command from the repository root.

## Scope

- **Main caller:** `experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py::main`
- **Main task:**
  1. Parse the run ID and options.
  2. Load and verify the prepared input.
  3. Load existing run objects and find the pending post IDs.
  4. Score pending pairs in batches with a bounded thread pool.
  5. Write immutable prediction and failure batches.
  6. Write one immutable `JevRunManifest`.
- **Unit of work:** one process owns the `jev_1_13_0` folder for one run ID.
- **Out of scope:** live smoke and full runs (Step 4), metrics and documentation (Step 5), and changes to `shared/models/jev/` or issue 326 files.

## Exact file tree

```text
experiments/zero_shot_jev_inference_2026_10_01/
  src/
    step2_inference/
      __init__.py
      run.py
```

## Files to inspect

- `docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step2.md` (the "Resume and identity rules", "Batch rules", and "S3 layout" sections define this step's behavior)
- `experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py` (`PredictionRecord`, `FailureRecord`, `InputManifest`, `Study2InputRecord`)
- `experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/constants.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py`
- `shared/models/jev/scorer.py`
- `data_platform/generate_features/s3_feature_campaign.py`

## Files allowed to change

- `experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/__init__.py`
- `experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py`

## Files forbidden to change

- `experiments/zero_shot_jev_inference_2026_10_01/shared/**`
- `experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/**`
- `experiments/zero_shot_llm_inference_2026_09_30/**`
- `shared/**`
- `data_platform/**`
- `pyproject.toml`
- `uv.lock`

If this step needs a change to a Step 2 file, stop and return to plan review.

## Confirmed contracts

### CLI

| Option | Rule |
| --- | --- |
| `--run-id` | Required. Must pass the safe-segment validator. |
| `--limit` | Optional positive integer. Selects the first records in prepared order, after the full input is validated. |
| `--batch-size` | Positive integer. Default `DEFAULT_BATCH_SIZE` (500). |
| `--max-workers` | Positive integer. Default `DEFAULT_MAX_WORKERS` (8). |

`--help` must not build a scorer, read a secret, or access S3. The production path applies issue 326's credential adapter, then builds `CampaignObjectStore(S3_BUCKET)` and `build_jev_scorer()`.

### Public run function

`run_inference(store, scorer, run_id, limit, batch_size, max_workers) -> JevRunManifest` accepts an injected `CampaignObjectStore`-shaped store and any object with a `score(request) -> JevResult` method, so direct checks need no AWS or Jev access.

### Behavior

Before any Jev call:

1. Read `INPUT_MANIFEST_KEY` and `INPUT_RECORDS_KEY`. Check the records SHA-256 against the manifest. Parse every line as `Study2InputRecord` and reject duplicate IDs.
2. Apply `--limit` to the validated records in prepared order to form the requested set.
3. Load existing `JevRunManifest` objects under the run folder. Reject a `--limit`, `--batch-size`, or `--max-workers` that differs from the first manifest.
4. Load every prediction object as `PredictionRecord`. Reject a mismatched `run_id`, `model_folder`, or `model_id`, a duplicate or unknown `post_id`, or invalid JSONL.
5. Pending IDs are requested IDs, in prepared order, that have no valid prediction. A failure row never counts as complete.

For each batch of up to `batch_size` pending records:

1. Submit `scorer.score(build_remove_request(record))` for each record to a `ThreadPoolExecutor(max_workers)` that shares one scorer.
2. Map each success with `to_prediction_record(run_id, record, result)`. Map each exception to one `FailureRecord` with the exception type, a nonempty message, and wrapper call count `1`. `JevScorer` retries internally, so the experiment calls it once per record.
3. Restore prepared-input order, then write at most one prediction object and one failure object with `put_new`. Skip a side that is empty.
4. Stop on any write error or `FileExistsError`. Do not write a manifest that claims unwritten results.

After the last batch, or right away when nothing is pending, recount state from S3 and write one new `JevRunManifest`. Its status is `complete` only when every requested ID has exactly one valid prediction and the unresolved failure count is 0.

Print one summary line:

```text
run_id=RUN_ID model_folder=jev_1_13_0 model_id=jev-1.13.0 expected=N skipped=S new_predictions=P new_failures=F unique_valid_predictions=V unresolved_failures=U input_tokens=I output_tokens=O status=STATUS
```

`input_tokens` and `output_tokens` are sums over all valid predictions in the run.

## Caller-first implementation phases

### Phase 0: Confirm scope

The command has one caller, and each process handles one model folder and one run ID. Do not add a supervisor process that starts several runs.

### Phase 1: Scaffold

Create both files with stubs, then commit.

```bash
PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run import main, run_inference; print('step3-imports-ok')"
```

Expected output:

```text
step3-imports-ok
```

### Phase 2: Confirm contracts

Fill in typed signatures for argument parsing, input loading, state loading, pending selection, batch execution, batch writes, the manifest write, and the summary. Commit. Stop for plan review before Phase 3 unless this step file was approved without revisions.

### Phase 3: Direct checks to satisfy

Each check runs against a fake store and a fake scorer that returns preset `JevResult` values or raises preset exceptions.

1. Given two pending records, when the run executes, then the fake scorer receives two requests whose `state` matches each pair in order, and one prediction object holds both rows in prepared order.
2. Given a valid prediction for the first ID, when the run resumes, then the scorer receives only the second ID and the first object is unchanged.
3. Given valid predictions for every ID, when the run resumes, then the scorer receives no calls and a `complete` manifest is written.
4. Given a historical failure with no prediction, when the run resumes, then that ID is scored again and the old failure object stays listed.
5. Given one success and one `TypeSafeRateLimitError` in a batch, when the batch finishes, then one prediction object and one failure object are written and the manifest status is `incomplete`.
6. Given a duplicate prediction, a mismatched `model_id`, an unknown `post_id`, invalid JSONL, or an input SHA-256 mismatch, when state loads, then the run raises before any scorer call.
7. Given `--limit 2` and a malformed record at position 10, when the input loads, then the run raises before selecting the limited set.
8. Given an existing manifest with `limit=5`, when the run is called with no limit, then it raises before any scorer call.
9. Given an unsafe run ID or a nonpositive `--limit`, `--batch-size`, or `--max-workers`, when the arguments are parsed, then the command exits nonzero before building a scorer.
10. Given a fake store that raises `FileExistsError` on a prediction write, when the batch is written, then the run stops and writes no manifest.

### Phase 4: Implement one unit at a time

Implement in caller dependency order, committing each unit separately:

1. Argument parsing and validation
2. Input loading and digest check
3. Requested-set selection
4. Manifest and prediction state loading
5. Pending selection
6. Batch scoring with ordered results
7. Batch writes
8. State recount and manifest write
9. `main` wiring

### Phase 5: Verify

```bash
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run --help
```

The command should exit 0, and the help text should list the required `--run-id` and optional `--limit`, `--batch-size`, and `--max-workers`. The command must not read a secret or access S3.

Do not run live inference in this step.

## Pass

- The resume logic skips only IDs with one valid prediction and retries unresolved failures.
- Every object is created with `put_new` under `runs/RUN_ID/jev_1_13_0/`.
- Output order follows prepared order regardless of thread completion order.
- Every prediction row passes issue 326's `PredictionRecord` validation, including the 0.5 threshold rule.

## Fail

- A resumed run scores a completed ID again.
- A failure row permanently suppresses a retry.
- Any write replaces, appends to, or deletes an S3 object.
- A direct check reaches live Jev, Secrets Manager, or S3.
- Any forbidden file changes.
