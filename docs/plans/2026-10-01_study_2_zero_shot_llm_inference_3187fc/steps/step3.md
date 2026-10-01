# Step 3: Verify each model and run inference

## Scope

- **Main caller:** `experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run:main`
- **Task:** verify the inference contract, run one smoke prediction per model, run four full model processes in parallel, and accept the run only when every model has 13,992 valid unique predictions and no unresolved failures.
- **Repository changes:** none. Commands read repository code and registered data, then write generated artifacts only to `s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/`.
- **Out of scope:** changing inference behavior or schemas, calculating metrics, rendering results, editing documentation, and probing alternate model IDs.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/engines/bedrock_engine.py`

## Files allowed to change

None.

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/**`
- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`

## Fixed inputs and outputs

Use these model folder and Bedrock model ID pairs without substitution:

| Model folder | Bedrock model ID |
|---|---|
| `amazon_nova_micro` | `us.amazon.nova-micro-v1:0` |
| `qwen3_32b` | `qwen.qwen3-32b-v1:0` |
| `openai_gpt_5_6_terra` | `us.openai.gpt-5.6-terra` |
| `claude_sonnet_5_5` | `us.anthropic.claude-sonnet-5-5` |

The prepared input is the Step 1 manifest for exactly 13,992 unique posts with five labelers. The full run writes under:

```text
s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/
  runs/RUN_ID/
    amazon_nova_micro/
    qwen3_32b/
    openai_gpt_5_6_terra/
    claude_sonnet_5_5/
