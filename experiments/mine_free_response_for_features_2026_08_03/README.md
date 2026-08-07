# Mining free responses for features

## Motivation

In Phase 2 Part 2 of the study, we asked users for free-response and survey feedback about what information they used when they chose keep or remove.

## Background

In Phase 2 Part 2, we asked users to rate 20 posts in the linked fate condition. We then asked them the following:

- Free response (`phase1_pair_reflection_text`): what was going through their mind, and what influenced evaluating posts as a pair.
- 1 to 7 Likert (`phase1_pair_influence_rating`): how much seeing both versions influenced decisions (1 = Not at all, 7 = Very much).

We can take their free responses and mine them for insights.

## Proposed solution

1. Histogram: what was the distribution of the Likert scores?
2. Mine the free responses for features. Some details for that approach live in `experiments/create_llm_feature_clusters_2026_08_02/PLAN.md`.

### Part 1: Graphing the distribution of the Likert scores

We graph the distribution of Likert scores in `part_1_histogram`.

### Part 2: Mining free responses

We store the work for Part 2 in `part_2_mine_free_responses`.

We split the analysis into two groups:

- Users who gave a Likert score &lt; 4 (the `low` group)
- Users who gave a Likert score &gt;= 4 (the `high` group)

| Group | n |
| --- | ---: |
| Total users with free response + Likert | 1177 |
| Likert &lt; 4 | 255 |
| Likert &gt;= 4 | 922 |

We use an LLM-based approach, following `experiments/create_llm_features_2026_08_05/`, because BERTopic on a relatively small sample can be noisy.

The pipeline is:

1. Give an LLM batches of documents and ask it to generate features.
2. Get a semantic embedding of each generated feature.
3. Cluster the semantic embeddings.
4. Ask a language model to name each cluster from a random sample of features in the cluster.

The Python files in `src/` are:

- `llm_generate_features.py` (uses the `runner` from `research_tools`)
- `generate_embeddings.py`
- `cluster_embeddings.py`
- `generate_labels_for_embeddings.py` (uses the `runner` from `research_tools`)
- `compact_generate_features.py` (one-off: collapses Stage 1 per-batch `NNNNN_*.json` files into `batches.jsonl`)

Results live under `outputs/` as:

- `generated_features/{low,high}`
- `generated_embeddings/{low,high}`
- `clusters/{low,high}`
- `generated_labels/{low,high}`

We use `gpt-5.4-nano` for the LLM. We use Amazon Titan for embeddings (`shared/embeddings/bedrock.py`: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized). We generate the embeddings from scratch and key on the user ID (TODO: check if this is the best choice for ID).

## How we can mine text for features

See [HOW_TO_MINE_FOR_TEXT_FEATURES](https://github.com/METResearchGroup/lab_knowledge_base/blob/main/docs/runbooks/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md) and [HOW_TO_CLUSTER_TEXT](https://github.com/METResearchGroup/lab_knowledge_base/blob/main/docs/runbooks/methods/HOW_TO_CLUSTER_TEXT.md).
