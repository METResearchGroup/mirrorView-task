# Bedrock Nova Micro cost estimate

The model is `us.amazon.nova-micro-v1:0`.

On-demand Ohio rates are $0.035 per million input tokens, and $0.14 per million output tokens.

Mean tokens per request from the smoke run of 100 posts are 284.85 input tokens and 10.00 output tokens.

The actual cost of the smoke run of 100 posts was $0.0011.

The size runs total 9,500 posts, and the estimated cost is $0.1080, from 2,706,075 input tokens and 95,000 output tokens.

The process count runs total 40,000 posts, and the estimated cost is $0.4548, from 11,394,000 input tokens and 400,000 output tokens.

The combined estimate is $0.5628.

The allowed ceiling is twice the combined estimate, which is $1.1256.

Steps 4 and 5 live jobs wait for operator approval.

After approval, start the size runs with:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py --i-approve-the-cost-estimate
```

After approval, start the process count runs with:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py --i-approve-the-cost-estimate
```
