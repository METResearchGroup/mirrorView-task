# Step 3: Write the cost estimate and wait for approval

Turn the 100-post smoke token counts into a dollar estimate for the OpenAI-sized runs. Do not start those runs.

## Caller / unit of work

**Main caller:** `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/write_cost_estimate.py` `main()`.

**Slice:** read `smoke_metrics.json` → scale mean tokens per request to 9,500 and 40,000 posts → write `COST_ESTIMATE.md`.

**Out of scope:** live size runs, live process-count runs, pytest (experimental code), changing the engine.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/smoke_metrics.json` | Step 2 output |
| `/workspace/data_platform/generate_features/OPENAI_BATCH_SMOKE_RESULTS.md` | OpenAI job sizes and process counts |
| `/workspace/docs/plans/2026-09-06_bedrock_batch_throughput_7c2a91/plan.md` | On-demand rates and ceiling |

## Files allowed to change

- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/write_cost_estimate.py` (create)
- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/COST_ESTIMATE.md` (create)

## Files forbidden to change

- `/workspace/data_platform/generate_features/engines/bedrock_engine.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/experiments/openai_batch_parallelization_2026_09_05/**`

## Contracts to lock

```text
SIZE_POST_COUNTS = (100, 200, 300, 400, 500, 1000, 2000, 5000)
# sum = 9500
PROCESS_COUNTS = (2, 4, 6, 8)
POSTS_PER_PROCESS = 2000
# total process posts = 40000
ON_DEMAND_INPUT_USD_PER_MILLION = 0.035
ON_DEMAND_OUTPUT_USD_PER_MILLION = 0.14
TOKENS_PER_MILLION = 1_000_000
CEILING_MULTIPLIER = 2
```

Cost for a post count:

```text
input_tokens = round(mean_input_tokens_per_request * post_count)
output_tokens = round(mean_output_tokens_per_request * post_count)
usd = (input_tokens * 0.035 + output_tokens * 0.14) / 1_000_000
```

`COST_ESTIMATE.md` must include:

- Model id and on-demand Ohio rates
- Mean input and output tokens per request from the smoke
- Estimated dollars for the 100-post smoke (actual from `smoke_metrics.json`)
- Estimated dollars for the size runs totaling 9,500 posts
- Estimated dollars for the process-count runs totaling 40,000 posts
- Combined estimate and the 2x ceiling
- The sentence "Steps 4 and 5 live jobs wait for operator approval."
- Exact commands that would start those jobs after approval

## Pass / fail

Must pass:

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/write_cost_estimate.py
```

Expected: exit 0. `COST_ESTIMATE.md` exists and contains the combined estimate and the wait sentence.

Must fail the step if:

- The script submits any Bedrock request.
- The script starts Step 4 or Step 5 jobs.

## Commands with expected output

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/write_cost_estimate.py
```

Stdout includes `Wrote experiments/bedrock_batch_parallelization_2026_09_06/COST_ESTIMATE.md`. Exit code 0.
