# Step 5: Run full few-shot Jev inference

The work implements the production-run half of proposal section "Step 4: Run few-shot Jev inference" and the inference part of "Expected results." Plan Step 4 already proved the caller on five rows. The production run uses the same caller and immutable S3 layout to score all 13,992 prepared rows, resume interrupted work, and record measured runtime and usage in `RESULTS.md`.

## Caller and scope

- Caller: `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/main.py`.
- Happy path: preflight AWS and Jev access, validate the prepared input, run or resume one production run, recount immutable predictions and failures, write a complete run manifest, then record measured runtime and usage.
- Production run ID: `study2-jev-few-shot-2026-10-01`.
- The production run requires no new implementation. If the five-row smoke contract from Step 4 is not complete, stop and return to Step 4.
- No unit test file or persistent smoke script is allowed. The production caller and read-only inline verification commands are the executable specification for this step.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/proposal.md`, especially "Prompt contract," "Data and S3 isolation," "Model and response contract," and "Expected results."
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/SETUP.md`.
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md`.
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/config.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/jev.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/main.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py`.
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py`.
- `/Users/mark/src/work/mirrorview-wt/shared/models/jev/client.py`.

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md`.

## Files forbidden to change

- Every Python file. A production-run defect returns to the step that introduced that code.
- Every file under `/Users/mark/src/work/mirrorview-wt/shared/models/jev/`.
- Every file under `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/`.
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/SETUP.md` and `README.md`.
- Any file under `tests/`, any `test_*.py` file, and any persistent smoke script.
- The zero-shot Jev S3 prefix and the issue 329 few-shot LLM S3 prefix.
- Any local copy of prediction, failure, manifest, or analysis artifacts. The artifacts stay in S3.

## Contracts

### Identity

The production run uses Jev 1.13.0, `FEW_SHOT_VARIANT`, and the run ID `study2-jev-few-shot-2026-10-01`. Every new manifest stores:

- experiment name `few_shot_jev_inference_2026_10_01`;
- source prompt SHA-256 `ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3`;
- transformed-instructions SHA-256 `a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac`;
- input-record SHA-256 equal to the verified input manifest;
- no configured limit, batch size 500, and 8 workers.

The resume path rejects any stored manifest whose run ID, model, experiment, prompt identity, input digest, limit, batch size, or worker count differs. It never mixes predictions from another configuration into this run.

### Resume and failure behavior

- The caller reads and validates all stored manifests, predictions, and failures before it starts new requests.
- A valid stored prediction skips that post ID. A prior failure does not block a retry. A later valid prediction resolves that post ID.
- Prediction, failure, and manifest objects are create-only. A key collision or invalid stored row fails without overwriting the object.
- Request exceptions become immutable failure rows. The caller writes a recounted manifest after the pass.
- When the recounted manifest is incomplete, do not analyze, edit results, use a new run ID, or delete an object. Rerun the exact production command so it resumes the same run. Treat `status=incomplete` as a stop signal regardless of the process exit code.
- Success requires 13,992 unique valid predictions, zero unresolved failures, and a final manifest with status `complete`. Historical failure rows may remain because they are immutable.

### Measurement

`RESULTS.md` records the production run ID, S3 run prefix, wall-clock runtime from `/usr/bin/time`, input tokens, output tokens, and USD cost. Token totals come from the 13,992 stored prediction rows, not console output or an estimate. Cost uses the pinned Jev input and output prices.

## Implementation

### 1. Confirm the caller and the five-row gate

From the repository root, confirm that the production CLI still exposes the Step 4 options and that `RESULTS.md` contains a successful five-row smoke record.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main --help
rg -n "smoke_run_id=study2-jev-few-shot-2026-10-01-smoke" /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
rg -n "rows=5" /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
rg -n "predictions=5" /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
rg -n "unresolved_failures=0" /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
rg -n "status=complete" /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
rg -n "real_seconds=[0-9]+([.][0-9]+)? input_tokens=[1-9][0-9]* output_tokens=[0-9]+ usd=[0-9]+[.][0-9]{6}" /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
```

