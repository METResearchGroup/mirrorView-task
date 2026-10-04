# Study 2 few-shot keep or remove inference results

Run ID: `study2-few-shot-2026-10-01`

Analysis: `s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/analysis/study2-few-shot-2026-10-01/`

Input: `experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl` with SHA-256 `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. It contains 13,992 rows: 4,051 unanimous and 9,941 split.

Prompt: `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT` with SHA-256 `ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3`.

All 13,992 rows were predicted for each model. Model metrics alone exclude these five prompt-demonstration matches:

- `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
- `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
- `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
- `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
- `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

The run stored 55,968 valid predictions and no unresolved failures.

## Measured usage

| Model folder | Wall time, seconds | Input tokens | Output tokens | Cost |
| --- | ---: | ---: | ---: | --- |
| `amazon_nova_micro` | 959.86 | 19535295 | 310298 | Unavailable from the recorded Bedrock response and no documented rate was applied. |
| `qwen3_32b` | 620.21 | 19643743 | 317883 | Unavailable from the recorded Bedrock response and no documented rate was applied. |
| `openai_gpt_5_6_terra` | 2315.01 | 27984 | 799910 | Unavailable from the recorded Bedrock response and no documented rate was applied. |
| `claude_sonnet_5_5` | 1030.45 | 29928471 | 311874 | Unavailable from the recorded Bedrock response and no documented rate was applied. |

## Human label distribution

| Dataset | Label | Count | Proportion |
| --- | --- | ---: | ---: |
| all | keep | 11,024 | 0.787879 |
| all | remove | 2,968 | 0.212121 |
| unanimous | keep | 3,743 | 0.923969 |
| unanimous | remove | 308 | 0.076031 |
| split | keep | 7,281 | 0.732421 |
| split | remove | 2,660 | 0.267579 |

## Split remove-vote distribution

| Remove votes | Count | Proportion |
| ---: | ---: | ---: |
| 1 | 4,244 | 0.426919 |
| 2 | 3,037 | 0.305502 |
| 3 | 1,777 | 0.178755 |
| 4 | 883 | 0.088824 |

## Model metrics

### All five-labeler posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Amazon Nova Micro | 13,987 | 0.428947 | 0.580253 | 0.743425 | 0.301435 |
| Qwen 3 32B | 13,987 | 0.463378 | 0.566812 | 0.881996 | 0.314234 |
| OpenAI GPT-5.6 Terra | 13,987 | 0.338110 | 0.805176 | 0.234659 | 0.604692 |
| Claude Sonnet 5.5 | 13,987 | 0.330366 | 0.806392 | 0.225219 | 0.619666 |

### Unanimous posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Amazon Nova Micro | 4,046 | 0.274428 | 0.654968 | 0.862745 | 0.163164 |
| Qwen 3 32B | 4,046 | 0.305225 | 0.668067 | 0.964052 | 0.181315 |
| OpenAI GPT-5.6 Terra | 4,046 | 0.526316 | 0.942165 | 0.424837 | 0.691489 |
| Claude Sonnet 5.5 | 4,046 | 0.511931 | 0.944390 | 0.385621 | 0.761290 |

### Split posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Amazon Nova Micro | 9,941 | 0.464521 | 0.549844 | 0.729699 | 0.340706 |
| Qwen 3 32B | 9,941 | 0.496046 | 0.525601 | 0.872556 | 0.346521 |
| OpenAI GPT-5.6 Terra | 9,941 | 0.312448 | 0.749422 | 0.212782 | 0.587747 |
| Claude Sonnet 5.5 | 9,941 | 0.307005 | 0.750226 | 0.206767 | 0.595883 |
