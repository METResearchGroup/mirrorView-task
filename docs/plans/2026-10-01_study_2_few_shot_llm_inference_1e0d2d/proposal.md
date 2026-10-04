# Proposal: Few-shot keep or remove inference on the Study 2 dataset

Scope: [issue 329](https://github.com/METResearchGroup/mirrorView-task/issues/329). The proposal covers the few-shot Bedrock experiment, its S3 artifacts, and its analysis. It reuses the completed [issue 326](https://github.com/METResearchGroup/mirrorView-task/issues/326) implementation from [PR 333](https://github.com/METResearchGroup/mirrorView-task/pull/333) and the datasets from [issue 325](https://github.com/METResearchGroup/mirrorView-task/issues/325). DSPy and GEPA optimization from [issue 332](https://github.com/METResearchGroup/mirrorView-task/issues/332) remain outside this work.

## Overview

The new experiment will run the issue 329 few-shot prompt against the same 13,992 Study 2 pairs and four Bedrock models used by the zero-shot experiment. The implementation will keep the completed setup, inference, resume, storage, and analysis behavior in one place. The few-shot experiment will contain the prompt, one configuration record, and three thin `main.py` entry points.

The run will store 55,968 predictions, one for each pair and model. `RESULTS.md` will report the human label distributions, the split-vote distribution, and F1, accuracy, recall, and precision for the all, unanimous, and split datasets.

## Cross-cutting concerns

### Reuse boundary

Issue 329 refers to `experiments/few_shot_llm_inference_2026_09_30/` as its own reuse source, although that folder does not exist. The intended source is the completed zero-shot experiment at `experiments/zero_shot_llm_inference_2026_09_30/`.

The few-shot package will import the reusable runners, schemas, model registry, storage helpers, and analysis functions from the zero-shot package. The zero-shot package will never import from the few-shot package. The refactor will add one concrete experiment configuration type and one prompt formatter argument. It will not add a plugin system, base class hierarchy, or second copy of the inference code.

The public runners will accept a `Study2InferenceVariant` and, for inference, a `PromptFormatter`. Their existing zero-shot entry points will pass `ZERO_SHOT_VARIANT` and `format_baseline_zero_shot_keep_remove_prompt`, so the completed run remains readable and the zero-shot command behavior does not change.

| Existing code | Symbols reused by the few-shot experiment |
| --- | --- |
| `data_platform/generate_features/engines/bedrock_engine.py` | `create_bedrock_runtime_client`, `converse_label`, `BedrockUsage` |
| `experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py` | `Study2InputRecord`, `RemovePrediction`, `PredictionRecord`, `FailureRecord`, `ModelRunManifest`, `InputManifest` |
| `experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py` | JSON and JSONL serialization, SHA-256, immutable writes, prepared input loading, and run key builders |
| `experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/prepare.py` | `prepare_study2_five_labeler_input`, input validation, and manifest construction |
| `experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py` | `run_model_inference`, resume validation, ordered concurrent batches, and manifest writes |
| `experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py` | `run_analysis`, partition checks, descriptive counts, and classification metrics |
| `experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py` | `render_results_fragment` |

### Prompt identity and demonstration overlap

`BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT` will preserve the issue 329 text, example order, labels, placeholders, and line breaks. Each run manifest and analysis manifest will store the prompt name and SHA-256 digest. The digest will make a changed prompt a different run contract even when the run ID is reused.

A read-only audit compared the ten prompt demonstrations with the 13,992 prepared input rows. Normalization used Unicode normalization, lowercase text, punctuation removal, and whitespace collapse. Five demonstrations matched input rows: two remove examples and three keep examples. All five matched rows are in the unanimous dataset. The other five demonstrations did not have a deterministic normalized match and will not be excluded through subjective fuzzy matching.

The recommended analysis will still predict all 13,992 rows. Its metric tables will exclude the five matched demonstrations, which leaves 13,987 evaluation rows in all, 4,046 in unanimous, and 9,941 in split. The human label and split-vote tables will continue to describe the complete input. Decision 2 asks the reviewer to confirm this treatment.

### Data and S3 isolation

The setup entry point will read and verify the completed zero-shot input package. It will copy `records.jsonl` byte for byte into the few-shot prefix and write a new input manifest whose `records_s3_key` points to the few-shot copy. The records digest and row counts must match the issue 326 input manifest. The setup will not query the registered datasets again, so the zero-shot and few-shot runs use the same ordered input bytes.

All new generated artifacts will live under `s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/`. Existing zero-shot S3 objects and repository files remain in place. The implementation will not change the user's untracked `REPORT.md` or `probe_bedrock_models.py` files in the zero-shot folder.

### Models and response contract

The experiment will reuse `MODEL_REGISTRY` and `RemovePrediction` from issue 326. The models remain Amazon Nova Micro, Qwen 3 32B, OpenAI GPT-5.6 Terra, and Claude Sonnet 5.5 with the exact model IDs from issue 329. Each response must contain `is_remove` and `p_remove`, with `is_remove == (p_remove >= 0.5)`.

`label_record` will accept a prompt formatter instead of importing the zero-shot formatter directly. The Bedrock engine, concurrency, immutable batches, resume behavior, failure records, token usage, and model folder names remain unchanged. The work adds no dependency.

### Stored artifact identity

The existing prediction and failure shapes can represent both prompt variants. Their schema version comes from `Study2InferenceVariant`, so new few-shot rows use few-shot version strings while existing zero-shot rows retain their current version strings.

`ModelRunManifest` and `AnalysisManifest` will add `experiment_name`, `prompt_name`, and `prompt_sha256`. The new fields will have zero-shot defaults when older issue 326 manifests are loaded. New writes must supply all three fields from the active variant.

## File structure

### Repository

```text
docs/plans/2026-10-01_study_2_few_shot_llm_inference_1e0d2d/
  proposal.md                                      this proposal

experiments/zero_shot_llm_inference_2026_09_30/
  shared/
    config.py                                      new reusable Study2InferenceVariant and ZERO_SHOT_VARIANT
    constants.py                                   route zero-shot paths and versions through ZERO_SHOT_VARIANT
    llm.py                                         accept an injected PromptFormatter
    schemas.py                                     store prompt identity in ModelRunManifest
    storage.py                                     build keys from the active variant
  src/
    step1_setup/prepare.py                         expose the reusable setup runner
    step2_inference/run.py                         expose the reusable inference runner
    step3_analysis/analyze.py                      expose the reusable analysis runner and manifest identity

experiments/few_shot_llm_inference_2026_09_30/
  README.md                                        links to SETUP.md and RESULTS.md
  SETUP.md                                         required input data and artifact locations
  RESULTS.md                                       generated result tables and run identity
  shared/
    __init__.py
    config.py                                      FEW_SHOT_VARIANT
    prompts.py                                     exact issue 329 prompt and formatter
  src/
    step1_setup/
      __init__.py
      main.py                                      call the issue 326 setup runner with FEW_SHOT_VARIANT
    step2_inference/
      __init__.py
      main.py                                      call the issue 326 inference runner with the few-shot formatter
    step3_analysis/
      __init__.py
      main.py                                      call the issue 326 analysis runner with FEW_SHOT_VARIANT
```

`experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py` stays unchanged because it already renders the shared model and dataset tables. The existing zero-shot documentation and S3 artifacts also stay unchanged. The planned issue 332 code can import `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT` from the path it already expects.

### S3

```text
s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/
  inputs/
    study_2_five_labeler/
      records.jsonl                                byte copy of issue 326 input
      manifest.json                                few-shot key, shared digest and counts
  runs/
    RUN_ID/
      amazon_nova_micro/
        predictions/batch-000000.jsonl ...
        failures/batch-000000.jsonl ...
        manifests/manifest-000000.json ...
      qwen3_32b/
      openai_gpt_5_6_terra/
      claude_sonnet_5_5/
  analysis/
    RUN_ID/
      label_counts.csv
      split_remove_vote_counts.csv
      model_metrics.csv
      results_fragment.md
      analysis_manifest.json
```

## Schema and key interfaces

| Model or interface | Lives in | Status and role |
| --- | --- | --- |
| `Study2InferenceVariant` | `experiments/zero_shot_llm_inference_2026_09_30/shared/config.py` | New immutable dataclass that holds the experiment name, S3 bucket and root, input keys, four artifact schema versions, prompt name, prompt SHA-256, and metric exclusion IDs. It stays in memory. |
| `PromptFormatter` | `experiments/zero_shot_llm_inference_2026_09_30/shared/llm.py` | New callable type from `(post_1_text, post_2_text)` to the rendered user prompt. It stays in memory. |
| `Study2InputRecord` and `InputManifest` | Issue 326 `shared/schemas.py` | Reused without field changes. The few-shot input manifest stores the copied records key and the issue 326 records digest. |
| `RemovePrediction`, `TokenUsage`, `PredictionRecord`, and `FailureRecord` | Issue 326 `shared/schemas.py` | Reused. Stored prediction and failure rows use the active variant's schema versions. |
| `ModelRunManifest` | Issue 326 `shared/schemas.py` | Extended with stored `experiment_name`, `prompt_name`, and `prompt_sha256` fields. Older zero-shot manifests load with zero-shot defaults. |
| `AnalysisManifest` | Issue 326 `src/step3_analysis/analyze.py` | Extended with the same stored prompt identity and the tuple of demonstration post IDs excluded from primary metrics. |

The reusable entry points will have these signatures:

```python
run_setup(variant: Study2InferenceVariant) -> PreparedInputSummary

copy_prepared_input(
    source: Study2InferenceVariant,
    target: Study2InferenceVariant,
) -> PreparedInputSummary

run_inference_cli(
    variant: Study2InferenceVariant,
    prompt_formatter: PromptFormatter,
) -> None

run_analysis_cli(variant: Study2InferenceVariant) -> None
```

## Steps

### Step 1: Parameterize the completed issue 326 runners

Add `Study2InferenceVariant`, pass it through the existing setup, storage, inference, and analysis boundaries, and pass a prompt formatter into `label_record`. Keep the zero-shot constants and entry points as compatibility wrappers around `ZERO_SHOT_VARIANT`.

### Step 2: Add the few-shot prompt and thin entry points

Create the exact issue 329 prompt and formatter, define `FEW_SHOT_VARIANT`, and add one `main.py` for setup, inference, and analysis. Each `main.py` will call the corresponding reusable issue 326 runner and will not contain experiment logic.

### Step 3: Prepare an identical input package

Read the issue 326 input manifest and records, verify their digest and counts, and write the records under the few-shot prefix without changing a byte. Write a few-shot input manifest that points to the copied records.

### Step 4: Run the four model folders

Start one resumable process per model, using the few-shot formatter and the existing Bedrock response contract. Each process will write only within its model folder under the few-shot run ID.

### Step 5: Analyze and report the run

Reuse the issue 326 descriptive statistics, metric calculations, and Markdown renderer. Apply the confirmed demonstration-overlap policy, store the prompt identity and excluded IDs in the analysis manifest, and write the final tables to `RESULTS.md`.

## Expected results

The completed issue 326 input measured 13,992 five-labeler pairs, including 4,051 unanimous pairs and 9,941 split pairs. A complete few-shot run will therefore store 55,968 valid predictions across four model folders, with no unresolved failures.

The standard analysis will produce six human label rows, four split-vote rows, and twelve model metric rows. Under confirmed decision 2, the model rows will use 13,987 all rows, 4,046 unanimous rows, and 9,941 split rows. The analysis will write five artifacts under the few-shot analysis prefix, matching issue 326's artifact count.

Runtime, input tokens, output tokens, and cost are not estimated from the zero-shot run because the ten demonstrations make the few-shot prompt much longer. The implementation will measure those values per model during bounded smoke runs before the full 55,968-call run and will record the measured totals in `RESULTS.md`.

## Confirmed decisions

1. **Confirmed: Treat the zero-shot experiment as issue 329's reuse source.** Import from `experiments/zero_shot_llm_inference_2026_09_30/` and keep the few-shot package thin.
2. **Confirmed: Exclude five normalized exact demonstration matches from model metrics.** Predict all 13,992 rows, use 13,987 rows for the all-dataset model metrics, and keep human label counts over every row.
3. **Confirmed: Copy the prepared input into the few-shot S3 prefix.** Copy `records.jsonl` byte for byte and write a new manifest with the same digest.
4. **Confirmed: Do not add unit tests.** The implementation will not create unit-test files for this experiment.
