# Data requirements

Reproduce this result from the prepared five-labeler Study 2 input and one completed inference run.

The prepared input is the manifest and records at `s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/`. It is a byte copy of the zero-shot input and contains 13,992 unique posts with five labelers: 4,051 unanimous and 9,941 split.

The completed run ID is `study2-few-shot-2026-10-01`. It must contain these model folders: `amazon_nova_micro`, `qwen3_32b`, `openai_gpt_5_6_terra`, and `claude_sonnet_5_5`. Each folder needs 13,992 unique valid predictions and no unresolved failures.

The analysis artifact is at `s3://mirrorview-experimental-artifacts/experiments/few_shot_llm_inference_2026_09_30/analysis/study2-few-shot-2026-10-01/`.

Generated artifacts stay in S3. They are not checked into Git.
