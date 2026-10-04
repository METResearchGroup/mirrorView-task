# Step 4: Smoke the few-shot inference path

## Proposal sections implemented

- Cross-cutting concerns: Reuse boundary
- Cross-cutting concerns: Prompt contract
- Cross-cutting concerns: Model and response contract
- Schema and key interfaces: `JevInferenceVariant`, `RemoveRequestBuilder`, and `JevRunManifest`
- Step 4: Run few-shot Jev inference

## Scope

- **Caller:** `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/main.py` `main`
- **Unit of work:** Run the first five prepared pairs through Jev 1.13.0 with the few-shot request builder, validate the stored results and prompt identity, then rerun the same command to prove completed pairs are skipped.
- **Out of scope:** The 13,992-row production run, analysis, final results publication, changes to Jev client code, unit tests, and persistent smoke scripts.

The work implements one thin inference caller. Step 1 owns `run_inference_cli` and the resumable runner. Step 2 owns `FEW_SHOT_VARIANT` and `build_few_shot_remove_request`. Step 3 owns the prepared input.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/steps/step1.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/steps/step2.md`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/steps/step3.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/jev.py`
- `/Users/mark/src/work/mirrorview-wt/shared/models/jev/constants.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/main.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md`

## Files forbidden to change

- Every file under `/Users/mark/src/work/mirrorview-wt/shared/models/jev/`
- Every file under `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/`
- Every few-shot Jev file not listed under files allowed to change
- Every `tests/` directory, every new test file, and every checked-in smoke script
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- All production-run and analysis S3 prefixes

## Caller contract

Expose the shared boundary from Step 1 with this signature:

```python
def run_inference_cli(
    variant: JevInferenceVariant,
    request_builder: RemoveRequestBuilder,
) -> None: ...
```

The existing zero-shot `main` remains a wrapper around `run_inference_cli(ZERO_SHOT_VARIANT, build_remove_request)`. The new few-shot `main` calls `run_inference_cli(FEW_SHOT_VARIANT, build_few_shot_remove_request)`. The few-shot file contains no argument parsing, AWS setup, scorer construction, batching, retries, storage, resume, or manifest logic.

The shared CLI retains the existing arguments `--run-id`, `--limit`, `--batch-size`, and `--max-workers`. `--help` must exit before it maps credentials, creates an S3 client, or creates a Jev scorer.

## Smoke run contract

Use run ID `study2-jev-few-shot-2026-10-01-smoke`, limit 5, batch size 5, and one worker. The smoke run uses the first five rows in prepared-input order. It writes only below:

```text
s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/runs/study2-jev-few-shot-2026-10-01-smoke/jev_1_13_0/
```

Each request uses `build_few_shot_remove_request`. The source prompt digest is `ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3`. The compiled instruction digest is `a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac`. The run manifest stores the experiment name, prompt name, both digests, prepared-input key and digest, configured limit, batch size, worker count, and Jev model identity.

Every successful prediction has `p_remove` in `[0, 1]`, `is_remove == (p_remove >= 0.5)`, and internally consistent token usage. The five stored post IDs must equal the first five prepared input post IDs. Any request error produces an unresolved failure and blocks Step 5.

Resume with the identical run identity and options. It may append a new terminal manifest, but it must not call Jev for a completed post ID or append a prediction or failure batch. Resume with a different limit, batch size, worker count, input digest, experiment identity, prompt identity, instruction identity, model identity, or schema version must fail before scoring.

## Implementation phases

### Phase 1: Confirm the caller boundary

Name the new `main` as the only caller for this unit of work. Confirm the shared CLI and few-shot request builder signatures from Steps 1 and 2.

### Phase 2: Scaffold the inference package

Step 2 already created `__init__.py`. Create `main.py` with only the two imports and a thin caller stub. Confirm that imports resolve before adding behavior.

### Phase 3: Wire the approved contract

Call the shared CLI with `FEW_SHOT_VARIANT` and `build_few_shot_remove_request`. Do not copy logic from the zero-shot runner.

