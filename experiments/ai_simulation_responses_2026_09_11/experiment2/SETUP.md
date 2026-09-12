# Experiment 2 setup

Humans judged one linked-fate pair at a time on the website. Models in this experiment see all 20 pairs in one prompt and return a list of 1-indexed pair numbers to remove.

## Data

Shared cohort parquet at `../shared/cohort_users.parquet` and `../shared/cohort_trials.parquet` (also on S3 under the same relative path in `mirrorview-experimental-artifacts`).

## Prompt template

System prompt is `STUDY_SYSTEM_PROMPT` in `../shared/prompts.py`.

User prompt shape (omit empty demographic bullets):

```text
## Participant information

The following answers were provided by the participant whose keep/remove choices you are simulating. Use them if they help you match that participant's decisions.

- Age: {age}
- Gender: {gender}
- Education: {education}
- Political affiliation: {political_affiliation}
- Party lean: {party_lean}
- Party group: {party_group}
- Political ideology (1 = Extremely liberal, 7 = Extremely conservative): {political_ideology}
- How closely do you follow politics (1 = Not closely at all, 7 = Very closely): {political_follow}
- I identify with the Republican Party (1 = Fully Disagree, 7 = Fully agree): {rep_id}
- I identify with the Democratic Party (1 = Fully Disagree, 7 = Fully agree): {dem_id}
- Reducing access to abortion (0 = Strongly Oppose, 100 = Strongly Support): {attitude_reduce_abortion}
- Providing a path to citizenship for undocumented immigrants (0 to 100): {attitude_citizenship_undocumented}
- Increasing restrictions on gun ownership (0 to 100): {attitude_restrict_guns}
- Increasing government regulations to protect the environment (0 to 100): {attitude_regulate_environment}
- Raising taxes on the wealthiest Americans (0 to 100): {attitude_raise_wealth_taxes}
- Expanding Medicaid to cover all currently uninsured Americans (0 to 100): {attitude_expand_medicaid}

## Post pair 1

Post 1:
{first text in pair_order}

Post 2:
{second text in pair_order}

## Post pair 2

...
```

Full experiment 2 labeling waits on explicit approval of this template.

## Models

Four models label the full cohort: OpenAI `gpt-5.4-nano`, Bedrock Nova Micro, Bedrock Qwen3 32B, and Bedrock Claude Sonnet 4.6.
