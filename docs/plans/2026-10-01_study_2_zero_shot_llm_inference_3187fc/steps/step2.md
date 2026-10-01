# Step 2: Add resumable per-model Bedrock inference

## Goal

Build one inference caller that processes the prepared input for exactly one requested model and run ID. It must call the existing public Bedrock functions, write immutable prediction and failure JSONL batches below that model's run folder, record per-record token usage, publish an immutable model manifest, and skip post IDs that already have valid predictions.

## Scope

- **Main caller:** `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py::main`
- **Happy-path task:** parse one run ID and model folder, load and verify the prepared input, discover completed post IDs, call Bedrock for only pending records, write immutable batch objects, then write the model manifest.
- **Unit of work:** one process owns one model folder for one run ID.
- **Out of scope:** preparing data, running all four processes from one supervisor, model-access smoke checks, full inference execution, retrying unresolved failures in the same run, metrics, analysis, and `RESULTS.md` rendering.

## Dependencies confirmed by Step 1

Step 2 consumes these Step 1 contracts without redefining them:

- `BASELINE_ZERO_SHOT_KEEP_REMOVE_PROMPT` and its formatter.
- `Study2InputRecord`, `RemovePrediction`, `ModelDefinition`, and `InputManifest`.
- The four-entry model registry and fixed S3 root.
- Standardized JSON and JSONL serialization, SHA-256 verification, safe key construction, and immutable writes.
- The prepared records and manifest keys under `experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/`.

If Step 1 contracts change during implementation, return to plan review before modifying this step.

## Exact file tree

Create only the following new files in this step and edit only the listed shared files:

```text
/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/
  shared/
    llm.py
    schemas.py
    storage.py
  src/
    step2_inference/
      __init__.py
      run.py
```

`shared/schemas.py` and `shared/storage.py` already exist after Step 1. Extend them only with the inference contracts below.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/plan.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step1.md`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/engines/bedrock_engine.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/s3_feature_campaign.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/engines/base.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/prompts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`

