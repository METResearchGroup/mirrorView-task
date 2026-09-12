# Experiment 6 cost estimate

## Pricing sources

- OpenAI Batch: https://developers.openai.com/api/docs/pricing (input $0.10/M, output $0.625/M)
- Bedrock on-demand: https://aws.amazon.com/bedrock/pricing/
  - Nova Micro: input $0.035/M, output $0.14/M
  - Qwen3 32B: input $0.15/M, output $0.60/M

Claude Sonnet 4.6 is excluded from experiment 6.

Low/high bounds are 0.5× and 2× the median estimate.

## Experiment 6

Estimated cost:

| model | estimated tokens in | estimated tokens out | median estimated cost | low/high estimated cost |
| --- | --- | --- | --- | --- |
| openai | 9520920 | 319360 | $1.15 | $0.58 / $2.30 |
| bedrock_micro_nova | 8602760 | 199600 | $0.33 | $0.16 / $0.66 |
| bedrock_qwen | 8932100 | 279440 | $1.51 | $0.75 / $3.01 |
