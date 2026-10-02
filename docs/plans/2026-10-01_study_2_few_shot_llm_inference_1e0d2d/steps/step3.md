# Step 3: Add and smoke the few-shot inference caller

## Proposal sections implemented

- Cross-cutting concerns: Reuse boundary
- Cross-cutting concerns: Models and response contract
- Cross-cutting concerns: Stored artifact identity
- Step 4: Run the four model folders

## Scope

- **Caller:** `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step2_inference/main.py` `main`
- **Task:** Parameterize the reusable inference runner, add the thin few-shot caller, and prove all four model paths with one live record each.
- **Out of scope:** The complete 55,968-call run, analysis, results publication, probability normalization, and unit tests.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_llm_inference_1e0d2d/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/llm.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/engines/bedrock_engine.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/llm.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step2_inference/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step2_inference/main.py` (new)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/engines/bedrock_engine.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`
- All experiment documentation in this step
- Every `tests/` directory and every new test file

## Inference contract

Expose `run_inference_cli(variant, prompt_formatter)`. Keep the existing zero-shot `main` as a wrapper that supplies `ZERO_SHOT_VARIANT` and the zero-shot formatter. The few-shot `main` supplies `FEW_SHOT_VARIANT` and the few-shot formatter and contains no inference logic.

Pass the active variant and formatter through run planning, prepared-input loading, resume loading, batch reads and writes, individual record labeling, prediction and failure construction, manifest construction, and identity validation. Every new stored row uses the active variant's schema version. Every new manifest explicitly stores the active experiment name, prompt name, and prompt digest.

Preserve ordered concurrent batches, immutable storage, retry and failure behavior, token usage, threshold validation, command arguments, and one-model-per-process ownership. Resume must reject an existing model folder with a different configured limit, input digest, model identity, experiment identity, prompt identity, or schema version.

Do not normalize an out-of-range probability. Preserve the failure and stop or retry through the existing schema path. A new normalization policy requires separate review.

## Import and path smoke contract

```bash
PYTHONPATH=. uv run python - <<'PY'
from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT
from experiments.few_shot_llm_inference_2026_09_30.shared.prompts import BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT
from experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main import main
from experiments.zero_shot_llm_inference_2026_09_30.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import build_model_run_prefix

assert FEW_SHOT_VARIANT.s3_root != ZERO_SHOT_VARIANT.s3_root
assert build_model_run_prefix(FEW_SHOT_VARIANT, "run", "amazon_nova_micro").startswith(FEW_SHOT_VARIANT.s3_root)
assert "few-shot" in FEW_SHOT_VARIANT.experiment_name
assert BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT
assert callable(main)
print("variant-paths-ok")
PY
PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --help >/dev/null
```

Expected stdout is exactly `variant-paths-ok`. The help command exits 0 without making an AWS request.

## Live smoke callers

Run only after Step 2 passes. Map AWS credentials, then use a dedicated smoke run ID:

```bash
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
export SMOKE_RUN_ID=study2-few-shot-2026-10-01-smoke
SMOKE_LOG_DIR=/tmp/mirrorview-few-shot-smoke-logs
mkdir -p "$SMOKE_LOG_DIR"

{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --model amazon_nova_micro --limit 1 --batch-size 1 --max-concurrency 1; } >"$SMOKE_LOG_DIR/amazon_nova_micro.log" 2>&1
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --model qwen3_32b --limit 1 --batch-size 1 --max-concurrency 1; } >"$SMOKE_LOG_DIR/qwen3_32b.log" 2>&1
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --model openai_gpt_5_6_terra --limit 1 --batch-size 1 --max-concurrency 1; } >"$SMOKE_LOG_DIR/openai_gpt_5_6_terra.log" 2>&1
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --model claude_sonnet_5_5 --limit 1 --batch-size 1 --max-concurrency 1; } >"$SMOKE_LOG_DIR/claude_sonnet_5_5.log" 2>&1
rg -n "expected=1 unique_valid_predictions=1 unresolved_failures=0|^real " "$SMOKE_LOG_DIR"/*.log
```

Each command must exit 0. Each log contains the correct run ID, model folder, model ID, the completion summary, and a final `real` timing line. The model identity is:

| Folder | Model ID |
| --- | --- |
| `amazon_nova_micro` | `us.amazon.nova-micro-v1:0` |
| `qwen3_32b` | `qwen.qwen3-32b-v1:0` |
| `openai_gpt_5_6_terra` | `us.openai.gpt-5.6-terra` |
| `claude_sonnet_5_5` | `us.anthropic.claude-sonnet-5-5` |