The final two files remain read-only.

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/llm.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/**`
- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`
- Step 1 files not named in the allowed list.
- Step 3 analysis files, documentation files, and every file outside the experiment directory.

## Confirmed contracts

### Bedrock boundary

`shared/llm.py` must import and call these public functions from `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/engines/bedrock_engine.py`:

- `create_bedrock_runtime_client()` for the real CLI path.
- `converse_label(client, model_id, system_prompt, output_schema, user_text, max_tokens)` for one prepared record.

Pass an empty string as `system_prompt`, the exact rendered Step 1 prompt as `user_text`, and `RemovePrediction` as `output_schema`. The existing engine appends its schema-derived JSON instruction to the system message. Do not add another task instruction, call private Bedrock helpers, duplicate Converse parsing, access the boto3 client directly, or change retry constants in the existing engine.

The thin public wrapper must accept an injected `BedrockRuntimeClient`, a `ModelDefinition`, and one `Study2InputRecord`. It must return the validated `RemovePrediction` plus the engine's `BedrockUsage`. Keep client construction outside this wrapper so direct checks need no AWS credentials.

### Inference schemas

Extend `shared/schemas.py` with strict models:

- `TokenUsage`: `input_tokens: int`, `output_tokens: int`, and `total_tokens: int`. Values are nonnegative and `total_tokens` equals the other two fields' sum.
- `PredictionRecord`: schema version, `run_id`, model folder, exact model ID, `post_id`, `is_remove`, `p_remove`, and `usage: TokenUsage`.
- `FailureRecord`: schema version, `run_id`, model folder, exact model ID, `post_id`, exception type, nonempty error message, and wrapper call count.
- `ModelRunManifest`: schema version, `run_id`, model display name, model folder, exact model ID, prepared input key and SHA-256, configured batch size, configured max tokens, configured optional limit, requested record count, completed prediction count, unresolved failure count, ordered prediction object keys, ordered failure object keys, and status.

Manifest status is `complete` only when every requested post ID has exactly one valid prediction and unresolved failure count is zero. Step 2 may write `incomplete` after processing all pending rows in one run. A failure is unresolved when its post ID has no valid prediction in any immutable prediction object. Historical failure rows remain immutable after a later run succeeds.

### S3 layout

For model folder `MODEL_FOLDER` and run ID `RUN_ID`, use exactly:

```text
s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/
  runs/
    RUN_ID/
      MODEL_FOLDER/
        predictions/
          batch-000000.jsonl
          batch-000001.jsonl
        failures/
          batch-000000.jsonl
          batch-000001.jsonl
        manifests/
          manifest-000000.json
          manifest-000001.json
```

Every object is created with `CampaignObjectStore.put_new`. Never use `replace`, `append_jsonl`, or `delete`. Choose the next six-digit object sequence by listing the relevant prefix, parsing only exact expected filenames, and taking one greater than the largest existing sequence. A single process owns one model folder. Detect concurrent creation through `FileExistsError` and stop rather than retrying with a new number.

`run_id` and model folder must pass the Step 1 safe-segment validation. The model folder must resolve to exactly one confirmed registry entry. Reject an unknown folder before reading or writing run objects.

### Resume and identity rules

Before any Bedrock call:

1. Load the prepared input manifest and records objects.
2. Verify the records bytes against the manifest SHA-256.
3. Parse every record through `Study2InputRecord` and reject duplicate IDs.
4. Apply the optional positive `--limit` to the fully validated records, preserving their prepared input order. When omitted, select all prepared records. The resulting ordered records are the requested set for this run and manifest.
5. Load and validate existing manifest objects under the selected run and model folder, then reject a configured limit that differs from the current run.
6. Load every prediction object under the selected run and model folder.
7. Parse every prediction through `PredictionRecord`.
8. Reject mismatched run IDs, model folders, model IDs, duplicate prediction IDs, unknown post IDs, or schema-invalid records.
9. Define completed IDs only as requested post IDs with one valid prediction.
10. Preserve requested input order and remove completed IDs to form the pending list.

Do not treat a failure row as completed. On a later run, retry a failed post unless it now has a valid prediction. Do not call Bedrock when no IDs are pending. Still publish a new immutable manifest that describes the observed state.

`--limit` is optional and must be a positive integer when present. It exists only for bounded smoke inference. Validate the complete prepared input and its digest before applying the limit, so a small run cannot hide malformed or duplicate records later in the input. A run and model folder must keep the same configured limit across runs, so reject a limit that differs from an existing manifest. A smoke run must use a run ID reserved for smoke artifacts. Each full-model run must use its own production run ID and omit `--limit`. Do not resume a full run from a limited smoke run.

### Batch rules

Process pending records in prepared input order. Batch size and max tokens are explicit CLI options with positive integer validation and documented defaults. Within one input batch, bounded concurrency is allowed, but output records must return to prepared input order before serialization.

For each input batch:

1. Call the thin LLM wrapper once for each pending post.
2. Convert each success to one `PredictionRecord`, including that call's token usage.
3. Convert each exception to one `FailureRecord` without aborting the remaining records in that batch. The wrapper call count is one because the experiment calls `converse_label` once per record. Do not claim to know how many internal attempts the engine made.
4. Write at most one immutable prediction JSONL object and one immutable failure JSONL object for the batch, omitting an empty side.
5. Stop the run immediately if an immutable write collides or fails. Do not publish a manifest that claims an unwritten result.

The sum of per-record token usage is derived later. Do not store only aggregate token counts.

## Caller-first implementation phases

### Phase 0: Confirm scope

Name `run.py::main` as the only caller. Limit one run to one run ID and one model folder. The caller applies the Step 1 credential adapter before constructing the S3 store or Bedrock client. Do not add a four-model supervisor or analysis path.

**Gate:** exactly one caller, one per-model task, and the five allowed files are named.

### Phase 1: Scaffold

Create the new packages, public signatures, imports, and a thin caller showing parse, load, resume, infer, write, and manifest calls. Bodies must remain `...` or raise `NotImplementedError`.

Run:

```bash
PYTHONPATH=. uv run python -c "from experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run import main; from experiments.zero_shot_llm_inference_2026_09_30.shared.llm import label_record; print('step2-imports-ok')"
```

Expected output:

```text
step2-imports-ok
```

**Gate:** imports resolve, the caller shows the entire per-model flow, and no Bedrock or storage behavior exists.

### Phase 2: Confirm contracts

Add only the inference models, path signatures, LLM wrapper signature, run function signature, and documented exception behavior. Keep reads, Bedrock calls, and writes stubbed.

**Gate:** schema fields, run paths, resume identity, immutability, Bedrock public API, and per-record token usage match this step. Stop for plan review before Phase 3 unless the reviewer has approved this step file without revisions.

### Phase 3: Implement pure contracts

Implement the pure behavior needed to satisfy these scenarios:

1. Given two pending records and a fake client with valid Converse responses, when the public run function executes, then it calls the exact requested model ID, sends the rendered issue prompt as the user text with each pair in unchanged order, and writes ordered predictions with per-record token usage.
2. Given an existing valid prediction for the first input ID, when the run resumes, then the fake client receives only the remaining IDs and the old prediction object remains unchanged.
3. Given only valid predictions for every input ID, when the run resumes, then the fake client receives no calls and a complete manifest is written.
4. Given a historical failure without a prediction, when the run resumes, then the failed ID is retried.
5. Given one success and one raised exception in a batch, when the batch completes, then separate immutable prediction and failure JSONL objects are written and the manifest is incomplete.
6. Given a later valid prediction for the failed ID, when state is summarized, then unresolved failures are zero while the historical failure object remains listed.
7. Given duplicate predictions, a mismatched model ID, a mismatched run ID, an unknown post ID, invalid JSONL, or an input digest mismatch, when state loads, then it raises before any Bedrock call.
8. Given validated records in prepared order and a positive `--limit`, when the requested set is built, then it contains only the first limited records, pending-ID selection occurs within that set, and the manifest records both the configured limit and limited requested count.
9. Given malformed or duplicate prepared records after the requested limit boundary, when a limited run loads input, then it rejects the full prepared input before selecting the limited requested set or calling Bedrock.
10. Given an existing manifest for a limited run, when a later run changes or omits the limit, then it rejects the configuration before creating a client.
11. Given an unknown model folder, unsafe run ID, nonpositive limit, nonpositive batch size, or nonpositive max tokens, when arguments validate, then it raises before creating a client.
12. Given an existing target sequence key or simulated `FileExistsError`, when an immutable write runs, then the run stops and never replaces the object.
13. Given Bedrock usage values, when `PredictionRecord` is created, then exact input, output, and total token counts are retained for that record.

### Phase 4: Implement one unit at a time

Implement in caller dependency order. After each unit, run an import check or a focused read-only Python command against the public function that was completed. Use injected public collaborators, not boto3 or AWS, for checks that exercise the caller boundary.

1. Inference schemas and identity validation.
2. Run, model, prediction, failure, and manifest key builders.
3. Prepared input loading and digest verification.
4. Positive optional limit validation and ordered requested-set selection.
5. Existing manifest, prediction, and failure loading.
6. Completed and pending ID calculation within the requested set.
7. Thin `converse_label` wrapper and token usage mapping.
8. Ordered batch execution and per-record outcome conversion.
9. Immutable prediction and failure batch writes.
10. State recount and immutable model manifest write.
11. `run.py::main` CLI wiring with `create_bedrock_runtime_client`.

Do not combine units, alter Step 1 contracts silently, or refactor the Bedrock engine.

### Phase 5: Verify the caller

Run:

```bash
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help
```

Expected result: exit code 0. Help lists required `--run-id` and `--model`, the optional positive `--limit`, and options for positive batch size, bounded concurrency, and max tokens. It must not create a Bedrock client or access S3.

Do not run live inference in this step's verification. Step 3 owns model-access smoke checks and full runs. Its smoke commands must pass a positive `--limit` and use a separate smoke run ID. Its full-run commands must omit `--limit`.

## Pass

- The caller handles exactly one confirmed model folder and one safe run ID.
- The implementation uses only `create_bedrock_runtime_client` and `converse_label` at the Bedrock boundary.
- Every success contains a validated label, unrounded probability, and exact per-record input, output, and total token usage.
- Every prediction, failure, and manifest object is immutable and below the selected model folder.
- Resume logic skips only IDs with one valid prediction and retries unresolved failures.
- A positive optional limit is applied only after complete prepared-input validation and before pending-ID selection.
- Existing object corruption or identity conflicts fail before any new model call.
- Output order follows the prepared input regardless of completion order.

## Fail

- A resumed run calls Bedrock again for a completed ID.
- A failure row permanently suppresses a retry.
- A prediction lacks a label, probability, or per-record token usage.
- The model label and probability violate the Step 1 threshold contract.
- Any write replaces, appends to, or deletes an S3 object.
- A process writes outside `runs/RUN_ID/MODEL_FOLDER/`.
- An unknown model folder or unsafe run ID reaches client construction.
- A missing limit restricts the requested set, a nonpositive limit is accepted, or a full run reuses a limited smoke run ID.
- The implementation calls a private Bedrock helper, duplicates Converse parsing, or changes `data_platform/**`.
- A direct local check unexpectedly accesses live Bedrock or S3.
- Any forbidden file changes.
