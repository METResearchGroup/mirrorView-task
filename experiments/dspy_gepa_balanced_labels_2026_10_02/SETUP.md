# Setup

This ablation redraws 405 unanimous Study 2 posts so the cohort is 203 keep and 202 remove. The finished natural-prevalence run stays in `experiments/dspy_gepa_optimization_2026_09_30/`.

## Required data

- Registered dataset `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS`.
- The same ten excluded prompt-example post IDs used by the finished run.
- The issue 329 prompt in `experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py`.

The cohort is written under `s3://mirrorview-experimental-artifacts/experiments/dspy_gepa_balanced_labels_2026_10_02/`.

| Split | Posts | Keep | Remove |
| --- | ---: | ---: | ---: |
| Optimization | 222 | 111 | 111 |
| GEPA validation | 61 | 31 | 30 |
| Development | 61 | 30 | 31 |
| Test | 61 | 31 | 30 |
