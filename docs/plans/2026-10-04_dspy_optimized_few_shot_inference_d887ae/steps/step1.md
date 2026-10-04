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

## Smoke contract

Use one inline Python smoke command after implementation. It must confirm that variant construction rejects empty and duplicate model tuples, both existing variants retain the four-folder order, inference accepts `amazon_nova_micro` for a two-model variant, and inference rejects `openai_gpt_5_6_terra` for that variant before AWS access. Step 5 provides the end-to-end analysis smoke check against two completed model folders.

## Implementation order

1. Add the configuration field and its validation, then update the two existing variant values.
2. Pass the active variant through inference validation and enforce the selected model set before AWS access.
3. Replace analysis loops and fixed model counts with the active variant order.
4. Update fixed four-model wording in changed docstrings and CLI summaries without changing behavior outside the selected model set.

Keep each numbered implementation task in its own commit. Suggested commit messages are `refactor: add model sets to Study 2 variants`, `feat: enforce inference model selection`, and `feat: analyze configured Study 2 models`.

## Verification

Run from `/Users/mark/.codex/worktrees/39d9/mirrorview-wt`:

```bash
PYTHONPATH=. uv run python - <<'PY'
from dataclasses import replace

from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run import validate_inference_arguments

all_models = (
    "amazon_nova_micro",
    "qwen3_32b",
    "openai_gpt_5_6_terra",
    "claude_sonnet_5_5",
)
assert ZERO_SHOT_VARIANT.model_folders == all_models
assert FEW_SHOT_VARIANT.model_folders == all_models
for invalid in ((), ("amazon_nova_micro", "amazon_nova_micro")):
    try:
        replace(ZERO_SHOT_VARIANT, model_folders=invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(f"accepted invalid model folders: {invalid}")
two_models = replace(
    ZERO_SHOT_VARIANT,
    model_folders=("amazon_nova_micro", "qwen3_32b"),
)
allowed = validate_inference_arguments(
    "model-selection-smoke",
    "amazon_nova_micro",
    1,
    1,
    1,
    256,
    two_models,
)
assert allowed.folder_name == "amazon_nova_micro"
try:
    validate_inference_arguments(
        "model-selection-smoke",
        "openai_gpt_5_6_terra",
        1,
        1,
        1,
        256,
        two_models,
    )
except ValueError:
    pass
else:
    raise AssertionError("accepted a model outside the active variant")
print("model-selection-smoke-ok existing_models=4 selected_models=2")
PY
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help >/dev/null
PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step2_inference.main --help >/dev/null
git diff --check
```

The smoke command must print exactly `model-selection-smoke-ok existing_models=4 selected_models=2`. Both help commands must exit 0 without an AWS request. `git diff --check` must print nothing.

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
