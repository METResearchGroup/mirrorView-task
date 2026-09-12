# Experiment 4 setup

Humans judged one linked-fate pair at a time on the website. Models in this experiment see all 20 pairs in one prompt and return a list of 1-indexed pair numbers to remove.

## Data

Shared cohort parquet at `../shared/cohort_users.parquet` and `../shared/cohort_trials.parquet` (also on S3 under the same relative path in `mirrorview-experimental-artifacts`).

## Prompt

Experiment 4 concatenates the experiment 2 demographics block, the experiment 3 reflection block, then the 20 post pairs. System prompt is `STUDY_SYSTEM_PROMPT` in `../shared/prompts.py`.

## Models

Four models label the full cohort: OpenAI `gpt-5.4-nano`, Bedrock Nova Micro, Bedrock Qwen3 32B, and Bedrock Claude Sonnet 4.6.
