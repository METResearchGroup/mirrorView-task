# Zero-shot Jev keep or remove inference for Study 2

## Run record

Run ID: `study2-jev-zero-shot-2026-10-01`.

Analysis prefix: `s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/analysis/study2-jev-zero-shot-2026-10-01/`.

Smoke usage: `rows=5 mean_input_tokens=740.0 est_full_input_tokens=10354080 est_full_usd=0.4349`.

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
| Jev 1.13.0 | 13,992 | 0.529322 | 0.712621 | 0.761792 | 0.405561 |

### Unanimous posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 4,051 | 0.493617 | 0.853123 | 0.941558 | 0.334487 |

### Split posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 9,941 | 0.535016 | 0.655367 | 0.740977 | 0.418649 |

## Jev usage

| Model | Predictions | Input tokens | Output tokens | USD |
| --- | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 13,992 | 10,162,373 | 293,832 | 0.426820 |
