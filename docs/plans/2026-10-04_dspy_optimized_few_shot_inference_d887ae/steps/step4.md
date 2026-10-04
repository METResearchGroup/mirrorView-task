# Step 4: Run Nova Micro and Qwen 3 32B

## Proposal sections implemented

- Cross-cutting concerns, Prompt identity
- Cross-cutting concerns, Models and analysis
- File structure, S3
- Step 4, Run the two model folders

## Scope

- Caller: `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step2_inference/main.py` `main`
- Task: Prove one live request for each allowed model, then run all 13,992 prepared rows for both models with resume support.
- Out of scope: repository edits, models outside the variant, analysis writes, result tables, and deletion of S3 objects.

## Files to inspect

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/docs/plans/2026-10-04_dspy_optimized_few_shot_inference_d887ae/proposal.md`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/shared/config.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step2_inference/main.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`

## Files allowed to change

No repository file may change in this step. The inference caller may create prediction, failure, and manifest objects only under these run prefixes:

- `s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/runs/study2-dspy-optimized-few-shot-2026-10-04-smoke/`
- `s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/runs/study2-dspy-optimized-few-shot-2026-10-04/`

## Files and objects forbidden to change

- Every repository file
- Prepared input objects from Step 3
- Existing baseline few-shot, zero-shot, and DSPy optimization objects
- Any `openai_gpt_5_6_terra` or `claude_sonnet_5_5` folder under the optimized experiment
- Analysis objects

## Preflight

Confirm the Step 3 input verification passed. Map AWS credentials as in Step 3, then require both new run prefixes to be empty:

```bash
for candidate_run_id in \
  study2-dspy-optimized-few-shot-2026-10-04-smoke \
  study2-dspy-optimized-few-shot-2026-10-04; do
  aws s3api list-objects-v2 \
    --bucket mirrorview-experimental-artifacts \
    --prefix "experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/runs/$candidate_run_id/" \
    --region us-east-2 \
    --query 'length(Contents || `[]`)' \
    --output text
done
```

Both lines must be `0`. Stop on any nonzero count and do not delete existing objects.

Confirm model filtering before a live request:

```bash
if PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main --run-id rejected-model-check --model openai_gpt_5_6_terra --limit 1; then
  echo "disabled model unexpectedly ran" >&2
  exit 1
else
  echo "disabled-model-rejected"
fi
```

The command must fail before creating an AWS client or writing an object. The final stdout line is `disabled-model-rejected`.

## Live smoke run

```bash
export OPTIMIZED_SMOKE_RUN_ID=study2-dspy-optimized-few-shot-2026-10-04-smoke
OPTIMIZED_SMOKE_LOG_DIR=/tmp/mirrorview-dspy-optimized-few-shot-smoke
mkdir -p "$OPTIMIZED_SMOKE_LOG_DIR"

{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main --run-id "$OPTIMIZED_SMOKE_RUN_ID" --model amazon_nova_micro --limit 1 --batch-size 1 --max-concurrency 1; } >"$OPTIMIZED_SMOKE_LOG_DIR/amazon_nova_micro.log" 2>&1
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main --run-id "$OPTIMIZED_SMOKE_RUN_ID" --model qwen3_32b --limit 1 --batch-size 1 --max-concurrency 1; } >"$OPTIMIZED_SMOKE_LOG_DIR/qwen3_32b.log" 2>&1
rg -n "expected=1 unique_valid_predictions=1 unresolved_failures=0|^real " "$OPTIMIZED_SMOKE_LOG_DIR"/*.log
```

Both commands must exit 0. Each log contains one completion summary and one `real` timing line.

Verify the stored smoke objects:

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
import os

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.shared.config import OPTIMIZED_FEW_SHOT_VARIANT

models = {
    "amazon_nova_micro": "us.amazon.nova-micro-v1:0",
    "qwen3_32b": "qwen.qwen3-32b-v1:0",
}
run_id = os.environ["OPTIMIZED_SMOKE_RUN_ID"]
store = CampaignObjectStore(OPTIMIZED_FEW_SHOT_VARIANT.s3_bucket, region_name="us-east-2")
keys = store.list_keys(f"{OPTIMIZED_FEW_SHOT_VARIANT.s3_root}runs/{run_id}/")
prediction_total = 0
failure_total = 0
for folder, model_id in models.items():
    prediction_keys = sorted(key for key in keys if f"/{folder}/predictions/" in key)
    manifest_keys = sorted(key for key in keys if f"/{folder}/manifests/" in key)
    failure_keys = sorted(key for key in keys if f"/{folder}/failures/" in key)
    rows = []
    for key in prediction_keys:
        stored = store.get(key)
        assert stored is not None
        rows.extend(json.loads(line) for line in stored.body.decode().splitlines())
    assert len(rows) == 1
    row = rows[0]
    assert row["run_id"] == run_id
    assert row["model_folder"] == folder and row["model_id"] == model_id
    assert 0.0 <= row["p_remove"] <= 1.0
    assert row["is_remove"] == (row["p_remove"] >= 0.5)
    assert row["usage"]["total_tokens"] == row["usage"]["input_tokens"] + row["usage"]["output_tokens"]
    manifest_object = store.get(manifest_keys[-1])
    assert manifest_object is not None
    manifest = json.loads(manifest_object.body)
    assert manifest["configured_limit"] == 1 and manifest["status"] == "complete"
    assert manifest["experiment_name"] == OPTIMIZED_FEW_SHOT_VARIANT.experiment_name
    assert manifest["prompt_name"] == OPTIMIZED_FEW_SHOT_VARIANT.prompt_name
    assert manifest["prompt_sha256"] == OPTIMIZED_FEW_SHOT_VARIANT.prompt_sha256
    for key in failure_keys:
        stored = store.get(key)
        assert stored is not None
        failure_total += len(stored.body.decode().splitlines())
    prediction_total += len(rows)
