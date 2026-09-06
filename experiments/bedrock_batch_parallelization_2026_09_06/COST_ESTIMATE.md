# Bedrock Nova Micro cost estimate

Model: `us.amazon.nova-micro-v1:0`

On-demand Ohio rates: $0.035 per million input tokens, and $0.14 per million output tokens.

Mean tokens per request from the 100-post smoke: 284.85 input, and 10.00 output.

100-post smoke actual cost: $0.0011

Size runs totaling 9,500 posts: $0.1080 (2,706,075 input tokens, 95,000 output tokens).

Process-count runs totaling 40,000 posts: $0.4548 (11,394,000 input tokens, 400,000 output tokens).

Combined estimate: $0.5628

2x ceiling: $1.1256

Steps 4 and 5 live jobs wait for operator approval.

After approval, start the size runs with:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py --i-approve-the-cost-estimate
```

After approval, start the process-count runs with:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/run_process_experiment.py --i-approve-the-cost-estimate
```
