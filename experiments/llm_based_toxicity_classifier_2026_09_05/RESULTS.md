# LLM toxicity classifier smoke results

## Command

```bash
PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
```

## Setup

- Model: `gpt-5.4-nano`
- Posts: 50
- Injected toxic posts: 15
- Seed: 42

## Runtime cost

| Metric | Value |
| ------ | ----- |
| Elapsed seconds | 141.59 |
| Input tokens | 17715 |
| Output tokens | 1100 |
| Total tokens | 18815 |
| Estimated cost (USD) | 0.0049 |

Cost uses the published GPT-5.4 nano Batch API rates: $0.20 per million input tokens and $1.25 per million output tokens.

```text
(input tokens × $0.20 / 1000000)
  + (output tokens × $1.25 / 1000000)
```

## Label distribution

| Tier | Count | Percent |
| ---- | ----- | ------- |
| low | 35 | 70.0 |
| medium | 7 | 14.0 |
| high | 8 | 16.0 |
| total | 50 | 100.0 |

## Injected posts

This is not a gold-label accuracy score. Among the 15 posts that had toxic language inserted, the model labeled 0 low, 7 medium, and 8 high.

## Outputs

- `outputs/synthetic_posts.csv`
- `outputs/labels.json`
- `outputs/metrics.json`
