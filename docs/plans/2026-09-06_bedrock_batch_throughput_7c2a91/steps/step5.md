# Step 5: Add the process-count runner, do not execute it

Add a runner that can spawn 2, 4, 6, and 8 processes of 2,000 posts each. Do not execute those jobs until the operator approves `COST_ESTIMATE.md`.

## Caller / unit of work

**Main caller:** `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py` `main()`.

**Slice:** parse process counts → for each count, spawn processes that each call `run_bedrock_engine_smoke` on 2,000 posts → checkpoint JSON. Refuse to run unless `--i-approve-the-cost-estimate` is passed.

**Out of scope:** live execution in this PR, size jobs, pytest for `experiments/`, IAM roles.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/openai_batch_parallelization_2026_09_05/run_experiment.py` | Process pool, aggregate metrics, checkpoint JSON |
| `/workspace/data_platform/generate_features/smoke_bedrock_engine.py` | `run_bedrock_engine_smoke` |

## Files allowed to change

- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py` (create)
- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/README.md` (update)

## Files forbidden to change

- `/workspace/data_platform/generate_features/engines/bedrock_engine.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/COST_ESTIMATE.md`

## Contracts to lock

```text
BATCH_SIZE_PER_PROCESS = 2000
DEFAULT_PROCESS_COUNTS = "2,4,6,8"
SOURCE_POSTS_CSV = shared/data/raw/study_phase_2_part_2/stimuli/flips.csv
ID_COLUMN = "post_primary_key"
TEXT_COLUMN = "original_text"
OUTPUT_JSON = experiments/bedrock_batch_parallelization_2026_09_06/process_results.json
ON_DEMAND_INPUT_USD_PER_MILLION = 0.035
ON_DEMAND_OUTPUT_USD_PER_MILLION = 0.14
```

Copy the OpenAI process experiment's spawn, aggregate, and checkpoint behavior. Use `multiprocessing` spawn and `ProcessPoolExecutor`. Without `--i-approve-the-cost-estimate`, exit 2 and do not call Bedrock.

## Pass / fail

Must pass:

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py
```

Expected: exit 2. Output contains `blocked`. No Bedrock calls. `process_results.json` is not created.

Must fail the step if the default command starts a live job.

## Commands with expected output

Blocked (this PR):

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py
```

Exit 2.

After later approval, not in this PR:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py \
  --i-approve-the-cost-estimate
```
