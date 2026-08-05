# Mining free responses for features

## Motivation

During the second phase of our study in part 2, we asked users to leave free response and survey feedback related to what information they used to determine their keep versus remove decisions.

## Background

In Phase 2, Part 2, we asked users to rate 20 posts in the linked fate condition. We then asked them the following:

- Free response (phase1_pair_reflection_text): what was going through their mind; what influenced evaluating posts as a pair.
- 1–7 Likert (phase1_pair_influence_rating): how much seeing both versions influenced deacisions (1 = Not at all, 7 = Very much).

We can take their free responses and mine them for insights.

## Proposed solution

1. Histogram: what was the distribution of the Likert scores?
2. Mine the free responses for features (we have some details on this in `experiments/create_llm_feature_clusters_2026_08_02/PLAN.md`).

We'll actually split out analysis into two parts:

- Users who gave a Likert score < 4
- Users who gave a Likert score > 4

We'll use an LLM-based approach, modeling [this experiment](../create_llm_features_2026_08_05/), as relying on BERTopic for a sample size of ...


## How we can mine text for features

See [HOW_TO_MINE_FOR_TEXT_FEATURES](https://github.com/METResearchGroup/lab_knowledge_base/blob/main/docs/runbooks/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md) and [HOW_TO_CLUSTER_TEXT](https://github.com/METResearchGroup/lab_knowledge_base/blob/main/docs/runbooks/methods/HOW_TO_CLUSTER_TEXT.md).
