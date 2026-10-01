# Data requirements

The source input is issue 326's prepared Study 2 five-labeler package:

`s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/`

This experiment stores a byte copy of that package at:

`s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/`

Analysis uses the complete run `study2-jev-zero-shot-2026-10-01`. Predictions, failures, and manifests live in `runs/study2-jev-zero-shot-2026-10-01/jev_1_13_0/`. That folder must hold 13,992 unique valid predictions and no unresolved failures.

The analysis bundle is at:

`s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/analysis/study2-jev-zero-shot-2026-10-01/`

Generated artifacts stay in S3.
