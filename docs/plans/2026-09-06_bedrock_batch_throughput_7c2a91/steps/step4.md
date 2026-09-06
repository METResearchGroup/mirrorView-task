# Step 4: Add the batch-size runner, do not execute it

Add a runner that can label the OpenAI size list through the Bedrock engine. Do not run the 9,500-post jobs until the operator approves `COST_ESTIMATE.md`.

## Caller / unit of work

**Main caller:** `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py` `main()`.

**Slice:** parse size list → for each size, call `run_bedrock_engine_smoke` → checkpoint JSON. Refuse to run unless `--i-approve-the-cost-estimate` is passed.

**Out of scope:** live execution in this PR, process-count jobs, pytest for `experiments/`, IAM roles.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/generate_features/smoke_bedrock_engine.py` | `run_bedrock_engine_smoke` |
| `/workspace/data_platform/generate_features/OPENAI_BATCH_SMOKE_RESULTS.md` | Size list |
| `/workspace/experiments/openai_batch_parallelization_2026_09_05/run_experiment.py` | Checkpoint JSON shape |

## Files allowed to change

- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py` (create)
- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/README.md` (create or update)

## Files forbidden to change

- `/workspace/data_platform/generate_features/engines/bedrock_engine.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/COST_ESTIMATE.md`

## Contracts to lock

```text
DEFAULT_SIZES = "100,200,300,400,500,1000,2000,5000"
SOURCE_POSTS_CSV = shared/data/raw/study_phase_2_part_2/stimuli/flips.csv
ID_COLUMN = "post_primary_key"
TEXT_COLUMN = "original_text"
OUTPUT_JSON = experiments/bedrock_batch_parallelization_2026_09_06/size_results.json
```

Without `--i-approve-the-cost-estimate`, `main` prints that the live size jobs are blocked and exits 2. It must not call Bedrock.

With the flag, it runs each size through `run_bedrock_engine_smoke` and writes `size_results.json` after every size, matching the OpenAI smoke table columns plus `estimated_cost_usd`.

## Pass / fail

Must pass:

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py
```

Expected: exit 2. Stderr or stdout contains `blocked`. No Bedrock calls. `size_results.json` is not created.

Must fail the step if the default command starts a live job.

## Commands with expected output

Blocked (this PR):

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py
```

Exit 2.

After later approval, not in this PR:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py \
  --i-approve-the-cost-estimate
```
