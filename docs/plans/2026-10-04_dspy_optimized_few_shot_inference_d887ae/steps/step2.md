# Step 2: Add the optimized prompt and experiment package

## Proposal sections implemented

- Cross-cutting concerns, Reuse boundary
- Cross-cutting concerns, Prompt identity
- Cross-cutting concerns, Demonstration overlap
- File structure, Repository
- Schema and key interfaces
- Step 2, Add the optimized prompt and experiment package

## Scope

- Caller: `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step2_inference/main.py` `main`
- Task: Add the exact issue 351 prompt and formatter, define the two-model experiment variant, and add thin setup, inference, and analysis entry points.
- Out of scope: live S3 writes, Bedrock requests, completed metrics, and final result values.

## Files to inspect

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/docs/plans/2026-10-04_dspy_optimized_few_shot_inference_d887ae/proposal.md`
- [Issue 351](https://github.com/METResearchGroup/mirrorView-task/issues/351)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/config.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step1_setup/main.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step2_inference/main.py`
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step3_analysis/main.py`

## Files allowed to change

- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/shared/models/llm/__init__.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/shared/models/llm/prompt.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/README.md` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/SETUP.md` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/RESULTS.md` (new placeholder)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/shared/__init__.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/shared/config.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step1_setup/__init__.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step1_setup/main.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step2_inference/__init__.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step2_inference/main.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step3_analysis/__init__.py` (new)
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/src/step3_analysis/main.py` (new)

## Files forbidden to change

- Existing zero-shot and baseline few-shot prompt files
- Existing Pydantic schemas, storage helpers, and the result renderer
- `/Users/mark/.codex/worktrees/39d9/mirrorview-wt/data_platform/`
- `pyproject.toml` and `uv.lock`
- Existing S3 objects

## Prompt contract

Copy `OPTIMIZED_STUDY_PROMPT_TEMPLATE` from issue 351 exactly, including all ten demonstrations, both placeholders, line breaks, and the final newline after `keep or remove`. Its UTF-8 SHA-256 must be `6ebcd9bbb16ff39dbeba93fe832a601a589ce1d8233645aad5030b105df9af15`.

`format_optimized_study_prompt(post_1_text, post_2_text)` must require exactly one `{post_1_text}` and one `{post_2_text}` placeholder. It substitutes only those placeholders and preserves inserted post text without normalization.

## Variant contract

Define `OPTIMIZED_FEW_SHOT_VARIANT` with these values:

| Field | Value |
| --- | --- |
| Experiment name | `study2-dspy-optimized-few-shot` |
| S3 bucket | `mirrorview-experimental-artifacts` |
| S3 root | `experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/` |
| Prediction schema | `study2-dspy-optimized-few-shot-prediction-v1` |
| Failure schema | `study2-dspy-optimized-few-shot-failure-v1` |
| Model-run schema | `study2-dspy-optimized-few-shot-model-run-v1` |
| Analysis schema | `study2-dspy-optimized-few-shot-analysis-v1` |
| Prompt name | `OPTIMIZED_STUDY_PROMPT_TEMPLATE` |
| Prompt digest | `6ebcd9bbb16ff39dbeba93fe832a601a589ce1d8233645aad5030b105df9af15` |
| Model folders | `amazon_nova_micro`, then `qwen3_32b` |

Copy the five metric exclusion post IDs from `FEW_SHOT_VARIANT` by value. Do not import the baseline variant into the root prompt package. The root `shared/` package must not import from `experiments/`.

## Entry-point contract

- Setup calls `copy_prepared_input(FEW_SHOT_VARIANT, OPTIMIZED_FEW_SHOT_VARIANT)`.
- Inference calls the shared runner with the optimized variant and formatter.
- Analysis calls the shared runner with the optimized variant.
- `README.md` contains only a title and links to `SETUP.md` and `RESULTS.md`.
- `SETUP.md` describes required data and S3 locations, without environment setup or commands.
- `RESULTS.md` contains a title and states that no completed run has been published yet. Step 5 replaces this placeholder.

## Smoke contract

The inline smoke check must confirm the exact prompt digest, one substitution for each sentinel, the ordered two-model set, the five unique exclusion IDs, and import-safe command modules with callable `main` functions. It must not construct AWS clients or access AWS.

## Implementation order

1. Create the package tree, empty documentation files, and thin caller stubs, then confirm that imports reach only stubbed behavior.
2. Add the exact prompt and formatter behavior.
3. Add the variant values and thin caller wiring.
4. Complete `README.md`, `SETUP.md`, and the temporary `RESULTS.md` without adding run results.

Keep the initial files, prompt behavior, and caller wiring in separate commits. Suggested commit messages are `chore: scaffold optimized few-shot experiment`, `feat: add optimized Study 2 prompt`, and `feat: add optimized few-shot callers`.

## Verification

Run from `/Users/mark/.codex/worktrees/39d9/mirrorview-wt`:

```bash
PYTHONPATH=. uv run python - <<'PY'
import hashlib

from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.shared.config import OPTIMIZED_FEW_SHOT_VARIANT
from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step1_setup.main import main as setup_main
from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main import main as inference_main
from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step3_analysis.main import main as analysis_main
from shared.models.llm.prompt import OPTIMIZED_STUDY_PROMPT_TEMPLATE, format_optimized_study_prompt

expected_digest = "6ebcd9bbb16ff39dbeba93fe832a601a589ce1d8233645aad5030b105df9af15"
assert hashlib.sha256(OPTIMIZED_STUDY_PROMPT_TEMPLATE.encode("utf-8")).hexdigest() == expected_digest
rendered = format_optimized_study_prompt("POST_ONE_SENTINEL", "POST_TWO_SENTINEL")
assert rendered.count("POST_ONE_SENTINEL") == 1
assert rendered.count("POST_TWO_SENTINEL") == 1
assert OPTIMIZED_FEW_SHOT_VARIANT.model_folders == ("amazon_nova_micro", "qwen3_32b")
exclusions = OPTIMIZED_FEW_SHOT_VARIANT.metric_exclusion_post_ids
assert len(exclusions) == 5
assert len(set(exclusions)) == 5
assert all(callable(entry_point) for entry_point in (setup_main, inference_main, analysis_main))
print("optimized-contract-smoke-ok models=2 exclusions=5")
PY
PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step2_inference.main --help >/dev/null
PYTHONPATH=. uv run python -m experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.src.step3_analysis.main --help >/dev/null
git diff --check
```

The smoke command must print `optimized-contract-smoke-ok models=2 exclusions=5`. The inference and analysis help commands must exit 0 without AWS access. The setup command has no arguments, so the smoke command verifies it by import instead of running it. `git diff --check` must print nothing.

## Must pass

- The prompt digest, placeholders, example order, labels, whitespace, and final newline match issue 351.
- The new variant enables only Nova Micro and Qwen 3 32B and uses the five confirmed exclusions.
- All three entry points are thin callers of the existing shared functions.
- Existing experiment imports and command help remain functional.

## Must fail

- Any prompt byte or placeholder-count change.
- Any model beyond the two confirmed folders.
- Any S3 key outside the optimized experiment root.
- Any import from an experiment package into `shared/models/llm/`.
