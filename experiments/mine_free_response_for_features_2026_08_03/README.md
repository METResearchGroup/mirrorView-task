# Mining free responses for features

## Motivation

During the second phase of our study in part 2, we asked users to leave free response and survey feedback related to what information they used to determine their keep versus remove decisions.

## Background

In Phase 2, Part 2, we asked users to rate 20 posts in the linked fate condition. We then asked them the following:

- Free response (phase1_pair_reflection_text): what was going through their mind; what influenced evaluating posts as a pair.
- 1–7 Likert (phase1_pair_influence_rating): how much seeing both versions influenced decisions (1 = Not at all, 7 = Very much).

We can take their free responses and mine them for insights.

## Proposed solution

1. Histogram: what was the distribution of the Likert scores?
2. Mine the free responses for features (we have some details on this in `experiments/create_llm_feature_clusters_2026_08_02/PLAN.md`). We filter for users whose Likert score was >= 4.

## How we want to mine for free responses

### Approach 1: Classic extraction methods

Some classic methods for extracting features from free responses include:

- Document frequency: ...
- Bag-of-words: ...

While doing this, some things to consider include:

- Lemmatize
- Remove stopwords and "unimportant words".
- Basic synonym merging

We want to avoid TF-IDF here actually as we want to maximize term frequency, which is corrected for in TF-IDF.

Another axis to explore is unigram vs. bigram vs. n-gram for extraction. Unigrams work OK as a start if you've done some basic cleaning as noted above.

### Approach 2: Clustering

The con with this is if people cite multiple reasons in one. For example:

- "The level of vulgarity or the inappropriate writing style (e.g., ALL CAPS)."
- "The malice and lack of real thought behind the post"

These two examples show multiple reasons...

To counteract these .... (TODO: come up with something).

#### Clustering algorithms to explore

BERTopic ...

K-means...

Hierarchical clustering...

### Combining generated features using an LLM

Whether you use classical methods or clustering to get groups of possible features, the next step is using an LLM. The LLM can be tasked with taking the groups and creating a label for it.

A prompt can be something like:

```markdown
{SYSTEM PROMPT}

Group 1:
{Group 1}

Group 2:
{Group 2}

...
```

The system prompt can be something like:

```markdown

```
