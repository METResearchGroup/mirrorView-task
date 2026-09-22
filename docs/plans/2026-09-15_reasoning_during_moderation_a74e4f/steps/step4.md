# Step 4: Run experiment 2

## Scope

- **Caller:** `experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py` `main`
- **Task:** Repeat experiment 1 with `add_criteria=true`. Keep post ids, models, generation seeds, and Post 1 / Post 2 order matched to experiment 1. Store traces and write the same six-row summary shape. Do not rewrite the instruction text. Do not score accuracy.
- **Out of scope:** Changing `KEEP_REMOVE_FEATURES.md`, human times, bag-of-words, rewriting `README.md`, editing the website.

## Dependencies

Experiment 1 traces exist for both models. The Step 2 renderer already accepts `add_criteria`. Do not start until experiment 1 `--summarize` has written six rows.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/steps/step2.md` | Addendum slot and renderer flags |
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/steps/step3.md` | Trace columns, summary columns, resume, Jobs |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/prompt.py` | `KEEP_REMOVE_FEATURES_ADDENDUM` |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py` | Copy the run loop, not the prompt arm |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment1/summarize.py` | Reuse `summarize_tokens` |

## Files allowed to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment2/__init__.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_prompt_arm_match.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` (add the experiment 2 command only)

## Files forbidden to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/README.md`
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/prompt.py` except if Step 2 left `add_criteria` unwired, in which case fix it here and add a test
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/KEEP_REMOVE_FEATURES.md`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/prompt.py`
- `/workspace/webapp/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md`
- Experiment 1 trace objects on S3
- Objects under `s3://jspsych-mirror-view-2026-09-09/`

## Run contract

Call `render_prompt(..., add_criteria=True)`. `prompt_arm` is `study_plus_criteria`.

For each experiment 1 trace row, experiment 2 must use the same `post_id`, `model_id`, `post_1_role`, `post_2_role`, and `generation_seed`. Load those fields from the experiment 1 traces when present, and fall back to the cohort plus `generation_seed(post_id)` if a smoke-only environment has no full experiment 1 file.

Do not import `STUDY_PROMPT_TEMPLATE`. Do not copy the addendum into `experiment2/`.

Local paths:

```text
experiments/reasoning_during_moderation_2026_09_15/experiment2/outputs/traces_qwen.jsonl
experiments/reasoning_during_moderation_2026_09_15/experiment2/outputs/traces_deepseek.jsonl
experiments/reasoning_during_moderation_2026_09_15/experiment2/outputs/token_summary.csv
```

Matching S3 keys under `s3://mirrorview-experimental-artifacts/experiments/reasoning_during_moderation_2026_09_15/experiment2/`.

Summary columns are the same as experiment 1. Call `summarize_tokens` from `experiment1/summarize.py`. Do not copy the summarizer.

## Pytest files

### `tests/test_prompt_arm_match.py`

Class `TestPromptArmMatch`.

```text
given one cohort row and an experiment 1 trace with post_1_role mirror and seed 123
when experiment2 planned completion fields are built
then post_1_role is mirror
and generation_seed is 123
and add_criteria is true
and prompt_arm is study_plus_criteria

given render_prompt with add_criteria true versus false on the same posts
when both strings are built
then the criteria addendum is the only inserted block
and Post 1 text, Post 2 text, and Allow or Remove? match
```

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --model qwen
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --model deepseek
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --summarize
```

On a machine without a GPU, run the model commands as Hugging Face Jobs, one job per model, using `jobs.py` from Step 2.

Expected `--summarize` stdout includes `rows=6` and `prompt_arm=study_plus_criteria`.

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_prompt_arm_match.py -q
```

Expected: exit 0.

## Must pass

- Experiment 2 prompts contain `KEEP_REMOVE_FEATURES_ADDENDUM`.
- Pair order and generation seed match experiment 1 for every `post_id` and model.
- Summary has six rows and no accuracy columns.
- Experiment 1 traces on disk and in S3 are unchanged.

## Must fail

- A different Post 1 / Post 2 order from experiment 1.
- A different generation seed from experiment 1.
- Rewriting the website instruction text.
- Copying `KEEP_REMOVE_FEATURES_ADDENDUM` into a new string.
- Scoring keep or remove accuracy.
- Overwriting experiment 1 S3 keys.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `experiment2/run.py` `main` as the caller.

Phase 2 scaffolds `experiment2/run.py` so it calls `render_prompt`, the shared runner, and `summarize_tokens`.

Phase 3 locks `prompt_arm` and the matched-field helper.

Phase 4 writes `test_prompt_arm_match.py`.

Phase 5 implements the matched-field helper, then the run loop, then summarize.

Phase 6 is complete when the match tests are green and `--summarize` is wired.
