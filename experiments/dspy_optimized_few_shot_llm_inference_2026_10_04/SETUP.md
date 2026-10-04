# Data requirements

Reproduce the results in RESULTS.md from the prepared five-labeler Study 2 input and one completed inference run.

The prepared input is the manifest and records at `s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/inputs/study_2_five_labeler/`. It is a byte copy of the baseline few-shot input at `s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/`. The input contains 13,992 unique posts with five labelers. 4,051 posts are unanimous, and 9,941 posts are split.

The completed run must contain these model folders: `amazon_nova_micro` and `qwen3_32b`. Each folder needs 13,992 unique valid predictions and no unresolved failures.

The analysis artifact is under `s3://mirrorview-experimental-artifacts/experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/analysis/`.

Generated artifacts stay in S3. They are not checked into Git.
