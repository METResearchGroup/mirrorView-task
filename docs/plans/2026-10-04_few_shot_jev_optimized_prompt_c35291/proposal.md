# Proposal: Few-shot Jev inference with the balanced GEPA instruction

Scope: [issue 352](https://github.com/METResearchGroup/mirrorView-task/issues/352). The proposal covers the prompt constant, the new Jev experiment, the S3 artifacts, and the analysis. The runners, request shape, and metric exclusions come from [issue 345](https://github.com/METResearchGroup/mirrorView-task/issues/345) and [PR 348](https://github.com/METResearchGroup/mirrorView-task/pull/348). The instruction text comes from the balanced GEPA candidate in [PR 339](https://github.com/METResearchGroup/mirrorView-task/pull/339).

## Overview

You score the same 13,992 Study 2 pairs that have five labelers, with Jev 1.13.0 and the instruction selected by the balanced GEPA run. Each request puts the ten labeled examples in the Jev instructions and the current pair in classifier state. The request then asks one removal question. The run writes one remove probability and one label for each pair, and the report gives F1, accuracy, recall, and precision for all pairs, the unanimous pairs, and the split pairs.

You add one prompt constant under `shared/models/llm/` and one small experiment package. The completed zero-shot and few-shot Jev runners stay in place.

## Cross-cutting concerns

### Reuse

Root `shared/` never imports from `experiments/`. Issue 352 puts the prompt string in `shared/models/llm/prompt.py`, so the constant lives there. The compiler stays in the new experiment, because it depends on the removal question for this task.

| Existing code | What this experiment uses |
| --- | --- |
| `shared/models/jev/scorer.py` | `JevScorer`, `build_jev_scorer` |
| `shared/models/jev/constants.py` | `JEV_MODEL_ID`, `JEV_USD_PER_MILLION_INPUT` of `0.042` |
| `experiments/zero_shot_jev_inference_2026_10_01/shared/config.py` | `JevInferenceVariant`, `ZERO_SHOT_VARIANT` |
| `experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py` | `REMOVE_QUESTION`, `build_remove_request` |
| `experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/prepare.py` | `copy_prepared_input` |
| `experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/run.py` | `run_inference`, `run_inference_cli` |
| `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py` | `run_analysis`, `run_analysis_cli` |
| `experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py` | `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT`, for the ten examples only |
| `experiments/few_shot_jev_inference_2026_10_01/shared/config.py` | the same five metric exclusion post IDs |

`build_few_shot_remove_instructions` stays in the completed few-shot experiment. It requires the source prompt to end with `Allow Or Remove?`, and the issue 352 template ends with `keep or remove`. The new compiler does the same replacement with that ending. `shared/models/jev/`, the zero-shot package, and the completed few-shot package stay as they are.

### Prompt bytes

`OPTIMIZED_STUDY_PROMPT_TEMPLATE` follows the issue 352 paste. Decision 1 chooses whether to restore one space that GitHub dropped. The constant has no final newline, matching `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT`. The issue's Python literal has a newline only because the closing quotes are on the next line, and the compiler deletes that ending before the request, so Jev does not receive it.

Build the recommended string as follows.

1. Read the fenced text under "Optimized instruction" in `experiments/dspy_gepa_balanced_labels_2026_10_02/RESULTS.md`. The text is candidate 4 from run `study2-gepa-balanced-2026-10-02-pilot`. Drop the newline that the fence adds after `Allow Or Remove?`.
2. Remove the suffix `\n\nReturn only the decision.\n\nAllow Or Remove?`.
3. Append `\n\n` and the example block from `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT`, starting at `Here are examples of pairs of posts that human annotators remove:` and stopping before `Allow Or Remove?`. The block includes the space at the end of the first line of keep example 2, and the line that contains only one space before remove example 3.
4. Append `Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\nReturn only the decision.\n\nkeep or remove`, with no final newline.

The natural-prevalence instruction in `experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md` is a different paragraph. The issue 352 paste matches the balanced instruction, so the experiment uses the balanced text.

The recommended template is 6,290 UTF-8 bytes. Its SHA-256 is `178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f`. Both numbers were measured in this session by assembling the two files above and hashing the result. The issue paste itself is 6,289 bytes with SHA-256 `6ebcd9bbb16ff39dbeba93fe832a601a589ce1d8233645aad5030b105df9af15`, because GitHub dropped the line that contains only a space and the Python literal includes a final newline.

`build_optimized_remove_instructions` requires one copy of `Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\n`, requires the string to end with `keep or remove`, deletes that pair block, and replaces the ending with `REMOVE_QUESTION`. Once that replacement is applied, the compiled instructions are 6,339 UTF-8 bytes with SHA-256 `1929e49a31c20488ff25a134d53d9e267d7214ca723575042ef6d7a19f23cb5e`. The byte count and digest were measured on the recommended template. The run manifest stores both digests in the existing `prompt_sha256` and `instructions_sha256` fields.

### Rows and metrics

The input is the zero-shot Jev `records.jsonl`, SHA-256 `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. The file has 13,992 rows, with 4,051 unanimous rows and 9,941 split rows. The experiment copies those bytes into its own prefix.

Model metrics omit the same five unanimous demonstration post IDs that PR 348 omitted:

- `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
- `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
- `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
- `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
- `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

Human label counts and token totals still use all 13,992 predictions. Decision 4 covers whether the 405 balanced GEPA posts are also left out of the metrics.

### Model and request limits

The model is Jev 1.13.0 through `TypeSafeClassifier`. `p_remove` is the yes probability on question ID `is_remove`, and `is_remove` is true when `p_remove >= 0.5`. The run uses batches of 500, 8 workers, at most 1,000 request starts per minute, and three retries for transient errors. The limits match the completed few-shot run. Predictions, failures, and manifests stay immutable, and a rerun resumes from the stored predictions.

The production run ID is `study2-jev-optimized-prompt-2026-10-04`. The prompt name stored on the variant is `optimized_study_prompt`. The manifest schema version is `study2-optimized-prompt-jev-run-v1`.

## File structure

### Repository

```text
docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/
  proposal.md                                      this proposal

shared/models/llm/
  __init__.py                                      re-exports the prompt constant
  prompt.py                                        OPTIMIZED_STUDY_PROMPT_TEMPLATE

experiments/few_shot_jev_optimized_prompt_2026_10_04/
  README.md                                        links to SETUP.md and RESULTS.md
  SETUP.md                                         required input and artifact locations
  RESULTS.md                                       tables written after analysis
  __init__.py
  shared/
    __init__.py
    config.py                                      OPTIMIZED_VARIANT and the five exclusions
    jev.py                                         compiler and request adapter
  src/
    __init__.py
    step1_setup/
      __init__.py
      main.py                                      copy and check the prepared input
    step2_inference/
      __init__.py
      main.py                                      resumable Jev scoring
    step3_analysis/
      __init__.py
      main.py                                      analyze one complete run
```

`shared/models/__init__.py` stays a package docstring and does not import `llm`. `experiments/few_shot_jev_inference_2026_10_01/`, `experiments/zero_shot_jev_inference_2026_10_01/`, `experiments/dspy_gepa_balanced_labels_2026_10_02/`, and `shared/models/jev/` stay as they are.

### S3

```text
s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_optimized_prompt_2026_10_04/
  inputs/
    study_2_five_labeler/
      records.jsonl                                same bytes as the zero-shot Jev input
      manifest.json                                new key, same digest and counts
  runs/
    study2-jev-optimized-prompt-2026-10-04/
      jev_1_13_0/
        predictions/batch-000000.jsonl ...
        failures/batch-000000.jsonl ...
        manifests/manifest-000000.json ...
  analysis/
    study2-jev-optimized-prompt-2026-10-04/
      label_counts.csv
      split_remove_vote_counts.csv
      model_metrics.csv
      usage.csv
      results_fragment.md
      analysis_manifest.json
```

## Schema and key interfaces

| Model or interface | Lives in | Status and role |
| --- | --- | --- |
| `OPTIMIZED_STUDY_PROMPT_TEMPLATE` | `shared/models/llm/prompt.py` | New string constant. It is the source prompt described above. |
| `JevInferenceVariant` | `experiments/zero_shot_jev_inference_2026_10_01/shared/config.py` | Reused. `OPTIMIZED_VARIANT` sets the prefix, prompt name, both digests, and the five exclusion IDs. |
| `RemoveRequestBuilder` | `experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py` | Reused callable from `Study2InputRecord` to `ClassifierRequest`. |
| `Study2InputRecord`, `InputManifest`, `PredictionRecord`, `FailureRecord`, `JevRunManifest` | existing zero-shot and issue 326 schema modules | Reused with the current fields. |

The stored rows stay on the existing models. `JevResult` stays in memory, and `to_prediction_record` still writes the issue 326 prediction row.

```python
def build_optimized_remove_instructions(prompt: str) -> str: ...

def build_optimized_remove_request(record: Study2InputRecord) -> ClassifierRequest: ...
```

`build_optimized_remove_request` calls `build_remove_request` with the compiled instructions. The three entry points call `copy_prepared_input`, `run_inference_cli`, and `run_analysis_cli` with `OPTIMIZED_VARIANT`.

## Steps

### Step 1: Add the shared prompt constant

Assemble `OPTIMIZED_STUDY_PROMPT_TEMPLATE` with the rules in the prompt section, check the recommended SHA-256, and export it from `shared.models.llm`.

### Step 2: Add the experiment variant and compiler

Add `OPTIMIZED_VARIANT`, `build_optimized_remove_instructions`, and `build_optimized_remove_request`. Check that the compiled instructions match the recommended digest. Add the three entry points that pass the variant into the existing runners.

### Step 3: Copy the prepared input

Read the zero-shot Jev records and manifest, check the digest and counts, and write the same record bytes under the new prefix. `copy_prepared_input` writes a manifest whose records key is new and whose digest and counts match the source.

### Step 4: Score the pairs

Run a five-row smoke sample first, so the token, cost, and runtime estimates below can be replaced with measurements. The full run then scores all 13,992 pairs under `study2-jev-optimized-prompt-2026-10-04` and resumes from stored predictions after an interruption.

### Step 5: Analyze the run

Reuse the existing label counts, split-vote counts, classification metrics, usage totals, and Markdown renderer. Leave the five demonstration matches out of model metrics, and write the tables to `RESULTS.md` and to the six analysis objects.

## Expected results

The full run writes 13,992 predictions under `jev_1_13_0/` with no unresolved failures. Step 5 writes the same table shapes as PR 348. If decision 4 stays with the recommendation, model metrics use 13,987 all rows, 4,046 unanimous rows, and 9,941 split rows. Metric values cannot be estimated before the run.

Input tokens are estimated from the two completed Jev runs. Zero-shot used 10,162,373 input tokens with 1,501 compiled instruction bytes. Few-shot used 24,672,077 input tokens with 6,000 compiled instruction bytes. The difference is 3,225.1 input tokens per extra instruction byte across 13,992 requests, or about 0.230 tokens per byte per request. The recommended template compiles to 6,339 bytes, which is 339 bytes more than the few-shot instructions, so the estimate adds 1,093,307 input tokens.

| Quantity | Value | Source |
| --- | ---: | --- |
| Input tokens | 25,765,384 | Estimated from the byte difference above |
| Output tokens | 293,832 | Estimated. Both completed Jev runs recorded this exact count |
| Cost | $1.082146 | Estimated at $0.042 per million input tokens, from `JEV_USD_PER_MILLION_INPUT` |
| Runtime | about 810 seconds | Estimated from the measured few-shot runtime of 809.81 seconds, because that run was already near the cap of 1,000 request starts per minute |

The five-row smoke run replaces the estimates before the full run.

## Decisions to confirm

1. **Restore the line that contains only a space before remove example 3.** Recommendation: copy that line from `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT`, so the ten examples match the bytes used by issue 329, PR 348, and the GEPA demonstrations. The main alternative is the issue paste as GitHub stored it, which uses a normal blank line there. The GitHub paste is SHA-256 `6ebcd9bbb16ff39dbeba93fe832a601a589ce1d8233645aad5030b105df9af15`.
2. **Put the run in a new experiment prefix.** Recommendation: `experiments/few_shot_jev_optimized_prompt_2026_10_04/`, so the completed run `study2-jev-few-shot-2026-10-01` stays unchanged. The main alternative is a new run ID under the existing few-shot prefix.
3. **Keep the terminal line `keep or remove` and add a small compiler.** Recommendation: follow the issue 352 template, and leave `build_few_shot_remove_instructions` unchanged. The compiled Jev text is the same if the stored template instead ends with `Allow Or Remove?`, and in that case the experiment calls the existing compiler.
4. **Leave only the five demonstration rows out of model metrics.** Recommendation: follow PR 348, score all 13,992 pairs, and report metrics on 13,987, 4,046, and 9,941 rows. The unanimous number then includes the 405 posts in the balanced GEPA cohort at `s3://mirrorview-experimental-artifacts/experiments/dspy_gepa_balanced_labels_2026_10_02/`. The split rows were not used to choose the instruction. The main alternative is to also leave those 405 posts out of model metrics.
