# LLM toxicity classifier live test results

## Command

```bash
PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
```

## Setup

- Model: `gpt-5.4-nano`
- Posts: 50
- Posts with added toxic language: 15
- Seed: 42

## Runtime cost

| Metric | Value |
| ------ | ----- |
| Elapsed seconds | 32.06 |
| Input tokens | 17767 |
| Output tokens | 1100 |
| Total tokens | 18867 |
| Estimated cost (USD) | 0.0049 |

The estimated cost is computed from the published GPT-5.4 nano Batch API rates. The rates are $0.20 per million input tokens and $1.25 per million output tokens.

```text
(input tokens × $0.20 / 1000000)
  + (output tokens × $1.25 / 1000000)
```

## Counts of low, medium, and high labels

| Tier | Count | Percent |
| ---- | ----- | ------- |
| low | 34 | 68.0 |
| medium | 8 | 16.0 |
| high | 8 | 16.0 |
| total | 50 | 100.0 |

## Posts with added toxic language

The 15 posts that had toxic language added were labeled 0 low, 7 medium, and 8 high. The live test only checks that the classifier returned labels for those posts, and it is not a measure of accuracy against human labels.

## Outputs

- `outputs/synthetic_posts.csv`
- `outputs/labels.json`
- `outputs/metrics.json`
