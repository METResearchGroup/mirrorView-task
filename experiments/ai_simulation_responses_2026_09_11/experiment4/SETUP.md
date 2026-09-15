# Experiment 4 setup

Humans judged one linked-fate pair at a time on the website. Models in this experiment see all 20 pairs in one prompt and return a list of 1-indexed pair numbers to remove.

## Data

Shared cohort parquet at `../shared/cohort_users.parquet` and `../shared/cohort_trials.parquet` (also on S3 under the same relative path in `mirrorview-experimental-artifacts`).

## Prompt

Experiment 4 concatenates the experiment 2 demographics block, the experiment 3 reflection block, then the 20 post pairs. System prompt is `STUDY_SYSTEM_PROMPT` in `../shared/prompts.py`.

## Models

Four models label the full cohort: OpenAI `gpt-5.4-nano`, Bedrock Nova Micro, Bedrock Qwen3 32B, and Bedrock Claude Sonnet 4.6.

## Full-cohort labeling

Live `run_id`: `ai_simulation_responses_2026_09_11_experiment4:remove_indexes`

OpenAI Batch id: `batch_6aa4dd2e87248190bda77f97e0503afb`

The cohort parquet has 1,000 rows and 998 unique `prolific_id` values. Labels use `prolific_id` as `source_record_id`, so each model labels 998 users.

| model | labeled | failed | final_uri |
| --- | --- | --- | --- |
| openai | 998 | 0 | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment4/outputs/openai/final.parquet` |
| bedrock_micro_nova | 998 | 0 | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment4/outputs/bedrock_micro_nova/final.parquet` |
| bedrock_qwen | 998 | 0 | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment4/outputs/bedrock_qwen/final.parquet` |
| bedrock_claude | 997 | 1 | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment4/outputs/bedrock_claude/final.parquet` |