```

The smoke run uses a different run ID and the same four folder names. It must never add a partial smoke result to the full run.

## Preconditions

1. Step 1 has written the prepared records and manifest to S3 and printed `rows=13992 unique_post_ids=13992 unanimous_rows=4051 split_rows=9941`.
2. Step 2's caller imports and supports `--run-id`, `--model`, and a positive optional `--limit` that selects the first records in prepared-input order.
3. AWS credentials are set through the standard variables or the experiment's lab credential adapter.
4. The AWS identity has access to all four fixed Bedrock model IDs in `us-east-2` and can read and write the experiment S3 prefix.

## Caller-first execution phases

### Phase 0: Confirm the operational contract

Confirm that `run:main` follows one path: parse one model folder, load the prepared input, discover completed immutable batches, call Bedrock only for missing post IDs, write new immutable batches and the run manifest, then verify the model folder.

Do not change the caller during this step. Return to Step 2 if the CLI flags, model mapping, resume rule, or completion check does not match this contract.

**Pass:** one caller owns smoke, full, resume, and completion-check modes for one model folder.

**Fail:** an operator must use a second entry point, edit a manifest by hand, or select a raw model ID that bypasses the fixed mapping.

### Phase 1: Check the caller contract

```bash
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help
```

**Expected output:** exit zero. Help lists required `--run-id` and `--model`, optional positive `--limit`, and positive batch size, bounded concurrency, and max-token options. It must not create a Bedrock client or access S3.

**Pass:** the public caller exposes the confirmed interface without accessing a remote service.

**Fail:** the command errors, omits a required option, or accesses Bedrock or S3.

### Phase 2: Run one smoke prediction per model

Choose an immutable full run ID, and use the same value for all four full processes. The commands below use an explicit example:

```bash
RUN_ID=study2-zero-shot-2026-10-01
SMOKE_RUN_ID="${RUN_ID}-smoke"
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$SMOKE_RUN_ID" --model amazon_nova_micro --limit 1
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$SMOKE_RUN_ID" --model qwen3_32b --limit 1
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$SMOKE_RUN_ID" --model openai_gpt_5_6_terra --limit 1
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$SMOKE_RUN_ID" --model claude_sonnet_5_5 --limit 1
```

**Expected output for each command:** exit zero and print the run ID and model folder with `expected=1`, `unique_valid_predictions=1`, and `unresolved_failures=0`.

Given one prepared post, when the caller runs a fixed model, then it stores one schema-valid Boolean remove label and one remove probability from zero through one. The label is true when the probability is at least `0.5` and false when it is below `0.5`.

**Pass:** all four commands exit zero, and each smoke manifest reports one valid unique prediction and no unresolved failure.

**Fail:** any call uses a model ID outside the fixed mapping, returns an invalid response, records an unresolved failure, or writes outside the smoke run prefix. Do not start the full processes.

### Phase 3: Start four full processes in parallel

Run from one shell after the smoke gate passes:

```bash
mkdir -p /tmp/mirrorview-zero-shot-logs
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model amazon_nova_micro > /tmp/mirrorview-zero-shot-logs/amazon_nova_micro.log 2>&1 &
NOVA_PID=$!
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model qwen3_32b > /tmp/mirrorview-zero-shot-logs/qwen3_32b.log 2>&1 &
QWEN_PID=$!
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model openai_gpt_5_6_terra > /tmp/mirrorview-zero-shot-logs/openai_gpt_5_6_terra.log 2>&1 &
TERRA_PID=$!
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model claude_sonnet_5_5 > /tmp/mirrorview-zero-shot-logs/claude_sonnet_5_5.log 2>&1 &
CLAUDE_PID=$!
wait "$NOVA_PID"; NOVA_STATUS=$?
wait "$QWEN_PID"; QWEN_STATUS=$?
wait "$TERRA_PID"; TERRA_STATUS=$?
wait "$CLAUDE_PID"; CLAUDE_STATUS=$?
test "$NOVA_STATUS" -eq 0 && test "$QWEN_STATUS" -eq 0 && test "$TERRA_STATUS" -eq 0 && test "$CLAUDE_STATUS" -eq 0
```

The disposable local logs stay under `/tmp`. Prediction, failure, usage, and run metadata artifacts go to S3 only.

**Expected output:** the final `test` exits zero. Each log ends with `expected=13992`, `unique_valid_predictions=13992`, and `unresolved_failures=0` for its model folder.

**Pass:** all four processes exit zero and keep every write inside their own model folder.

**Fail:** any process exits nonzero, writes a duplicate post ID, overwrites an immutable batch, or writes into another model's folder.

### Phase 4: Resume failures without repeating completed work

If one process exits nonzero or its manifest is incomplete, rerun the exact command for only that model with the same `RUN_ID`. Do not create a replacement run ID. Do not delete batches or failure records.

```bash
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model MODEL_FOLDER
```

Replace `MODEL_FOLDER` with one folder name from the fixed mapping.

Given immutable completed batches, when the same command is rerun, then the caller validates and skips their post IDs before any Bedrock request. Given a recorded failure without a valid prediction, the rerun may retry that post and must preserve the earlier failure record. A later valid prediction resolves the post for completion but does not erase history.

**Expected output:** the summary reports skipped completed post IDs, new valid predictions, and unresolved failures. A complete rerun reports `unique_valid_predictions=13992` and `unresolved_failures=0`.

**Pass:** completed post IDs produce zero repeat Bedrock calls, immutable objects remain unchanged, and only missing or unresolved post IDs are attempted.

**Fail:** the rerun repeats completed calls, changes an existing object, hides failure history, or counts more than one prediction for a post ID.

### Phase 5: Gate analysis on all four complete manifests

Rerun the ordinary caller once per model. A complete model has no pending IDs, so the caller must make no Bedrock calls and must publish a new immutable manifest describing the verified state.

```bash
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model amazon_nova_micro
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model qwen3_32b
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model openai_gpt_5_6_terra
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --run-id "$RUN_ID" --model claude_sonnet_5_5
```

**Expected output for each command:** exit zero and print `expected=13992 unique_valid_predictions=13992 unresolved_failures=0`, plus the fixed model folder and model ID.

**Pass:** the four folders contain 55,968 schema-valid predictions, exactly 13,992 unique prepared post IDs per model, no extra IDs, no duplicates, and zero unresolved failures.

**Fail:** any manifest is missing, has the wrong model ID or input identity, has a count other than 13,992, contains an unknown or duplicate ID, or has an unresolved failure. Do not run Step 4.

## What done looks like

1. The setup and inference callers import, and the inference help command matches the confirmed interface.
2. Each fixed model succeeds on one isolated smoke prediction.
3. Four parallel full processes use one run ID and separate model folders.
4. Safe reruns skip completed post IDs and preserve immutable artifacts and failure history.
5. All completion-check reruns report exactly 13,992 unique valid predictions and zero unresolved failures without calling Bedrock.
6. Step 3 leaves the repository byte-for-byte unchanged.
