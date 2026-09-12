# AI simulation responses cost estimate

## Pricing sources

- OpenAI Batch: https://developers.openai.com/api/docs/pricing (input $0.10/M, output $0.625/M)
- Bedrock on-demand: https://aws.amazon.com/bedrock/pricing/
  - Nova Micro: input $0.035/M, output $0.14/M
  - Qwen3 32B: input $0.15/M, output $0.60/M
  - Claude Sonnet 4.6: input $3.00/M, output $15.00/M

Low/high bounds are 0.5× and 2× the median estimate.

## Experiment 1

Estimated cost:

| model | estimated tokens in | estimated tokens out | median estimated cost | low/high estimated cost |
| --- | --- | --- | --- | --- |
| openai | 2673000 | 35000 | $0.29 | $0.14 / $0.58 |
| bedrock_micro_nova | 2765500 | 256000 | $0.13 | $0.07 / $0.27 |
| bedrock_qwen | 2661000 | 36500 | $0.42 | $0.21 / $0.84 |
| bedrock_claude | 2909000 | 19500 | $9.02 | $4.51 / $18.04 |

## Experiment 2

Estimated cost:

| model | estimated tokens in | estimated tokens out | median estimated cost | low/high estimated cost |
| --- | --- | --- | --- | --- |
| openai | 2966533 | 35000 | $0.32 | $0.16 / $0.64 |
| bedrock_micro_nova | 3069191 | 256000 | $0.14 | $0.07 / $0.29 |
| bedrock_qwen | 2953215 | 36500 | $0.46 | $0.23 / $0.93 |
| bedrock_claude | 3228449 | 19500 | $9.98 | $4.99 / $19.96 |

## Experiment 3

Estimated cost:

| model | estimated tokens in | estimated tokens out | median estimated cost | low/high estimated cost |
| --- | --- | --- | --- | --- |
| openai | 2879205 | 35000 | $0.31 | $0.15 / $0.62 |
| bedrock_micro_nova | 2978841 | 256000 | $0.14 | $0.07 / $0.28 |
| bedrock_qwen | 2866279 | 36500 | $0.45 | $0.23 / $0.90 |
| bedrock_claude | 3133411 | 19500 | $9.69 | $4.85 / $19.39 |

## Experiment 4

Estimated cost:

| model | estimated tokens in | estimated tokens out | median estimated cost | low/high estimated cost |
| --- | --- | --- | --- | --- |
| openai | 3172738 | 35000 | $0.34 | $0.17 / $0.68 |
| bedrock_micro_nova | 3282531 | 256000 | $0.15 | $0.08 / $0.30 |
| bedrock_qwen | 3158494 | 36500 | $0.50 | $0.25 / $0.99 |
| bedrock_claude | 3452860 | 19500 | $10.65 | $5.33 / $21.30 |

## Experiment 5

Estimated cost: 0 (analysis only)

## Total across experiments

Estimated cost:

| model | estimated tokens in | estimated tokens out | median estimated cost | low/high estimated cost |
| --- | --- | --- | --- | --- |
| openai | 11691476 | 140000 | $1.26 | $0.62 / $2.52 |
| bedrock_micro_nova | 12096063 | 1024000 | $0.56 | $0.29 / $1.14 |
| bedrock_qwen | 11638988 | 146000 | $1.83 | $0.92 / $3.66 |
| bedrock_claude | 12723720 | 78000 | $39.34 | $19.68 / $78.69 |