The completion summary is:

```text
expected=1 unique_valid_predictions=1 unresolved_failures=0
```

Validate the stored smoke objects:

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
import os

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT

models = {
    "amazon_nova_micro": "us.amazon.nova-micro-v1:0",
    "qwen3_32b": "qwen.qwen3-32b-v1:0",
    "openai_gpt_5_6_terra": "us.openai.gpt-5.6-terra",
    "claude_sonnet_5_5": "us.anthropic.claude-sonnet-5-5",
}
run_id = os.environ["SMOKE_RUN_ID"]
store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket, region_name="us-east-2")
prefix = f"{FEW_SHOT_VARIANT.s3_root}runs/{run_id}/"
keys = store.list_keys(prefix)
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
    assert row["schema_version"] == FEW_SHOT_VARIANT.prediction_schema_version
    assert row["run_id"] == run_id and row["model_folder"] == folder and row["model_id"] == model_id
    assert 0.0 <= row["p_remove"] <= 1.0 and row["is_remove"] == (row["p_remove"] >= 0.5)
    assert row["usage"]["total_tokens"] == row["usage"]["input_tokens"] + row["usage"]["output_tokens"]
    manifest_object = store.get(manifest_keys[-1])
    assert manifest_object is not None
    manifest = json.loads(manifest_object.body)
    assert manifest["configured_limit"] == 1 and manifest["status"] == "complete"
    assert manifest["experiment_name"] == FEW_SHOT_VARIANT.experiment_name
    assert manifest["prompt_name"] == FEW_SHOT_VARIANT.prompt_name
    assert manifest["prompt_sha256"] == FEW_SHOT_VARIANT.prompt_sha256
    for key in failure_keys:
        stored = store.get(key)
        assert stored is not None
        failure_total += len(stored.body.decode().splitlines())
    prediction_total += len(rows)
assert prediction_total == 4 and failure_total == 0
print("few-shot-smoke-ok models=4 predictions=4 failures=0")
PY
```

Expected stdout is exactly `few-shot-smoke-ok models=4 predictions=4 failures=0`. Record each log's `real` value and each prediction's input and output tokens for `RESULTS.md`. Record cost only from a documented rate source current on the run date.

Before the no-pending rerun, record the sorted prediction and failure keys under the smoke prefix. Rerun the same four commands without `/usr/bin/time`, record those keys again, and use `cmp` to prove no prediction or failure batch was added. A new terminal manifest is allowed. Each rerun prints the same completion summary.

```bash
SMOKE_PREFIX="experiments/few_shot_llm_inference_2026_09_30/runs/$SMOKE_RUN_ID/"
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix "$SMOKE_PREFIX" --region us-east-2 --query 'sort_by(Contents[?contains(Key, `/predictions/`) || contains(Key, `/failures/`)],&Key)[].Key' --output text > /tmp/few-shot-smoke-keys-before.txt
for model in amazon_nova_micro qwen3_32b openai_gpt_5_6_terra claude_sonnet_5_5; do
  PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --model "$model" --limit 1 --batch-size 1 --max-concurrency 1
done
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix "$SMOKE_PREFIX" --region us-east-2 --query 'sort_by(Contents[?contains(Key, `/predictions/`) || contains(Key, `/failures/`)],&Key)[].Key' --output text > /tmp/few-shot-smoke-keys-after.txt
cmp /tmp/few-shot-smoke-keys-before.txt /tmp/few-shot-smoke-keys-after.txt
```

All four commands report `expected=1 unique_valid_predictions=1 unresolved_failures=0`, and `cmp` exits 0.

## Must pass

- The zero-shot and few-shot callers use the same inference runner with different explicit configurations and formatters.
- All four smoke calls produce one valid prediction and no unresolved failure.
- Each model writes only below its own folder under the few-shot smoke run.
- Repeating the identical smoke command resumes without another Bedrock call and reports the same completed state.

## Must fail

- Any prompt, experiment, model, schema, input digest, or configured-limit mismatch during resume.
- An unknown model folder, invalid path segment, duplicate prediction, unknown post ID, or threshold-inconsistent response.
- Any smoke model failure. Do not start the complete run until all four pass.

## Commit

Commit only the allowed files with a message such as `feat: add few-shot Study 2 inference caller`.