Expected: the help exits zero and lists `--run-id`, `--limit`, `--batch-size`, and `--max-workers`. The search finds the completed five-row smoke record. Stop if it does not.

### 2. Run the read-only AWS, secret, input, and resume preflight

The command uses the repository credential adapter. It verifies access without printing credentials or secret values and reports whether the production prefix is new or resumable. Existing objects are not an error because the run is designed to resume.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
import boto3

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import InputManifest
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    parse_study2_input_jsonl_bytes,
    sha256_hex,
)
from shared.models.jev.client import get_jev_api_key

run_id = "study2-jev-few-shot-2026-10-01"
apply_lab_aws_credentials_when_unset()
boto3.client("sts").get_caller_identity()
store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket)
manifest_object = store.get(FEW_SHOT_VARIANT.input_manifest_key)
records_object = store.get(FEW_SHOT_VARIANT.input_records_key)
assert manifest_object is not None, FEW_SHOT_VARIANT.input_manifest_key
assert records_object is not None, FEW_SHOT_VARIANT.input_records_key
manifest = InputManifest.model_validate_json(manifest_object.body)
records = parse_study2_input_jsonl_bytes(records_object.body)
assert manifest.records_s3_key == FEW_SHOT_VARIANT.input_records_key
assert sha256_hex(records_object.body) == manifest.records_sha256
assert (manifest.total_record_count, manifest.unanimous_record_count, manifest.split_record_count) == (
    13_992,
    4_051,
    9_941,
)
assert len(records) == 13_992
assert len({record.post_id for record in records}) == 13_992
assert get_jev_api_key().strip()
run_prefix = f"{FEW_SHOT_VARIANT.s3_prefix}runs/{run_id}/jev_1_13_0/"
existing = store.list_keys(run_prefix)
state = "new" if not existing else "resume"
print(f"aws_ok=true jev_secret_ok=true input_rows=13992 input_sha256={manifest.records_sha256}")
print(f"run_state={state} existing_objects={len(existing)} run_prefix=s3://{FEW_SHOT_VARIANT.s3_bucket}/{run_prefix}")
PY
```

Expected first line: `aws_ok=true jev_secret_ok=true input_rows=13992 input_sha256=<64 lowercase hexadecimal characters>`. Expected second line: `run_state=new` with zero objects on the first attempt, or `run_state=resume` with a positive object count after an interrupted or incomplete attempt. Any exception is a hard stop.

### 3. Run or resume all 13,992 rows

Use one fixed run ID and the default batch and worker settings. Do not pass `--limit`.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. /usr/bin/time -p uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main \
  --run-id study2-jev-few-shot-2026-10-01 \
  --batch-size 500 \
  --max-workers 8
```

Expected successful summary shape:

```text
run_id=study2-jev-few-shot-2026-10-01 model_folder=jev_1_13_0 model_id=jev-1.13.0 expected=13992 skipped=<0..13992> new_predictions=<0..13992> new_failures=0 unique_valid_predictions=13992 unresolved_failures=0 input_tokens=<positive integer> output_tokens=<nonnegative integer> status=complete
real <measured seconds>
user <measured seconds>
sys <measured seconds>
```

If the summary reports `status=incomplete`, keep the output as evidence and rerun this exact command. A resume must report a positive `skipped` count and must not issue a second request for a post ID that already has a valid prediction. Do not proceed until the command reports the complete summary. A nonzero exit is also a hard stop, but an incomplete summary blocks progress even if the command exits zero.

### 4. Recount the immutable production state and calculate usage

The verification reads the latest manifest and its declared prediction objects. It allows historical failure objects but requires zero unresolved failures.

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.shared.schemas import JevRunManifest
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import PredictionRecord
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    parse_jsonl_document_bytes,
)
from shared.models.jev.constants import (
    JEV_USD_PER_MILLION_INPUT,
    JEV_USD_PER_MILLION_OUTPUT,
)

