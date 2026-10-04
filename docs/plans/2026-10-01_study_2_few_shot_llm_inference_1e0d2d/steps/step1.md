# Step 1: Add the shared experiment contracts

## Proposal sections implemented

- Cross-cutting concerns: Reuse boundary
- Cross-cutting concerns: Models and response contract
- Cross-cutting concerns: Stored artifact identity
- Schema and key interfaces
- Step 1: Parameterize the completed issue 326 runners

## Scope

- **Primary boundary:** The configuration, storage, and manifest contracts exercised by the one-off smoke command
- **Task:** Add the experiment configuration, prompt formatter type, variant-aware S3 key construction, and manifest identity fields needed by both experiments. Keep zero-shot defaults until later steps connect each command caller explicitly.
- **Out of scope:** Few-shot files, setup copying, analysis exclusions, live Bedrock calls, and unit tests.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_llm_inference_1e0d2d/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/prompts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/llm.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/config.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/llm.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/RESULTS.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`
- Every `tests/` directory and every new test file

## Contract

Create an immutable `Study2InferenceVariant` dataclass without importing schemas. Its fields are `experiment_name`, `s3_bucket`, `s3_root`, `input_records_s3_key`, `input_manifest_s3_key`, `prediction_schema_version`, `failure_schema_version`, `model_run_schema_version`, `analysis_schema_version`, `prompt_name`, `prompt_sha256`, and `metric_exclusion_post_ids`. Define `ZERO_SHOT_VARIANT` from the existing zero-shot values. Keep existing constants as compatibility aliases where callers still need them.

Define `PromptFormatter` as a callable that receives two post strings and returns the rendered prompt. Step 3 changes `label_record` and its caller together, so this step does not leave the existing inference caller with a missing argument.

Every root-dependent storage key builder, prepared-input loader, serializer validator, and identity validator must accept the active variant. Keep a zero-shot default only where required to preserve an existing public call until Steps 2 through 4 pass the variant explicitly. By the end of Step 4, every internal caller must be explicit. A few-shot key must never be derived from a zero-shot global. Prediction and failure validation must use the active schema version.

Extend `ModelRunManifest` with `experiment_name`, `prompt_name`, and `prompt_sha256`. Defaults must match the zero-shot experiment so older issue 326 manifests still parse. New writes in later steps must provide the three active values explicitly. Identity validation must reject a manifest whose experiment or prompt identity differs from the active variant.

Do not introduce a base class, registry for experiment plugins, dependency, or duplicated serializer.

## Caller-first work order

1. Add `Study2InferenceVariant` and `ZERO_SHOT_VARIANT`.
2. Add `PromptFormatter` without changing the `label_record` call contract yet.
3. Add variant parameters and zero-shot compatibility defaults to root-dependent storage and schema validation functions.
4. Add backward-compatible model-run prompt identity.
5. Run the smoke contract below. Do not create a test file.

## Smoke contract

Run from `/Users/mark/src/work/mirrorview-wt`:

```bash
PYTHONPATH=. uv run python - <<'PY'
from experiments.zero_shot_llm_inference_2026_09_30.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import ModelRunManifest

assert ZERO_SHOT_VARIANT.prompt_sha256 == "bbec6228173d04e0adafa871b6dc3751cbc1e8972f29cd49d45df7ca736a46ec"
legacy = ModelRunManifest.model_validate({
    "schema_version": "study2-zero-shot-model-run-v1",
    "run_id": "legacy",
    "model_display_name": "Amazon Nova Micro",
    "model_folder": "amazon_nova_micro",
    "model_id": "us.amazon.nova-micro-v1:0",
    "prepared_input_records_key": ZERO_SHOT_VARIANT.input_records_s3_key,
    "prepared_input_records_sha256": "0" * 64,
    "configured_batch_size": 1,
    "configured_max_tokens": 1,
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
print("legacy-manifest-ok")
PY
```

Expected stdout is exactly `legacy-manifest-ok`.

```bash
PYTHONPATH=. uv run python -c "from experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare import main as setup_main; from experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run import main as inference_main; from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import main as analysis_main; print('zero-shot-imports-ok')"
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help >/dev/null
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze --help >/dev/null
```

Expected output from the first command is exactly `zero-shot-imports-ok`. Both help commands exit 0 without AWS access.

## Must pass

- Older zero-shot model-run manifests parse with zero-shot identity defaults.
- New manifest identity validation rejects an experiment-name, prompt-name, or prompt-digest mismatch.
- Zero-shot imports and help commands still work.
- Storage APIs cannot silently fall back to the zero-shot root when a different variant is supplied.
- No AWS object is read or written in this step.

## Must fail

- A variant with an invalid or empty root, key, schema version, prompt name, or prompt digest. Add these negative assertions to the one-off smoke command.
- Manifest parsing with an explicit wrong experiment, prompt name, or prompt digest once identity validation is called. Prediction, failure, and resume-path negative checks are completed in Step 3 after the runner is connected.

## Commit

Commit only the allowed files with a message such as `refactor: add Study 2 inference variant contracts`.
