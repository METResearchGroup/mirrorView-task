# Few-shot Jev keep or remove inference on Study 2

## Run record

Production run ID: `study2-jev-few-shot-2026-10-01`.

S3 run prefix: `s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/runs/study2-jev-few-shot-2026-10-01/jev_1_13_0/`.

Analysis prefix: `s3://mirrorview-experimental-artifacts/experiments/few_shot_jev_inference_2026_10_01/analysis/study2-jev-few-shot-2026-10-01/`.

Smoke measurement:

smoke_run_id=study2-jev-few-shot-2026-10-01-smoke rows=5 predictions=5 unresolved_failures=0 status=complete real_seconds=4.26 input_tokens=8885 output_tokens=105 usd=0.000373

Production measurement:

production_run_id=study2-jev-few-shot-2026-10-01 predictions=13992 unresolved_failures=0 status=complete real_seconds=809.81 input_tokens=24672077 output_tokens=293832 usd=1.036227

The prompt has ten demonstrations. Five of them are exact matches to prepared rows, and those five rows are unanimous. Model metrics leave those five rows out. Human label counts include all 13,992 predictions, including those five rows. The split-vote table counts the 9,941 split predictions, and those five unanimous rows are not in it. Usage includes all 13,992 predictions. Model metrics use 13,987 rows for all posts, 4,046 unanimous rows, and 9,941 split rows. F1, recall, and precision treat remove as the positive label.

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
| Jev 1.13.0 | 13,987 | 0.561910 | 0.787517 | 0.642616 | 0.499214 |

### Unanimous posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 4,046 | 0.664251 | 0.931290 | 0.898693 | 0.526820 |

### Split posts

| Model | N | F1 | Accuracy | Recall | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 9,941 | 0.547683 | 0.729001 | 0.613158 | 0.494842 |

## Jev usage

| Model | Predictions | Input tokens | Output tokens | USD |
| --- | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 13,992 | 24,672,077 | 293,832 | 1.036227 |
