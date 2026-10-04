# Step 1: Parameterize the zero-shot Jev pipeline

## Proposal sections implemented

- "Cross-cutting concerns: Reuse boundary"
- "Cross-cutting concerns: Data and S3 isolation"
- "Schema and key interfaces"
- "Step 1: Parameterize the completed zero-shot Jev runners"

## Goal

Add one immutable experiment configuration and pass it through setup, storage, inference, and analysis. Keep the three zero-shot command lines unchanged. Older zero-shot run manifests must still parse, and rerunning the completed zero-shot analysis must reproduce the existing six artifact bodies byte for byte.

Run every command from `/Users/mark/src/work/mirrorview-wt` with `PYTHONPATH=.`.

## Scope

- **Main caller:** `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py::main`.
- **Happy path:** the zero-shot `main` calls `run_inference_cli(ZERO_SHOT_VARIANT, build_remove_request)`, which loads the same prepared input, resumes from the same run prefix, writes the same prediction and failure schemas, and writes a run manifest with explicit zero-shot prompt identity.
- **Compatibility callers:** the existing setup `main` and analysis `main` remain zero-argument wrappers around the zero-shot configuration.
- **Unit of work:** replace zero-shot path and prompt globals below the command wrappers with one explicit `JevInferenceVariant`.
- **Out of scope:** the few-shot package, the few-shot prompt, live few-shot calls, changes to Jev 1.13.0, new dependencies, unit tests, checked-in smoke scripts, and changes to existing S3 objects.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/proposal.md`, especially "Reuse boundary", "Prompt contract", "Data and S3 isolation", and "Schema and key interfaces"
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/render.py`, read only
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/prompts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/config.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/models/jev/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/render.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/RESULTS.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/**`
- Every `tests/` directory, every `test_*.py` file, and every checked-in smoke script

## Contracts

### Experiment configuration

Create `JevInferenceVariant` as a frozen dataclass in `shared/config.py`. It has exactly these fields:

```python
experiment_name: str
s3_bucket: str
s3_prefix: str
input_records_key: str
input_manifest_key: str
run_manifest_schema_version: str
prompt_name: str
prompt_sha256: str
instructions_sha256: str
metric_exclusion_post_ids: tuple[str, ...]
```

Reject an empty field, an `s3_prefix` without a trailing slash, an input key outside that prefix, a digest that is not 64 lowercase hexadecimal characters, or duplicate exclusion IDs. Do not add a registry, base class, or dependency.

Define `ZERO_SHOT_VARIANT` with the current bucket, prefix, input keys, and run-manifest schema version. Use prompt name `baseline_zero_shot_keep_remove`, source prompt SHA-256 `bbec6228173d04e0adafa871b6dc3751cbc1e8972f29cd49d45df7ca736a46ec`, transformed-instructions SHA-256 `924ad1e6a145a7e0b587ad8c5d0889c53133e6ea69f67bd64cad7b3a2214ac24`, and no metric exclusions. Keep existing constants as compatibility aliases to fields on `ZERO_SHOT_VARIANT`.

### Request boundary

Define `RemoveRequestBuilder` as `Callable[[Study2InputRecord], ClassifierRequest]`. Change `build_remove_request` to accept an optional compiled-instructions argument whose default is the existing `REMOVE_INSTRUCTIONS`. An unchanged call, `build_remove_request(record)`, must produce the same `ClassifierRequest` as `origin/main`.

### Storage boundary

Every key builder must derive its root from an explicit variant. Preserve current positional callers by keeping `run_id` and `sequence` in their current positions and adding `variant: JevInferenceVariant = ZERO_SHOT_VARIANT` as a keyword-only final argument.

This applies to `build_run_prefix`, `build_predictions_prefix`, `build_failures_prefix`, `build_manifests_prefix`, `build_analysis_prefix`, `build_prediction_batch_key`, `build_failure_batch_key`, and `build_manifest_key`. Private storage helpers also receive the variant. Supplying a nonzero variant must never return a zero-shot key.

### Setup boundary

Keep `prepare_input(store) -> InputManifest` and `main()` unchanged for the zero-shot command. Add:

```python
copy_prepared_input(
    store: CampaignObjectStore,
    source: JevInferenceVariant,
    target: JevInferenceVariant,
) -> InputManifest
```

`copy_prepared_input` reads `source.input_records_key` and `source.input_manifest_key`, validates the digest, counts, uniqueness, and sorted post IDs through the existing validation path, and writes the record bytes unchanged to the target. It writes a new `InputManifest` whose `records_s3_key` is `target.input_records_key`; every other field matches the source manifest. It writes records first and the manifest second with `put_new`. A collision propagates without overwriting an object.

Do not replace the zero-shot `prepare_input` with `copy_prepared_input(ZERO_SHOT_VARIANT, ZERO_SHOT_VARIANT)`. The zero-shot command still copies issue 326's upstream keys into the zero-shot prefix.

### Inference boundary

Use the proposal signature:

```python
run_inference(
    store: CampaignObjectStore,
    scorer: JevScorer,
    variant: JevInferenceVariant,
    request_builder: RemoveRequestBuilder,
    run_id: str,
    limit: int | None,
    batch_size: int,
    max_workers: int,
) -> JevRunManifest
```

Pass `variant` through prepared-input loading, every key builder, stored manifest validation, prediction and failure identity validation, batch writes, recounting, and manifest construction. Pass `request_builder` through `_write_scored_batches`, `_score_batch_in_order`, and `_score_one`. The zero-shot `main()` supplies `ZERO_SHOT_VARIANT` and `build_remove_request`. Its options, help text, validation order, summary text, concurrency, retries, resume rules, and exception-to-failure mapping remain unchanged.

Expose `run_inference_cli(variant: JevInferenceVariant, request_builder: RemoveRequestBuilder) -> None`. It owns argument parsing, option validation, credentials, object-store and scorer construction, and the call to `run_inference`. The existing zero-shot `main() -> None` contains only `run_inference_cli(ZERO_SHOT_VARIANT, build_remove_request)`.

### Run-manifest compatibility

Extend `JevRunManifest` with `experiment_name`, `prompt_name`, `prompt_sha256`, and `instructions_sha256`. All four fields are nonempty. Their defaults are the values on `ZERO_SHOT_VARIANT`, so every manifest already stored by PR 341 parses unchanged. New manifests always pass the active variant values explicitly.

Manifest identity validation rejects a schema version, experiment name, prompt name, source digest, transformed digest, run ID, model folder, or model ID that differs from the active configuration. Resume option checks remain unchanged.

### Analysis boundary and byte compatibility

Use the proposal signature:

```python
run_analysis(
    store: CampaignObjectStore,
    variant: JevInferenceVariant,
    run_id: str,
) -> str
```

Pass `variant` through prepared-input loading, run-manifest selection, prediction loading and validation, analysis key construction, metrics, and artifact writing. Add `metric_exclusion_post_ids: tuple[str, ...] = ()` to `JevAnalysisManifest`.

`build_analysis_tables` accepts the exclusion IDs. It validates that every exclusion ID exists once in the prepared input. It removes exclusions only from the three model-metric partitions. Human label counts, split-vote counts, completeness checks, prediction usage, and pinned label checks continue to use all prepared rows.

Serialize `JevAnalysisManifest` with `exclude_defaults=True`. The zero-shot default is empty, so `metric_exclusion_post_ids` is absent from a regenerated zero-shot manifest. This is required to keep the existing `analysis_manifest.json` body and SHA-256 unchanged. The zero-shot `main()` supplies `ZERO_SHOT_VARIANT`; its CLI and success line remain unchanged.

Expose `run_analysis_cli(variant: JevInferenceVariant) -> None`. It owns argument parsing, run-ID validation, credentials, object-store construction, and the call to `run_analysis`. The existing zero-shot `main() -> None` contains only `run_analysis_cli(ZERO_SHOT_VARIANT)`.

## Caller-first implementation phases

The user approved the full plan and requested one commit per step. Do not pause after contracts, and do not create the test files normally used by `implement-from-spec`. The given, when, then cases below become inline Python assertions. Work through the phases in order, but make one commit only after the entire step passes.

### Phase 1: Confirm the unit of work

Confirm the main caller, allowed file list, and happy path above. Record the `origin/main` zero-shot help output and the six existing analysis-object hashes before editing. Stop if `origin/main` does not contain PR 341.

### Phase 2: Scaffold the variant boundary

Add `shared/config.py`, the final dataclass fields, the type alias, and typed variant parameters. Keep compatibility defaults on existing key builders and `build_remove_request`. Do not add behavior beyond wiring. Imports and both zero-shot help commands must still resolve before continuing.

### Phase 3: Confirm contracts

Confirm every signature and schema field against this file. Keep new behavior stubbed until the contract smoke can import all symbols. Because this modifies a working pipeline, do not commit a stubbed or broken intermediate state.

### Phase 4: Design executable checks

Use these cases as the executable specification. The commands in Step 1 exercise cases 1, 2, 3, and 6 before the Step 1 commit. Steps 3, 4, and 6 exercise cases 4, 5, and 7 through the real callers and stored artifacts. Do not claim a case passed until its named step runs the corresponding command.

1. Given a legacy run-manifest payload without prompt identity, when Pydantic validates it, then the four zero-shot defaults appear.
2. Given a variant with another prefix, when every key builder runs, then no key starts with the zero-shot prefix.
3. Given one record, when the default request builder runs, then its serialized request equals the pre-change request.
4. Given the verified source input bytes and manifest, when the Step 3 caller runs `copy_prepared_input`, then record bytes are identical and the target manifest changes only `records_s3_key`.
5. Given five prepared rows and the live Jev scorer, when the Step 4 caller runs twice, then the first pass writes five predictions and the second pass skips all five.
6. Given the completed zero-shot S3 analysis, when analysis runs again, then all six object hashes remain unchanged.
7. Given the five verified exclusions, when Step 6 builds and verifies the stored tables, then only metric sample counts shrink.

### Phase 5: Implement in dependency order

Implement and smoke one unit at a time in this order:

1. `JevInferenceVariant` validation and `ZERO_SHOT_VARIANT`.
2. Compatibility aliases in `shared/constants.py`.
3. Variant-aware storage key builders.
4. `RemoveRequestBuilder` and the compiled-instructions argument.
5. Backward-compatible `JevRunManifest` fields and identity validation.
6. `copy_prepared_input`, while preserving `prepare_input`.
7. Variant and request-builder threading through inference.
8. Analysis exclusion handling and manifest serialization.
9. `run_inference_cli`, `run_analysis_cli`, and the three zero-shot command wrappers.

After each unit, run the import and compilation checks below. Do not refactor `shared/models/jev`, the issue 326 package, or the Markdown renderer.

### Phase 6: Verify and commit

Run every smoke check and inspect the final diff. Commit the allowed files once with:

```bash
git add experiments/zero_shot_jev_inference_2026_10_01/shared/config.py \
  experiments/zero_shot_jev_inference_2026_10_01/shared/constants.py \
  experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py \
  experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py \
  experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py \
  experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py \
  experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py \
  experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py
git commit -m "refactor: parameterize Study 2 Jev inference"
```

## Smoke checks

### Imports, compilation, and unchanged CLIs

```bash
PYTHONPATH=. uv run python -m compileall -q \
  experiments/zero_shot_jev_inference_2026_10_01 && echo compileall-ok
PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.shared.config import JevInferenceVariant, ZERO_SHOT_VARIANT; from experiments.zero_shot_jev_inference_2026_10_01.src.step1_setup.prepare import copy_prepared_input, main as setup_main; from experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run import main as inference_main, run_inference, run_inference_cli; from experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze import main as analysis_main, run_analysis, run_analysis_cli; print('zero-shot-imports-ok')"
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run --help
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze --help
```

Expected first two lines:

```text
compileall-ok
zero-shot-imports-ok
```

The inference help still describes `Run resumable zero-shot Jev inference.` with required `--run-id` and optional `--limit`, `--batch-size`, and `--max-workers`. The analysis help still describes `Analyze one complete Jev Study 2 run.` with required `--run-id`. Neither help command accesses AWS or Jev.

```bash
set +e
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step2_inference.run --run-id ../bad 2> /tmp/mirrorview-jev-invalid-run-id.err
status=$?
set -e
test "$status" -eq 2
test "$(cat /tmp/mirrorview-jev-invalid-run-id.err)" = "path segment must not contain slashes"
echo invalid-run-id-ok
```

Expected stdout is exactly `invalid-run-id-ok`.

### Legacy manifest and storage isolation

```bash
PYTHONPATH=. uv run python - <<'PY'
from dataclasses import replace

from experiments.zero_shot_jev_inference_2026_10_01.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.shared.schemas import JevRunManifest
from experiments.zero_shot_jev_inference_2026_10_01.shared.storage import (
    build_analysis_prefix,
    build_failure_batch_key,
    build_failures_prefix,
    build_manifest_key,
    build_manifests_prefix,
    build_prediction_batch_key,
    build_predictions_prefix,
    build_run_prefix,
)

legacy = JevRunManifest.model_validate({
    "schema_version": "study2-zero-shot-jev-run-v1",
    "run_id": "legacy",
    "model_display_name": "Jev 1.13.0",
    "model_folder": "jev_1_13_0",
    "model_id": "jev-1.13.0",
    "prepared_input_records_key": ZERO_SHOT_VARIANT.input_records_key,
    "prepared_input_records_sha256": "0" * 64,
    "configured_batch_size": 1,
    "max_workers": 1,
    "configured_limit": 1,
    "requested_record_count": 1,
    "completed_prediction_count": 1,
    "unresolved_failure_count": 0,
    "prediction_object_keys": ("prediction.jsonl",),
    "failure_object_keys": (),
    "status": "complete",
})
assert legacy.experiment_name == ZERO_SHOT_VARIANT.experiment_name
assert legacy.prompt_name == ZERO_SHOT_VARIANT.prompt_name
assert legacy.prompt_sha256 == ZERO_SHOT_VARIANT.prompt_sha256
assert legacy.instructions_sha256 == ZERO_SHOT_VARIANT.instructions_sha256

other = replace(
    ZERO_SHOT_VARIANT,
    experiment_name="jev-smoke",
    s3_prefix="experiments/jev-smoke/",
    input_records_key="experiments/jev-smoke/inputs/records.jsonl",
    input_manifest_key="experiments/jev-smoke/inputs/manifest.json",
)
keys = {
    build_run_prefix("run", variant=other),
    build_predictions_prefix("run", variant=other),
    build_failures_prefix("run", variant=other),
    build_manifests_prefix("run", variant=other),
    build_analysis_prefix("run", variant=other),
    build_prediction_batch_key("run", 0, variant=other),
    build_failure_batch_key("run", 0, variant=other),
    build_manifest_key("run", 0, variant=other),
}
assert len(keys) == 8
assert all(key.startswith(other.s3_prefix) for key in keys)
assert all(not key.startswith(ZERO_SHOT_VARIANT.s3_prefix) for key in keys)
print("legacy-manifest-and-storage-ok")
PY
```

Expected stdout is exactly `legacy-manifest-and-storage-ok`.

### Zero-shot request bytes

```bash
PYTHONPATH=. uv run python - <<'PY'
import hashlib

from experiments.zero_shot_jev_inference_2026_10_01.shared.jev import (
    REMOVE_INSTRUCTIONS,
    build_remove_request,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import Study2InputRecord

assert hashlib.sha256(REMOVE_INSTRUCTIONS.encode("utf-8")).hexdigest() == "924ad1e6a145a7e0b587ad8c5d0889c53133e6ea69f67bd64cad7b3a2214ac24"
record = Study2InputRecord(
    post_id="smoke",
    post_1_text="one",
    post_2_text="two",
    gold_is_remove=False,
    n_keep=5,
    n_remove=0,
    n_raters=5,
    is_unanimous=True,
)
default_request = build_remove_request(record)
explicit_request = build_remove_request(record, instructions=REMOVE_INSTRUCTIONS)
assert default_request == explicit_request
assert default_request["state"] == {"post_1": "one", "post_2": "two"}
assert default_request["questions"]["is_remove"].instructions == REMOVE_INSTRUCTIONS
print("zero-shot-request-ok")
PY
```

Expected stdout is exactly `zero-shot-request-ok`.

### Existing zero-shot artifact bytes

The check is read-only except for calling analysis against six objects that must already exist. `_write_or_verify` performs no write when the bytes match. Stop before the analysis call unless the object count is exactly six.

```bash
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
ZERO_ANALYSIS_URI="s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/analysis/study2-jev-zero-shot-2026-10-01/"
ZERO_HASH_DIR=$(mktemp -d /tmp/mirrorview-zero-jev-hashes.XXXXXX)
test "$(aws s3 ls "$ZERO_ANALYSIS_URI" --recursive | wc -l | tr -d ' ')" -eq 6
aws s3 cp "$ZERO_ANALYSIS_URI" "$ZERO_HASH_DIR/before" --recursive --only-show-errors
find "$ZERO_HASH_DIR/before" -type f -print0 | sort -z | xargs -0 shasum -a 256 > "$ZERO_HASH_DIR/before.sha256"
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze --run-id study2-jev-zero-shot-2026-10-01
aws s3 cp "$ZERO_ANALYSIS_URI" "$ZERO_HASH_DIR/after" --recursive --only-show-errors
find "$ZERO_HASH_DIR/after" -type f -print0 | sort -z | xargs -0 shasum -a 256 | sed "s#$ZERO_HASH_DIR/after#$ZERO_HASH_DIR/before#" > "$ZERO_HASH_DIR/after.sha256"
cmp "$ZERO_HASH_DIR/before.sha256" "$ZERO_HASH_DIR/after.sha256"
echo zero-shot-artifacts-byte-identical
```

Expected analysis stdout:

```text
analysis_prefix=experiments/zero_shot_jev_inference_2026_10_01/analysis/study2-jev-zero-shot-2026-10-01/ input_rows=13992 unanimous_rows=4051 split_rows=9941 models=1 metric_rows=3 artifacts=6
```

The final line is exactly `zero-shot-artifacts-byte-identical`.

### Scope and no-test guard

```bash
git diff --name-only origin/main | rg '(^|/)(tests?/|test_[^/]*\.py$)' && exit 1 || echo no-test-files
git diff --name-only origin/main -- shared/models/jev experiments/zero_shot_llm_inference_2026_09_30 data_platform
```

Expected output is `no-test-files`, followed by no forbidden paths.

## Must pass

- The current zero-shot setup, inference, and analysis help commands retain their arguments and text.
- A stored PR 341 run manifest without the four new fields parses with zero-shot defaults.
- A nonzero variant cannot produce a zero-shot S3 key.
- The default zero-shot request uses the same transformed instructions digest.
- Rerunning the completed zero-shot analysis leaves all six S3 object hashes unchanged.
- No test file, test directory, or checked-in smoke script is added.

## Must fail

- A malformed variant or duplicate exclusion ID.
- A stored manifest whose explicit experiment, prompt, digest, schema, run, or model identity differs from the active variant.
- An unknown or duplicate metric-exclusion post ID.
- A few-shot key derived from a zero-shot global.
- Any change to a forbidden file or existing S3 object body.
