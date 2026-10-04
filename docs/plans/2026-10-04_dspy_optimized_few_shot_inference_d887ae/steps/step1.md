# Step 1: Make the model set part of each experiment

## Proposal sections implemented

- Cross-cutting concerns, Models and analysis
- File structure, Repository
- Schema and key interfaces
- Step 1, Make the model set part of the experiment variant

## Scope

- Caller: `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py` `run_inference_cli`
- Task: Put the ordered model folders on each Study 2 experiment variant, enforce the list during inference, and make analysis load and report the same models in the same order.
- Out of scope: the issue 351 prompt, the new experiment package, S3 writes, Bedrock requests, and result publication.

## Files to inspect

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/docs/plans/2026-10-04_dspy_optimized_few_shot_inference_d887ae/proposal.md`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/config.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/config.py`

## Files allowed to change

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/config.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/config.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/tests/test_model_selection.py` (new)

## Files forbidden to change

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`
- Every prompt file
- Every file under `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/data_platform/`
- S3 objects and Bedrock

## Contract

Add `model_folders: tuple[str, ...]` to `Study2InferenceVariant`. Variant construction must reject an empty tuple, duplicate folder names, empty names, and names with leading or trailing whitespace. Registry lookup remains the authority for whether a nonempty folder name is known.

Set both existing variants to this ordered tuple:

```python
(
    "amazon_nova_micro",
    "qwen3_32b",
    "openai_gpt_5_6_terra",
    "claude_sonnet_5_5",
)
```

Pass the active variant into inference argument validation. A model must exist in `MODEL_REGISTRY` and in the active variant. Keep the zero-shot variant as the default only where an existing public call needs backward compatibility.

Analysis must resolve model definitions from `variant.model_folders`. Use that ordered set when loading completed runs, validating the expected run count, building metric rows, and printing the completion line. Keep `render.py` unchanged because its existing registry order can sort any subset of registered models.

## Test design

Write the scenarios as given, when, and then notes before writing the tests:

1. Given an empty or duplicate model tuple, when a variant is constructed, then construction raises `ValueError`.
2. Given the existing zero-shot and few-shot variants, when their model folders are read, then both equal the current four-folder order.
3. Given a two-model variant, when inference validates `amazon_nova_micro`, then validation returns the registry model.
4. Given a two-model variant, when inference validates `openai_gpt_5_6_terra`, then validation raises `ValueError` before an AWS client is constructed.
5. Given model runs in the two-model variant order, when model metrics are built, then analysis returns six rows in dataset and variant model order.
6. Given two loaded model runs for a two-model variant, when input validation runs, then it accepts two runs and rejects a missing or extra folder.

The tests must use public functions where available. A test may use the frozen analysis data classes as fixtures, but it must not seed private storage or make an AWS request.

## Implementation order

1. Add the configuration field and its validation, then update the two existing variant values.
2. Write `test_model_selection.py` and confirm that the inference and analysis scenarios fail for the missing behavior.
3. Pass the active variant through inference validation and make the two inference tests pass.
4. Replace analysis loops and fixed model counts with the active variant order, then make the analysis tests pass.
5. Update fixed four-model wording in changed docstrings and CLI summaries without changing behavior outside the selected model set.

Keep each numbered implementation task in its own commit. Suggested commit messages are `refactor: add model sets to Study 2 variants`, `test: define Study 2 model selection`, `feat: enforce inference model selection`, and `feat: analyze configured Study 2 models`.

## Verification

Run from `/Users/mark/.codex/worktrees/39d9/mirrorview-wt`:

```bash
PYTHONPATH=. uv run pytest -q experiments/zero_shot_llm_inference_2026_09_30/tests/test_model_selection.py
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help >/dev/null
PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --help >/dev/null
git diff --check
```

The test command must report six passed tests. Both help commands must exit 0 without an AWS request. `git diff --check` must print nothing.

## Must pass

- Both existing variants retain all four registered models in their current order.
- Inference rejects a registered model that is not enabled for the active variant.
- Analysis loads, validates, calculates, and reports only the active variant's ordered model set.
- The unchanged renderer can render metric rows for a model subset.

## Must fail

- Empty, duplicate, blank, or whitespace-padded model folder entries.
- An unknown registry folder.
- A registered model outside the active variant.
- Missing, extra, duplicated, or reordered model runs during analysis validation.
