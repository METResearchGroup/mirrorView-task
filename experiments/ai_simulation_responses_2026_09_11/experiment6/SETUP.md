# Experiment 6 setup

Humans judged one linked-fate pair at a time on the website. Experiment 1 showed all 20 pairs in one prompt. Experiment 6 matches the human process: one unnumbered pair per call, and a yes/no answer on whether to remove both posts.

## Data

Shared cohort parquet at `../shared/cohort_users.parquet` and `../shared/cohort_trials.parquet` (also on S3 under the same relative path in `mirrorview-experimental-artifacts`). Use the existing 998 unique `prolific_id` values. Do not rebuild the cohort.

## Prompt

The user message is only `Post 1:` and `Post 2:` for that trial, following stored `pair_order`. It does not include a pair number or the other 19 pairs. System prompt is `STUDY_SYSTEM_PROMPT_SINGLE_PAIR` in `../shared/prompts.py`. Model output is JSON `{"remove": "yes"}` or `{"remove": "no"}`.

## Models

Three models label the full cohort: OpenAI `gpt-5.4-nano`, Bedrock Nova Micro, and Bedrock Qwen3 32B. Claude Sonnet 4.6 is excluded.
