# Step 2: Smoke 10 users, write the cost table, and print the experiment 2 prompt

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/shared/run.py` `main` with `--smoke`, `--estimate-cost`, and `--print-experiment-2-prompt`
- **Task:** Label the first 10 cohort users (or the full cohort if smaller) on all four models using the experiment 1 prompt. Write smoke objects under each model's `smoke/` prefix. Scale token estimates to experiments 2 to 4. Write `COST_ESTIMATE.md`. Print the experiment 2 template plus one filled example. Stop. Do not write `final.parquet`. Do not start full labeling.
- **Out of scope:** experiments 2 to 4 full runs, experiment 5, `RESULTS.md`, `CHANGELOG.md`, editing product engines

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/plan.md` | Cost table shape, rates, 0.5× / 2× bounds |
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/steps/step1.md` | Cohort, prompts, runners |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/run.py` | `--smoke` path, smoke prefix, no copy into `final.parquet` |
| `/workspace/data_platform/generate_features/campaign_cost_report.py` | `BatchPricing.cost_usd`, OpenAI Batch and Nova rates |
| `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/write_cost_estimate.py` | `CEILING_MULTIPLIER` is 2 |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `FeaturePaths.from_root_uri` for smoke roots |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/openai_runner.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/bedrock_runner.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/cost.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md` (new, live numbers)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment2/SETUP.md` (add one filled example after the template)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/SETUP.md` (record smoke user count and smoke URIs)

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/scripts/export_study_results.py`
- `/workspace/lib/constants.py`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- Cohort S3 objects from Step 1 (do not overwrite)
- Any `final.parquet` key

## Smoke contract

Smoke users are the first 10 rows of `cohort_users.parquet` after sorting by `source_file_epoch_ms` then `prolific_id`. If `user_count` is less than 10, smoke every user.

Prompt is experiment 1 only. All four models must run:

1. `openai` through `build_openai_engine`
2. `bedrock_micro_nova` through `label_tasks_collecting_failures` with `us.amazon.nova-micro-v1:0`
3. `bedrock_qwen` through `label_tasks_collecting_failures` with `qwen.qwen3-32b-v1:0`
4. `bedrock_claude` through `label_tasks_collecting_failures` with `us.anthropic.claude-sonnet-4-6`

Bedrock `max_tokens` is 256. Do not send content-filter failures to OpenAI. Record those ids in the smoke `errors.jsonl`.

Smoke root URI pattern:

`s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/{model}/smoke/`

`--smoke` prints, per model:

```text
model=
labeled=
failed=
input_tokens=
output_tokens=
```

## Cost contract

`cost.py` loads smoke token counts per request. Median input and output tokens are the medians across the 10 (or fewer) successful smoke requests for that model. Experiments 2 to 4 estimated input tokens equal that median times `user_count` times (`mean_chars(experiment_n) / mean_chars(experiment_1)`), using rendered prompts on the full cohort with no extra model call. Estimated output tokens equal smoke-median output tokens times `user_count`. Median USD uses the pinned rates in the plan. Low is 0.5 times median. High is 2 times median. Experiment 5 is 0 tokens and 0 USD.

Write `experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md` with this shape:

```markdown
## Experiment 1

Estimated cost:

| model | estimated tokens in | estimated tokens out | median estimated cost | low/high estimated cost |
| --- | --- | --- | --- | --- |
| openai | | | | |
| bedrock_micro_nova | | | | |
| bedrock_qwen | | | | |
| bedrock_claude | | | | |

## Experiment 2

...

## Experiment 3

## Experiment 4

## Experiment 5

Estimated cost: 0 (analysis only)

## Total across experiments
```

`--estimate-cost` must refuse to run if any of the four smokes is missing, and it must refuse to call a model.

## Experiment 2 prompt dump

`--print-experiment-2-prompt` prints `STUDY_SYSTEM_PROMPT`, then the unfilled template from Step 1, then one filled example for the first cohort user. Append that filled example to `experiment2/SETUP.md`. Do not call a model.

## Must pass

- Four smoke prefixes each have 10 labels, or `user_count` labels if smaller, unless a content filter removed some rows. Print labeled and failed counts.
- No `final.parquet` exists under any experiment prefix.
- `COST_ESTIMATE.md` has the column set from the issue and a total section.
- Experiment 2 filled prompt is visible in stdout and in `experiment2/SETUP.md`.
- Pytest from Step 1 still exits 0.

## Must fail

- `--smoke` writing into `final.parquet`
- `--estimate-cost` before all four smokes exist
- `--smoke` calling `build_bedrock_engine` for Qwen or Claude
- Full-cohort labeling flags running inside `--smoke`

## Gate

Stop at the end of this step. Do not start Step 3 until the user has approved, in writing, both the cost table and the experiment 2 prompt template.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto for the smoke code, then stop for approval.

Phase 1 names `--smoke` as the caller.

Phase 2 to 5 implement `openai_runner.label_tasks`, `bedrock_runner.label_tasks`, smoke I/O, `cost.py`, and the three CLI flags. One commit per unit of work.

Phase 6 is complete when smoke, cost, and the prompt dump have run once live, and the process has not labeled the full cohort.
