# Bedrock Nova Micro throughput experiment

This experiment compares Amazon Nova Micro on Bedrock Converse with the OpenAI Batch GPT-5.4 nano runs. Native Bedrock batch jobs are not available in this AWS account without a new IAM service role, and the details are in `FINDINGS.md`. Measured results are in `RESULTS.md`.

## Smoke

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python data_platform/generate_features/smoke_bedrock_engine.py \
  --posts-csv shared/data/raw/study_phase_2_part_2/stimuli/flips.csv \
  --post-count 100 \
  --id-column post_primary_key \
  --text-column original_text
```

Then:

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/write_cost_estimate.py
```

## Size and process jobs

Without `--i-approve-the-cost-estimate` these commands exit 2 and do not call Bedrock:

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py
```

The approved runs for this experiment have already been executed. To repeat them, pass `--i-approve-the-cost-estimate` on those same commands.
