# Zero-shot keep or remove inference for Study 2

## Run provenance

- Run ID: `study2-zero-shot-2026-10-01`
- Analysis artifacts: `s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/analysis/study2-zero-shot-2026-10-01/`
- Four Amazon Nova Micro predictions were stored from rejected replies whose probabilities were 85 or 95. Those values were scaled to 0.85 and 0.95 before the complete manifest was written. Token usage on those four rows is 0 because the rejected calls did not retain usage.

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
| Amazon Nova Micro | 13,992 | 0.426029 | 0.550529 | 0.786388 | 0.292152 |
| Qwen 3 32B | 13,992 | 0.498773 | 0.649800 | 0.821429 | 0.358108 |
| OpenAI GPT-5.6 Terra | 13,992 | 0.316304 | 0.800100 | 0.217992 | 0.576135 |
| Claude Sonnet 5.5 | 13,992 | 0.223602 | 0.803459 | 0.133423 | 0.689895 |

### Unanimous posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Amazon Nova Micro | 4,051 | 0.256932 | 0.603061 | 0.902597 | 0.149784 |
| Qwen 3 32B | 4,051 | 0.395946 | 0.779314 | 0.951299 | 0.250000 |
| OpenAI GPT-5.6 Terra | 4,051 | 0.478528 | 0.937053 | 0.379870 | 0.646409 |
| Claude Sonnet 5.5 | 4,051 | 0.382134 | 0.938534 | 0.250000 | 0.810526 |

### Split posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Amazon Nova Micro | 9,941 | 0.467645 | 0.529122 | 0.772932 | 0.335236 |
| Qwen 3 32B | 9,941 | 0.517117 | 0.597022 | 0.806391 | 0.380589 |
| OpenAI GPT-5.6 Terra | 9,941 | 0.294281 | 0.744291 | 0.199248 | 0.562633 |
| Claude Sonnet 5.5 | 9,941 | 0.203249 | 0.748416 | 0.119925 | 0.665971 |