assert prediction_total == 2 and failure_total == 0
print("optimized-smoke-ok models=2 predictions=2 failures=0")
PY
```

Expected stdout is exactly `optimized-smoke-ok models=2 predictions=2 failures=0`. Repeat both smoke commands with the same arguments, and compare the prediction and failure key lists before and after. No new prediction or failure batch may appear. A new terminal manifest is allowed.

## Complete run

Start one process per model so the two model folders run in parallel:

```bash
export OPTIMIZED_RUN_ID=study2-dspy-optimized-few-shot-2026-10-04
export OPTIMIZED_RUN_LOG_DIR=/tmp/mirrorview-dspy-optimized-few-shot-run
mkdir -p "$OPTIMIZED_RUN_LOG_DIR"

{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main --run-id "$OPTIMIZED_RUN_ID" --model amazon_nova_micro; } >"$OPTIMIZED_RUN_LOG_DIR/amazon_nova_micro.log" 2>&1 &
nova_pid=$!
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main --run-id "$OPTIMIZED_RUN_ID" --model qwen3_32b; } >"$OPTIMIZED_RUN_LOG_DIR/qwen3_32b.log" 2>&1 &
qwen_pid=$!
wait "$nova_pid"
wait "$qwen_pid"
rg -n "expected=13992 unique_valid_predictions=13992 unresolved_failures=0|^real " "$OPTIMIZED_RUN_LOG_DIR"/*.log
```

Both processes must exit 0. Each log must contain the matching model identity, the complete count summary, and one `real` timing line.

## Verify the complete run

Load the verified prepared input and both completed model folders through the shared readers:

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
import os

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.shared.config import OPTIMIZED_FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import (
    load_run_inputs,
    validate_run_inputs,
)

run_id = os.environ["OPTIMIZED_RUN_ID"]
store = CampaignObjectStore(OPTIMIZED_FEW_SHOT_VARIANT.s3_bucket, region_name="us-east-2")
loaded = load_run_inputs(store, run_id, OPTIMIZED_FEW_SHOT_VARIANT)
validate_run_inputs(loaded)
assert tuple(run.model_folder for run in loaded.model_runs) == OPTIMIZED_FEW_SHOT_VARIANT.model_folders
usage = {}
for run in loaded.model_runs:
    manifest = run.manifest
    assert manifest.configured_limit is None
    assert manifest.status.value == "complete"
    assert manifest.requested_record_count == 13_992
    assert manifest.completed_prediction_count == 13_992
    assert manifest.unresolved_failure_count == 0
    assert manifest.experiment_name == OPTIMIZED_FEW_SHOT_VARIANT.experiment_name
    assert manifest.prompt_name == OPTIMIZED_FEW_SHOT_VARIANT.prompt_name
    assert manifest.prompt_sha256 == OPTIMIZED_FEW_SHOT_VARIANT.prompt_sha256
    assert len(run.predictions) == 13_992
    usage[run.model_folder] = {
        "predictions": len(run.predictions),
        "input_tokens": sum(row.usage.input_tokens for row in run.predictions),
        "output_tokens": sum(row.usage.output_tokens for row in run.predictions),
    }
print("usage_totals=" + json.dumps(usage, sort_keys=True))
print("optimized-run-ok models=2 predictions=27984 failures=0")
PY
```

Save the `usage_totals` line with the two log files for Step 5. The final summary line must be `optimized-run-ok models=2 predictions=27984 failures=0`. The shared readers and validators assert the following for each folder:

- The latest full-run manifest has `configured_limit` set to `None`, status `complete`, 13,992 requested rows, 13,992 predictions, and zero unresolved failures.
- Experiment name, prompt name, prompt digest, input key, input digest, schema version, folder, and model ID match the optimized variant.
- Prediction post IDs are unique and equal the prepared input IDs.
- Every probability is within 0 to 1, every label matches the 0.5 threshold, and every token total equals input plus output tokens.

## Must pass

- Both smoke calls produce one valid prediction and no unresolved failure.
- A repeated smoke call performs no additional Bedrock request for the completed row.
- Both complete model folders contain 13,992 unique valid predictions and no unresolved failure.
- Nova and Qwen write only below their own folders and use the exact optimized prompt identity.

## Must fail

- Any model outside the active two-model set.
- Any prompt, experiment, schema, input, run, folder, or model identity mismatch.
- Any invalid probability, threshold-inconsistent label, duplicate prediction, unknown post ID, or unresolved failure.
- Any complete-run start before both smoke models pass.
