# Step 2: Smoke 10 users times 20 pairs and write the experiment 6 cost table

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --smoke` and `--estimate-cost`
- **Task:** Label the first 10 unique cohort users times 20 pairs on OpenAI, Nova Micro, and Qwen using the one-pair yes/no prompt. Write smoke objects under each model's experiment 6 `smoke/` prefix. Write `experiment6/COST_ESTIMATE.md` locally and on S3. Append one filled one-pair prompt to `experiment6/SETUP.md`. Stop. Do not write `final.parquet`. Do not start full labeling. Do not call Claude.
- **Out of scope:** full `--model`, `--score`, experiment 1 through 5 S3 objects, parent `COST_ESTIMATE.md`, `CHANGELOG.md`

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_experiment6_795df1/plan.md` | Cost path, rates, 200-call smoke |
| `/workspace/docs/plans/2026-09-12_ai_simulation_experiment6_795df1/steps/step1.md` | Pair ids, yes/no spec |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` | Frozen `smoke_command` (experiment 1, four models). Copy the part-loop pattern, do not reuse that function for experiment 6. |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/cost.py` | `TokenUsageRecord`, `median_tokens`, `MODEL_PRICING`, `put_new_mirrored` via `upload_cost_estimate` which currently writes the parent cost file |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/openai_runner.py` | `label_tasks_with_usage` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/bedrock_runner.py` | `label_tasks_with_usage` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md` | Column layout to copy. Do not overwrite this file. |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` (experiment 6 smoke and estimate-cost dispatch only)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/cost.py` (add an experiment 6 markdown builder and upload helper that writes `experiment6/COST_ESTIMATE.md`; do not change `COST_ESTIMATE_RELATIVE_PATH` or `upload_cost_estimate`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_cost_estimate.py` (experiment 6 table shape, three models, no Claude row)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/SETUP.md` (filled example)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/COST_ESTIMATE.md` (live numbers, local and S3)

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/scripts/export_study_results.py`
- `/workspace/lib/constants.py`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md` local and S3
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py`
- Cohort S3 objects
- Any experiment 1 through 5 `final.parquet` or smoke object
- Any experiment 6 `final.parquet` key

## Smoke contract

Smoke users are the first 10 unique `prolific_id` values from `select_smoke_users`. That is 200 `LabelTask` rows per model. `LabelTask.uri` is `pair_record_id(prolific_id, pair_index)`. `LabelTask.text` is `render_single_pair(trial)`. Spec is `pair_yes_no_spec`.

Models, in order:

1. `openai` through `build_openai_engine` / `label_tasks_with_usage`
2. `bedrock_micro_nova` through the existing Bedrock usage helper with `us.amazon.nova-micro-v1:0`
3. `bedrock_qwen` through the same helper with `qwen.qwen3-32b-v1:0`

Do not instantiate a Claude client. Bedrock `max_tokens` is 256. Content-filter failures go to smoke `errors.jsonl`, not to OpenAI.

Smoke root:

`s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/{model}/smoke/`

Call `FeaturePaths.from_root_uri` with root `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/{model}/` and feature `smoke`.

`--smoke` prints, per model:

```text
model=
labeled_pairs=
failed_pairs=
input_tokens=
output_tokens=
```

`--smoke` also appends one filled example to `experiment6/SETUP.md` under a heading `## Filled example (first smoke user, pair_index 1)` if that heading is not already present. The example is the system prompt plus `render_single_pair` for that trial. Do not include demographics or a pair number.

Token usage is stored under the smoke prefix as `token_usage.json`, one record per successful pair call (`source_record_id` is the pair record id).

## Cost contract

`--estimate-cost` must refuse if any of the three experiment 6 smokes is missing, and it must refuse to call a model. It must refuse if `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/COST_ESTIMATE.md` already exists (`FileExistsError`).

Median input and output tokens are the medians across the successful smoke pair calls for that model (up to 200). Estimated tokens in = median input times 19,960. Estimated tokens out = median output times 19,960. User count is 998 unique ids, times 20 pairs. If smoke used 10 users, do not multiply by 10 a second time.

Median USD uses the pinned rates. Low is 0.5 times median. High is 2 times median.

Write `experiments/ai_simulation_responses_2026_09_11/experiment6/COST_ESTIMATE.md` with `put_new_mirrored`. Print `cost_s3_uri=s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/COST_ESTIMATE.md`.

Markdown shape:

```markdown
# Experiment 6 cost estimate

## Pricing sources

- OpenAI Batch: ... (input $0.10/M, output $0.625/M)
- Bedrock on-demand: ...
  - Nova Micro: input $0.035/M, output $0.14/M
  - Qwen3 32B: input $0.15/M, output $0.60/M

Claude Sonnet 4.6 is excluded from experiment 6.

Low/high bounds are 0.5× and 2× the median estimate.

## Experiment 6

Estimated cost:

| model | estimated tokens in | estimated tokens out | median estimated cost | low/high estimated cost |
| --- | ---: | ---: | ---: | --- |
| openai | | | | |
| bedrock_micro_nova | | | | |
| bedrock_qwen | | | | |
```

No Claude row. No experiments 1 through 5 sections. Do not call `upload_cost_estimate` (that helper writes the parent file).

## Dispatch contract

| Command | Behavior |
|---------|----------|
| `shared/run.py --smoke` | Frozen experiment 1 four-model smoke. Unchanged. |
| `experiment6/run.py --smoke` | Experiment 6 three-model pair smoke. |
| `shared/run.py --estimate-cost` | Frozen parent cost file. Must still raise if that key exists. |
| `experiment6/run.py --estimate-cost` | Experiment 6 cost file only. |

## Must pass

- Three smoke prefixes each have 200 labels, minus content-filter failures. Print labeled and failed pair counts.
- No `experiment6/outputs/{model}/final.parquet` exists.
- `experiment6/COST_ESTIMATE.md` exists locally and on S3, with three model rows and no Claude.
- Parent `COST_ESTIMATE.md` on S3 is unchanged.
- Filled one-pair example is in `experiment6/SETUP.md`.
- Pytest still exits 0.

## Must fail

- `--smoke` writing into `final.parquet`
- `--smoke` or `--estimate-cost` calling Claude
- `--estimate-cost` before all three experiment 6 smokes exist
- `--estimate-cost` writing the parent `COST_ESTIMATE.md`
- `experiment6/run.py --smoke` invoking `smoke_command()` (experiment 1 path)
- A second `--estimate-cost` overwriting the experiment 6 S3 cost object

## Gate

Stop at the end of this step. Do not start Step 3 until the user has approved, in writing, `experiments/ai_simulation_responses_2026_09_11/experiment6/COST_ESTIMATE.md`.

## Commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --smoke
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --estimate-cost
```

Expected smoke stdout includes three `model=` blocks with `labeled_pairs=` near 200. Expected cost stdout includes `cost_s3_uri=` under `experiment6/COST_ESTIMATE.md` and no `bedrock_claude` table row.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto for the smoke code, then stop for cost approval.

Phase 1 names `experiment6/run.py --smoke` as the caller.

Phase 5 units: experiment 6 smoke paths, three-model loop with pair tasks, token_usage.json, cost markdown/upload, SETUP filled example. One commit per unit of work.

Phase 6 is complete when smoke and cost have run once live, Claude was not called, and the full cohort was not labeled.
