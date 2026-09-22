# Experiment 5 setup

After experiments 1 through 4 finish labeling and scoring, this step ranks false-negative posts, false-positive posts, and lowest-F1 users. It reads existing labels and cohort fields only.

## Inputs

Shared cohort parquet:

- `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/shared/cohort_users.parquet`
- `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/shared/cohort_trials.parquet`

Sixteen `final.parquet` files (experiments 1 through 4, four models each):

| experiment | model | final_uri |
| --- | --- | --- |
| 1 | openai | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/openai/final.parquet` |
| 1 | bedrock_micro_nova | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/bedrock_micro_nova/final.parquet` |
| 1 | bedrock_qwen | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/bedrock_qwen/final.parquet` |
| 1 | bedrock_claude | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/bedrock_claude/final.parquet` |
| 2 | openai | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment2/outputs/openai/final.parquet` |
| 2 | bedrock_micro_nova | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment2/outputs/bedrock_micro_nova/final.parquet` |
| 2 | bedrock_qwen | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment2/outputs/bedrock_qwen/final.parquet` |
| 2 | bedrock_claude | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment2/outputs/bedrock_claude/final.parquet` |
| 3 | openai | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment3/outputs/openai/final.parquet` |
| 3 | bedrock_micro_nova | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment3/outputs/bedrock_micro_nova/final.parquet` |
| 3 | bedrock_qwen | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment3/outputs/bedrock_qwen/final.parquet` |
| 3 | bedrock_claude | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment3/outputs/bedrock_claude/final.parquet` |
| 4 | openai | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment4/outputs/openai/final.parquet` |
| 4 | bedrock_micro_nova | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment4/outputs/bedrock_micro_nova/final.parquet` |
| 4 | bedrock_qwen | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment4/outputs/bedrock_qwen/final.parquet` |
| 4 | bedrock_claude | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment4/outputs/bedrock_claude/final.parquet` |

## Outputs

- `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_negative_posts.csv`
- `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_positive_posts.csv`
- `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/lowest_f1_users.csv`
- `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment5/RESULTS.md`