### Phase 4: Run inline contract checks

Use the import, path, manifest, response, and resume assertions below. Do not create a test file or persistent smoke script.

### Phase 5: Execute five live requests

Run one worker against five rows. Capture `/usr/bin/time` output and the runner summary in a temporary log outside the repository.

### Phase 6: Verify resume and repository scope

Confirm that the identical rerun skips five rows and creates no prediction or failure batch. Confirm that a mismatched limit is rejected and that the step changed only its two allowed files.

## Import and identity checks

Run this before implementation. It must fail because the new caller does not exist. Run it again after wiring; it must print `few-shot-jev-inference-import-ok`.

```bash
PYTHONPATH=. uv run python - <<'PY'
from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.few_shot_jev_inference_2026_10_01.shared.jev import (
    FEW_SHOT_REMOVE_INSTRUCTIONS,
    build_few_shot_remove_request,
)
from experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main import main
from experiments.zero_shot_jev_inference_2026_10_01.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.shared.storage import build_run_prefix

assert callable(main)
assert callable(build_few_shot_remove_request)
assert FEW_SHOT_VARIANT.s3_prefix != ZERO_SHOT_VARIANT.s3_prefix
assert build_run_prefix("run", variant=FEW_SHOT_VARIANT) == (
    "experiments/few_shot_jev_inference_2026_10_01/runs/run/jev_1_13_0/"
)
assert FEW_SHOT_VARIANT.prompt_sha256 == "ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3"
assert FEW_SHOT_VARIANT.instructions_sha256 == "a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac"
assert "human annotators remove" in FEW_SHOT_REMOVE_INSTRUCTIONS
assert "human annotators keep" in FEW_SHOT_REMOVE_INSTRUCTIONS
print("few-shot-jev-inference-import-ok")
PY
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main --help >/dev/null
```

The help command exits 0 without an AWS or Jev request.

## Live five-row smoke

Run only after Step 3 passes:

```bash
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
aws sts get-caller-identity --output json
export SMOKE_RUN_ID=study2-jev-few-shot-2026-10-01-smoke
SMOKE_LOG=/tmp/few-shot-jev-smoke.log
{ /usr/bin/time -p env PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --limit 5 --batch-size 5 --max-workers 1; } >"$SMOKE_LOG" 2>&1
rg -n "expected=5 skipped=0 new_predictions=5 new_failures=0 unique_valid_predictions=5 unresolved_failures=0|input_tokens=|output_tokens=|status=complete|^real " "$SMOKE_LOG"
```

The command exits 0. Its summary contains:

```text
run_id=study2-jev-few-shot-2026-10-01-smoke model_folder=jev_1_13_0 model_id=jev-1.13.0 expected=5 skipped=0 new_predictions=5 new_failures=0 unique_valid_predictions=5 unresolved_failures=0
```

The same line ends with positive measured `input_tokens`, nonnegative measured `output_tokens`, and `status=complete`. The log ends with `real`, `user`, and `sys` timing lines. Preserve the measured `real` value and token totals for comparison with the production run. Do not extrapolate production totals from this sample.

## Validate the stored smoke artifacts

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
import os

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    PREDICTION_SCHEMA_VERSION,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    parse_study2_input_jsonl_bytes,
)
from shared.models.jev.constants import (
    JEV_MODEL_ID,
    JEV_USD_PER_MILLION_INPUT,
    JEV_USD_PER_MILLION_OUTPUT,
)

run_id = os.environ["SMOKE_RUN_ID"]
store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket, region_name="us-east-2")
input_object = store.get(FEW_SHOT_VARIANT.input_records_key)
assert input_object is not None
expected_ids = [row.post_id for row in parse_study2_input_jsonl_bytes(input_object.body)[:5]]
prefix = f"{FEW_SHOT_VARIANT.s3_prefix}runs/{run_id}/jev_1_13_0/"
keys = store.list_keys(prefix)
prediction_keys = sorted(key for key in keys if "/predictions/" in key and key.endswith(".jsonl"))
failure_keys = sorted(key for key in keys if "/failures/" in key and key.endswith(".jsonl"))
manifest_keys = sorted(key for key in keys if "/manifests/" in key and key.endswith(".json"))
assert prediction_keys and manifest_keys

