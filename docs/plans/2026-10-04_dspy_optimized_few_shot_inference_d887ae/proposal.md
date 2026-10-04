# Proposal: Run the DSPy optimized few-shot prompt on Nova Micro and Qwen 3 32B

Scope: [issue 351](https://github.com/METResearchGroup/mirrorView-task/issues/351). The proposal covers the two-model Study 2 inference run, its S3 artifacts, and its analysis. It reuses the experiment built for [issue 329](https://github.com/METResearchGroup/mirrorView-task/issues/329) in [PR 346](https://github.com/METResearchGroup/mirrorView-task/pull/346), following the design approved in [PR 344](https://github.com/METResearchGroup/mirrorView-task/pull/344). Prompt optimization and candidate selection remain in [PR 339](https://github.com/METResearchGroup/mirrorView-task/pull/339).

## Overview

The new experiment will run the exact issue 351 prompt against the same 13,992 Study 2 pairs used by the completed few-shot experiment. It will run only Amazon Nova Micro and Qwen 3 32B. The implementation will reuse the existing setup, inference, resume, storage, and analysis code, while the new experiment package will contain one configuration record and three thin command entry points.

The run will store 27,984 predictions, one for each pair and model. `RESULTS.md` will report the human label distributions, the split-vote distribution, and F1, accuracy, recall, and precision for the all, unanimous, and split datasets.

## Cross-cutting concerns

### Reuse boundary

The existing `Study2InferenceVariant`, `PromptFormatter`, and three shared runners already separate experiment identity from the inference and analysis logic. The new experiment will import those interfaces from `experiments/zero_shot_llm_inference_2026_09_30/`. Existing zero-shot and baseline few-shot commands will keep their current behavior.

The root `shared/` package will never import from `experiments/`. The issue 351 prompt belongs in `shared/models/llm/prompt.py` because the issue requires that path and the prompt is the output of a separate optimization experiment. The new experiment will import the prompt and its formatter from the root package.

| Existing code | Symbols reused by the new experiment |
| --- | --- |
| `shared/models/llm/prompt.py` | New `OPTIMIZED_STUDY_PROMPT_TEMPLATE` and `format_optimized_study_prompt` |
| `experiments/zero_shot_llm_inference_2026_09_30/shared/config.py` | `Study2InferenceVariant`, extended with the model folders allowed for a variant |
| `experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py` | `MODEL_REGISTRY`, `get_model_definition_by_folder` |
| `experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py` | Input, prediction, failure, token usage, and run manifest models, unchanged |
| `experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py` | Immutable S3 writes, input loading, run key builders, and artifact loading |
| `experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/prepare.py` | `copy_prepared_input` and prepared input validation |
| `experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py` | `run_inference_cli`, ordered concurrent batches, resume checks, and manifest writes |
| `experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py` | Input validation, descriptive counts, model metrics, and analysis artifact writes |
| `experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py` | `render_results_fragment`, unchanged |

### Prompt identity

`OPTIMIZED_STUDY_PROMPT_TEMPLATE` will preserve the issue 351 text, example order, labels, placeholders, line breaks, and final `keep or remove` instruction. The exact string has SHA-256 `6ebcd9bbb16ff39dbeba93fe832a601a589ce1d8233645aad5030b105df9af15`. Its instruction through the two binary decision bullets matches the selected prompt stored by PR 339 at `s3://mirrorview-experimental-artifacts/experiments/dspy_gepa_balanced_labels_2026_10_02/runs/study2-gepa-balanced-2026-10-02-pilot/selection/optimized_prompt.txt`. Issue 351 supplies the complete inference template with the ten demonstrations, post placeholders, and final response instruction.

The variant will store the prompt name and digest in every model-run and analysis manifest. Reusing a run ID with different prompt bytes will fail the existing identity checks.

### Models and analysis

`MODEL_REGISTRY` will remain the repository's four-model registry. Add an ordered `model_folders` tuple to `Study2InferenceVariant`. The zero-shot and baseline few-shot variants will list all four current folders, while the issue 351 variant will list only `amazon_nova_micro` and `qwen3_32b`.

The inference command will reject a registry model that the active variant does not allow. Analysis will load, validate, order, and render only the models listed by the active variant. The variant and analysis manifest will therefore agree on the two model runs, and the analysis code will no longer require four completed runs or twelve metric rows.

### Demonstration overlap

The issue 351 prompt uses the same ten demonstrations as the baseline few-shot prompt. Five demonstrations have normalized exact matches in the prepared input, all in the unanimous partition. The new variant will reuse the five approved metric exclusion post IDs from `FEW_SHOT_VARIANT`.

Inference will still predict all 13,992 rows. Model metrics will use 13,987 all rows, 4,046 unanimous rows, and 9,941 split rows. Human label and split-vote tables will continue to describe all input rows.

### Data and S3 isolation

Setup will use `copy_prepared_input` to copy the completed baseline few-shot `records.jsonl` bytes into the new S3 prefix. The records digest, row counts, first post ID, and last post ID must match the source manifest. Setup will not query the registered datasets again.

All new generated artifacts will live under `s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/`. Existing zero-shot, baseline few-shot, and DSPy optimization objects will remain unchanged.

## File structure

### Repository

```text
docs/plans/2026-10-04_dspy_optimized_few_shot_inference_d887ae/
  proposal.md                                      this proposal

shared/models/llm/
  __init__.py                                      package marker
  prompt.py                                        exact issue 351 prompt and formatter

experiments/zero_shot_llm_inference_2026_09_30/
  shared/
    config.py                                      add ordered model_folders to Study2InferenceVariant
  src/
    step2_inference/run.py                         enforce the active variant's model folders
    step3_analysis/analyze.py                      load and analyze the active variant's model folders
  tests/
    test_model_selection.py                        model-set configuration, inference, and analysis regressions

experiments/few_shot_llm_inference_2026_09_30/
  shared/config.py                                 list the existing four model folders explicitly

experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/
  README.md                                        link to SETUP.md and RESULTS.md
  SETUP.md                                         required input data and S3 artifact locations
  RESULTS.md                                       generated two-model result tables and run identity
  shared/
    __init__.py
    config.py                                      OPTIMIZED_FEW_SHOT_VARIANT
  tests/
    test_prompt_and_config.py                      exact prompt, formatter, and variant contract
  src/
    step1_setup/
      __init__.py
      main.py                                      copy the baseline few-shot prepared input
    step2_inference/
      __init__.py
      main.py                                      call the shared runner with the optimized formatter
    step3_analysis/
      __init__.py
      main.py                                      call the shared analysis runner
```

The Pydantic models in `experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`, the storage helpers, and the result renderer stay unchanged.

### S3

```text
s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/
  inputs/
    study_2_five_labeler/
      records.jsonl                                byte copy of baseline few-shot input
      manifest.json                                new key, shared digest and counts
  runs/
    RUN_ID/
      amazon_nova_micro/
        predictions/batch-000000.jsonl ...
        failures/batch-000000.jsonl ...
        manifests/manifest-000000.json ...
      qwen3_32b/
        predictions/batch-000000.jsonl ...
        failures/batch-000000.jsonl ...
        manifests/manifest-000000.json ...
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
| `Study2InferenceVariant` | `experiments/zero_shot_llm_inference_2026_09_30/shared/config.py` | Extended with `model_folders: tuple[str, ...]`. It validates that the tuple is nonempty and has no duplicates. It stays in memory. |
| `PromptFormatter` | `experiments/zero_shot_llm_inference_2026_09_30/shared/llm.py` | Reused callable from two post strings to one rendered prompt. It stays in memory. |
| `OPTIMIZED_STUDY_PROMPT_TEMPLATE` | `shared/models/llm/prompt.py` | New exact issue 351 prompt string. It stays in the repository and is rendered in memory. |
| `Study2InputRecord` and `InputManifest` | Existing shared schemas | Reused without field changes. The new input manifest stores the copied records key and the existing records digest. |
| `PredictionRecord`, `FailureRecord`, and `ModelRunManifest` | Existing shared schemas | Reused without field changes. Stored artifacts carry the new schema versions, experiment name, prompt name, and prompt digest. |
| `AnalysisManifest` | Existing shared analysis module | Reused without field changes. Its existing `model_runs` tuple records the two completed model manifests. |

The changed and reused interfaces will have these shapes:

```python
@dataclass(frozen=True)
class Study2InferenceVariant:
    # Existing fields stay unchanged.
    model_folders: tuple[str, ...]


def format_optimized_study_prompt(post_1_text: str, post_2_text: str) -> str: ...
```

## Steps

### Step 1: Make the model set part of the experiment variant

Add the ordered model folders to `Study2InferenceVariant`. Update inference and analysis to resolve their model definitions from that tuple, while keeping the existing four-model variants unchanged.

### Step 2: Add the optimized prompt and experiment package

Create the exact issue 351 prompt and formatter under `shared/models/llm/`. Define the two-model optimized variant and add thin setup, inference, and analysis entry points that call the existing runners.

### Step 3: Prepare an identical input package

Read and verify the completed baseline few-shot input package. Copy its records bytes into the optimized experiment prefix and write a manifest that points to the new key with the same digest and counts.

### Step 4: Run the two model folders

Run one resumable process for Amazon Nova Micro and one for Qwen 3 32B. Each process will write only within its model folder under the new experiment prefix.

### Step 5: Analyze and report the run

Load the two complete model folders and reuse the existing descriptive statistics, metric calculations, and Markdown renderer. Apply the five demonstration exclusions to model metrics, write the analysis bundle to S3, and record measured runtime and token use in `RESULTS.md`.

## Expected results

The prepared input contains a measured 13,992 five-labeler pairs: 4,051 unanimous and 9,941 split. A complete two-model run will store 27,984 valid predictions with no unresolved failures.

The analysis will produce six human label rows, four split-vote rows, and six model metric rows. Model metrics will use 13,987 all rows, 4,046 unanimous rows, and 9,941 split rows because they exclude the same five prompt demonstrations as the completed baseline few-shot run. The analysis will write five artifacts under the optimized experiment prefix.

Runtime, input tokens, output tokens, and cost will be measured during the new run and recorded per model in `RESULTS.md`. The completed baseline few-shot run measured 959.86 seconds for Nova Micro and 620.21 seconds for Qwen 3 32B, but those values are reference measurements, not estimates for the changed prompt.

## Confirmed decisions

1. **Confirmed: Use `experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/` and the matching S3 prefix.** The experiment name identifies both the prompt source and the new run.
2. **Confirmed: Store the allowed model folders on `Study2InferenceVariant`.** The variant will hold the model choice with its paths, schema versions, and prompt identity.
3. **Confirmed: Reuse the five baseline demonstration exclusions for model metrics.** The ten demonstrations are unchanged, so the same five normalized exact matches will not be both prompt examples and scored rows.
4. **Confirmed: Copy the prepared input into the new S3 prefix.** The copy preserves the isolation and byte identity pattern from PR 344.