run_id = "study2-jev-few-shot-2026-10-01"
apply_lab_aws_credentials_when_unset()
store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket)
run_prefix = f"{FEW_SHOT_VARIANT.s3_prefix}runs/{run_id}/jev_1_13_0/"
manifest_keys = [key for key in store.list_keys(run_prefix + "manifests/") if key.endswith(".json")]
assert manifest_keys, "run has no manifest"
manifest_object = store.get(manifest_keys[-1])
assert manifest_object is not None
manifest = JevRunManifest.model_validate_json(manifest_object.body)
assert manifest.run_id == run_id
assert manifest.model_folder == "jev_1_13_0"
assert manifest.model_id == "jev-1.13.0"
assert manifest.experiment_name == FEW_SHOT_VARIANT.experiment_name
assert manifest.prompt_name == FEW_SHOT_VARIANT.prompt_name
assert manifest.prompt_sha256 == "ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3"
assert manifest.instructions_sha256 == "a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac"
assert manifest.configured_limit is None
assert manifest.configured_batch_size == 500
assert manifest.max_workers == 8
assert manifest.requested_record_count == 13_992
assert manifest.completed_prediction_count == 13_992
assert manifest.unresolved_failure_count == 0
assert manifest.status.value == "complete"
predictions = []
for key in manifest.prediction_object_keys:
    stored = store.get(key)
    assert stored is not None, key
    predictions.extend(parse_jsonl_document_bytes(stored.body, PredictionRecord))
assert len(predictions) == 13_992
assert len({row.post_id for row in predictions}) == 13_992
assert all(row.run_id == run_id for row in predictions)
assert all(row.model_folder == "jev_1_13_0" and row.model_id == "jev-1.13.0" for row in predictions)
input_tokens = sum(row.usage.input_tokens for row in predictions)
output_tokens = sum(row.usage.output_tokens for row in predictions)
usd = round(
    (
        input_tokens * JEV_USD_PER_MILLION_INPUT
        + output_tokens * JEV_USD_PER_MILLION_OUTPUT
    )
    / 1_000_000,
    6,
)
print(
    f"status=complete predictions=13992 unresolved_failures=0 "
    f"input_tokens={input_tokens} output_tokens={output_tokens} usd={usd:.6f}"
)
print(f"final_manifest=s3://{FEW_SHOT_VARIANT.s3_bucket}/{manifest_keys[-1]}")
PY
```

Expected first line: `status=complete predictions=13992 unresolved_failures=0 input_tokens=<positive integer> output_tokens=<nonnegative integer> usd=<six decimal places>`. The second line names the final immutable manifest. A duplicate post ID, missing object, identity mismatch, prompt mismatch, or count mismatch fails the step.

### 5. Record measured production values

Edit only `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md`. Add the fixed run ID and S3 prefix, measured wall-clock runtime, 13,992 predictions, zero unresolved failures, input tokens, output tokens, and USD cost. Keep the Step 4 smoke measurement clearly labeled as smoke data. Replace any production estimate with the measured production value, but do not invent a value that the commands did not print.

### 6. Verify the step diff and commit

```bash
git -C /Users/mark/src/work/mirrorview-wt diff --check
git -C /Users/mark/src/work/mirrorview-wt diff --name-only
git -C /Users/mark/src/work/mirrorview-wt add -- /Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
git -C /Users/mark/src/work/mirrorview-wt diff --cached --name-only
git -C /Users/mark/src/work/mirrorview-wt commit -m "Run few-shot Jev inference"
```

Expected unstaged and staged path for this step:

```text
experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
```

Do not use `git add .`. The worktree may contain unrelated user files.

## Pass and fail criteria

Pass only when all of the following are true:

- the production manifest is complete for all 13,992 rows;
- 13,992 unique valid prediction rows exist and zero failures remain unresolved;
- stored experiment, model, prompt, input, limit, batch, and worker identities match this step;
- measured runtime and usage are in `RESULTS.md`;
- only `RESULTS.md` changed in this step;
- commit `Run few-shot Jev inference` exists.

Fail and stop when any preflight fails, the CLI remains incomplete, an immutable object conflicts, stored identity differs, a post ID is missing or duplicated, a measurement cannot be reproduced, or any forbidden file changed.
