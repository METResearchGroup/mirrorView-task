# Study 2 DSPy optimized few-shot keep or remove inference results

Run ID: `study2-dspy-optimized-few-shot-2026-10-04`

Analysis: `s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/analysis/study2-dspy-optimized-few-shot-2026-10-04/`

Input: `experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/inputs/study_2_five_labeler/records.jsonl` with SHA-256 `1dead1efcbc7f0023813bca357d845461ddbc87b93c50e9e73b4642977883395`. It contains 13,992 rows: 4,051 unanimous and 9,941 split.

Prompt: `OPTIMIZED_STUDY_PROMPT_TEMPLATE` with SHA-256 `6ebcd9bbb16ff39dbeba93fe832a601a589ce1d8233645aad5030b105df9af15`.

All 13,992 rows were predicted for each model. Model metrics alone exclude these five prompt-demonstration matches:

- `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
- `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
- `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
- `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
- `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

The run stored 27,984 valid predictions and no unresolved failures. Nova's recorded process time includes the first pass and the later passes that retried rows whose responses failed validation. One extra Nova prediction batch was removed because it was a byte-identical copy of the previous batch.

## Measured usage

| Model folder | Wall time, seconds | Input tokens | Output tokens | Cost |
| --- | ---: | ---: | ---: | --- |
| `amazon_nova_micro` | 1653.36 | 20660607 | 280586 | Unavailable from the recorded Bedrock response and no documented rate was applied. |
| `qwen3_32b` | 521.01 | 20497255 | 294326 | Unavailable from the recorded Bedrock response and no documented rate was applied. |

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
| Amazon Nova Micro | 13,987 | 0.281617 | 0.803031 | 0.182063 | 0.621404 |
| Qwen 3 32B | 13,987 | 0.466164 | 0.640738 | 0.739717 | 0.340313 |

### Unanimous posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Amazon Nova Micro | 4,046 | 0.452489 | 0.940188 | 0.326797 | 0.735294 |
| Qwen 3 32B | 4,046 | 0.355202 | 0.759516 | 0.875817 | 0.222776 |

### Split posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Amazon Nova Micro | 9,941 | 0.259358 | 0.747209 | 0.165414 | 0.600273 |
| Qwen 3 32B | 9,941 | 0.487348 | 0.592395 | 0.724060 | 0.367277 |