predictions = []
for key in prediction_keys:
    stored = store.get(key)
    assert stored is not None
    predictions.extend(json.loads(line) for line in stored.body.decode("utf-8").splitlines())
failures = []
for key in failure_keys:
    stored = store.get(key)
    assert stored is not None
    failures.extend(json.loads(line) for line in stored.body.decode("utf-8").splitlines())
assert len(predictions) == 5 and not failures
assert [row["post_id"] for row in predictions] == expected_ids
assert len(set(expected_ids)) == 5
for row in predictions:
    assert row["schema_version"] == PREDICTION_SCHEMA_VERSION
    assert row["run_id"] == run_id
    assert row["model_folder"] == "jev_1_13_0" and row["model_id"] == JEV_MODEL_ID
    assert 0.0 <= row["p_remove"] <= 1.0
    assert row["is_remove"] == (row["p_remove"] >= 0.5)
    assert row["usage"]["input_tokens"] > 0
    assert row["usage"]["output_tokens"] >= 0
    assert row["usage"]["total_tokens"] == row["usage"]["input_tokens"] + row["usage"]["output_tokens"]

manifest_object = store.get(manifest_keys[-1])
assert manifest_object is not None
manifest = json.loads(manifest_object.body)
assert manifest["schema_version"] == FEW_SHOT_VARIANT.run_manifest_schema_version
assert manifest["run_id"] == run_id
assert manifest["experiment_name"] == FEW_SHOT_VARIANT.experiment_name
assert manifest["prompt_name"] == FEW_SHOT_VARIANT.prompt_name
assert manifest["prompt_sha256"] == "ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3"
assert manifest["instructions_sha256"] == "a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac"
assert manifest["prepared_input_records_key"] == FEW_SHOT_VARIANT.input_records_key
assert manifest["prepared_input_records_sha256"] == "1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395"
assert manifest["model_folder"] == "jev_1_13_0" and manifest["model_id"] == JEV_MODEL_ID
assert manifest["configured_limit"] == 5
assert manifest["configured_batch_size"] == 5
assert manifest["max_workers"] == 1
assert manifest["requested_record_count"] == 5
assert manifest["completed_prediction_count"] == 5
assert manifest["unresolved_failure_count"] == 0
assert manifest["status"] == "complete"
input_tokens = sum(row["usage"]["input_tokens"] for row in predictions)
output_tokens = sum(row["usage"]["output_tokens"] for row in predictions)
usd = round(
    (
        input_tokens * JEV_USD_PER_MILLION_INPUT
        + output_tokens * JEV_USD_PER_MILLION_OUTPUT
    )
    / 1_000_000,
    6,
)
print(
    f"few-shot-jev-smoke-ok predictions=5 failures=0 "
    f"input_tokens={input_tokens} output_tokens={output_tokens} usd={usd:.6f}"
)
PY
```

The command prints one line beginning `few-shot-jev-smoke-ok predictions=5 failures=0`. Its token totals match the runner summary, and its cost uses the pinned Jev prices.

## Resume without another Jev call

Capture the prediction and failure keys, rerun the identical caller, then compare keys:

```bash
SMOKE_PREFIX="experiments/few_shot_jev_inference_2026_10_01/runs/$SMOKE_RUN_ID/jev_1_13_0/"
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix "$SMOKE_PREFIX" --region us-east-2 --query 'sort_by(Contents[?contains(Key, `/predictions/`) || contains(Key, `/failures/`)],&Key)[].Key' --output text > /tmp/few-shot-jev-smoke-keys-before.txt
PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --limit 5 --batch-size 5 --max-workers 1
aws s3api list-objects-v2 --bucket mirrorview-experimental-artifacts --prefix "$SMOKE_PREFIX" --region us-east-2 --query 'sort_by(Contents[?contains(Key, `/predictions/`) || contains(Key, `/failures/`)],&Key)[].Key' --output text > /tmp/few-shot-jev-smoke-keys-after.txt
cmp /tmp/few-shot-jev-smoke-keys-before.txt /tmp/few-shot-jev-smoke-keys-after.txt
```

The rerun summary contains:

```text
expected=5 skipped=5 new_predictions=0 new_failures=0 unique_valid_predictions=5 unresolved_failures=0
```

It ends with the same token totals and `status=complete`. The final `cmp` exits 0. A new terminal manifest is allowed.

Prove that a changed run contract is rejected:

```bash
if PYTHONPATH=. uv run python -m experiments.few_shot_jev_inference_2026_10_01.src.step2_inference.main --run-id "$SMOKE_RUN_ID" --limit 4 --batch-size 5 --max-workers 1; then
  echo "mismatched resume unexpectedly succeeded" >&2
  exit 1
