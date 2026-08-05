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

### Part 1: Graphing the distribution of the Likert scores

We graph the distribution of Likert scores, in `part_1_histogram`.

### Part 2: Mining free responses

We store the work for Part 2 in `part_2_mine_free_responses`.

We'll actually split out analysis into two parts:

- Users who gave a Likert score < 4 (we'll call this the `low` group)
- Users who gave a Likert score >= 4 (we'll call this the `high` group)

| Group | n |
| --- | ---: |
| Total users with free response + Likert | 1177 |
| Likert < 4 | 255 |
| Likert >= 4 | 922 |

We'll use an LLM-based approach, modeling [this experiment](../create_llm_features_2026_08_05/), as relying on BERTopic for a relatively small sample size might prove to be noisy.

Just like in our previous experiment, our approach is something like:

1. Give an LLM bunches of documents all at once and then ask it to generate features.
2. Get a semantic embedding of each generated feature.
3. Cluster the semantic embeddings.
4. Ask a language model to give a name/label for each cluster, by giving it a random sample of documents from the cluster.

We'll run this in a pipeline-like approach.

We have the following Python files, in src/

- llm_generate_features.py # uses the `runner` from research_tools
- generate_embeddings.py
- cluster_embeddings.py
- generate_labels_for_embeddings.py # uses the `runner` from research_tools

We store our results in outputs/, as

- generated_features/{low,high}
- generated_embeddings/{low,high}
- clusters/{low,high}
- generated_labels/{low,high}

We use `gpt5.4-nano` for our LLM. We use Amazon Titan for the embeddings (`shared/embeddings/bedrock.py`: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized). We generate the embeddings from scratch and key on the user ID (TODO: check if this is the best choice for ID).

## How we can mine text for features

See [HOW_TO_MINE_FOR_TEXT_FEATURES](https://github.com/METResearchGroup/lab_knowledge_base/blob/main/docs/runbooks/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md) and [HOW_TO_CLUSTER_TEXT](https://github.com/METResearchGroup/lab_knowledge_base/blob/main/docs/runbooks/methods/HOW_TO_CLUSTER_TEXT.md).
