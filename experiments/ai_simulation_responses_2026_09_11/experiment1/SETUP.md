# Experiment 1 setup

Humans judged one linked-fate pair at a time on the website. Models in this experiment see all 20 pairs in one prompt and return a list of 1-indexed pair numbers to remove.

## Data

Shared cohort parquet at `../shared/cohort_users.parquet` and `../shared/cohort_trials.parquet` (also on S3 under the same relative path in `mirrorview-experimental-artifacts`).

## Prompt

Experiment 1 user prompt contains only the 20 post pairs. System prompt is `STUDY_SYSTEM_PROMPT` in `../shared/prompts.py`.

## Models

Four models label the full cohort: OpenAI `gpt-5.4-nano`, Bedrock Nova Micro, Bedrock Qwen3 32B, and Bedrock Claude Sonnet 4.6.
## Smoke (Step 2)

Smoke user count: 10

Smoke S3 prefixes:

- `openai`: `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/openai/smoke/`
- `bedrock_micro_nova`: `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/bedrock_micro_nova/smoke/`
- `bedrock_qwen`: `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/bedrock_qwen/smoke/`
- `bedrock_claude`: `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/bedrock_claude/smoke/`