else
  echo "resume-contract-mismatch-rejected"
fi
```

Expected final stdout is `resume-contract-mismatch-rejected`. The command writes no prediction, failure, or manifest object.

## Record the smoke measurement

Edit `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md` after the stored-artifact and resume checks pass. Record the smoke run ID, five predictions, zero unresolved failures, `status=complete`, the measured `real` seconds, input tokens, output tokens, and six-decimal USD cost. Copy the values from the commands above. Do not estimate or extrapolate production values.

Use this exact machine-readable field set in one line so Step 5 can check every gate independently:

```text
smoke_run_id=study2-jev-few-shot-2026-10-01-smoke rows=5 predictions=5 unresolved_failures=0 status=complete real_seconds=<measured seconds> input_tokens=<positive integer> output_tokens=<nonnegative integer> usd=<six decimal places>
```

## Repository scope check

```bash
git diff --check
git diff --name-only -- experiments/few_shot_jev_inference_2026_10_01/src/step2_inference experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
PYTHONPATH=. uv run python - <<'PY'
import subprocess

allowed = {
    "experiments/few_shot_jev_inference_2026_10_01/RESULTS.md",
    "experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/main.py",
}
tracked = set(subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines())
untracked = set(
    subprocess.check_output(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "experiments/few_shot_jev_inference_2026_10_01/src/step2_inference",
        ],
        text=True,
    ).splitlines()
)
changed = tracked | untracked
assert changed == allowed, {"missing": sorted(allowed - changed), "unexpected": sorted(changed - allowed)}
print("step4-repository-scope-ok")
PY
```

The final command prints `step4-repository-scope-ok` when this step is reviewed in isolation from other plan steps.

## Must pass

- The thin few-shot caller supplies only `FEW_SHOT_VARIANT` and `build_few_shot_remove_request` to the shared CLI.
- The help path exits without accessing AWS or Jev.
- Five live requests produce five unique valid predictions for the first five prepared rows and no unresolved failure.
- The terminal manifest stores the few-shot experiment, source prompt, compiled instructions, input, model, option, and schema identities.
- The identical rerun skips all five rows and adds no prediction or failure batch.
- `RESULTS.md` contains the measured smoke gate with all required fields.
- The step adds no unit test file or persistent smoke script.

## Must fail

- Missing AWS credentials, a failed AWS identity lookup, or a missing prepared input.
- A changed experiment, source prompt, compiled instruction, input digest, Jev model, schema, limit, batch size, or worker count during resume.
- Any duplicate or unknown post ID, invalid probability, inconsistent label, invalid token total, or unresolved failure.
- Any live smoke result other than five complete predictions and zero unresolved failures.
- Any repository change outside the two allowed files.

## Commit

After every check passes, commit only the two allowed files with:

```bash
git add experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/main.py experiments/few_shot_jev_inference_2026_10_01/RESULTS.md
git commit -m "feat: add few-shot Jev inference caller"
```
