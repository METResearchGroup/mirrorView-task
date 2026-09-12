# Experiment 6 setup

Humans judged one linked-fate pair at a time on the website. Experiment 1 showed all 20 pairs in one prompt. Experiment 6 matches the human process: one unnumbered pair per call, and a yes/no answer on whether to remove both posts.

## Data

Shared cohort parquet at `../shared/cohort_users.parquet` and `../shared/cohort_trials.parquet` (also on S3 under the same relative path in `mirrorview-experimental-artifacts`). Use the existing 998 unique `prolific_id` values. Do not rebuild the cohort.

## Prompt

The user message is only `Post 1:` and `Post 2:` for that trial, following stored `pair_order`. It does not include a pair number or the other 19 pairs. System prompt is `STUDY_SYSTEM_PROMPT_SINGLE_PAIR` in `../shared/prompts.py`. Model output is JSON `{"remove": "yes"}` or `{"remove": "no"}`.

## Models

Three models label the full cohort: OpenAI `gpt-5.4-nano`, Bedrock Nova Micro, and Bedrock Qwen3 32B. Claude Sonnet 4.6 is excluded.

## Filled example (first smoke user, pair_index 1)

```text
We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.

The pairs are political mirrors of each other. This means that the mirror text recreates the original message from the opposite political stance. For example:

Original Text:
I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!

Mirror Text:
I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!

Notice that the mirror text changes the core message to match that of the opposite political stance. In other words, the mirror text is not a response to the original text - it replicates the original message as if written from the opposite political stance.

Your job is to decide whether both posts in the pair should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

There are no right or wrong answers - we are interested in what you personally think.

You will see one post pair in the user message. Return a JSON object with a single field remove. Set remove to yes if both posts in the pair should be removed from the platform. Set remove to no if both posts should be kept.

Post 1:
I fucking hope they try. Red states take in more federal dollars than they ever put in. They are actually welfare states. Meaning if federal redistribution stopped tomorrow, places like Mississippi and Kentucky would absolutely collapse without blue state money propping them up. Keep crying about big government while cashing those federal checks. Let's call that bluff.

Post 2:
I fucking hope they try. NYC contributes more in federal taxes than it receives back in federal spending. We are actually a donor city. Meaning if we kept 100% of what we contribute not only would we be fine we would be actually better off, at the detriment to the US budget and cities and states that are recipient states that rely on federal funding. Let's light this candle.
```
