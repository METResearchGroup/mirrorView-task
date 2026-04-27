# AI Suggested Analysis

This document captures suggested content-analysis metrics for comparing:

1. Base texts vs mirrored texts in aggregate
2. Per-pair differences between `(base_text, mirror_text)`
3. How those features relate to `keep` vs `remove` decisions

---

## Overall analysis structure

For each metric, compute:

- `base_metric`: score on base text
- `mirror_metric`: score on mirrored text
- `delta_metric`: `mirror_metric - base_metric` (or ratio if more interpretable)
- `pair_similarity_metric` when applicable (e.g., embeddings, lexical overlap)

Then analyze each metric in three lenses:

- **Aggregate lens**: compare base distribution vs mirror distribution
- **Pairwise lens**: compare within-pair differences
- **Behavioral lens**: compare metric values for `keep` vs `remove`

---

## 10 suggested analyses

### 1) Length and compression

Metrics:

- Character count
- Word count
- Sentence count
- Avg sentence length
- Punctuation density

Questions:

- Aggregate: are mirrored texts longer/shorter/denser?
- Pairwise: what is the distribution of length ratios and absolute differences?
- Keep/remove: are longer or more compressed texts more likely to be removed?

### 2) Readability and linguistic complexity

Metrics:

- Flesch-Kincaid grade level
- Reading ease
- Avg word length
- Type-token ratio (or moving-average TTR)
- Clause/subordination proxies (if available)

Questions:

- Aggregate: do mirrors become simpler or more formal?
- Pairwise: does readability shift systematically from base to mirror?
- Keep/remove: is complexity related to moderation outcomes?

### 3) Sentiment and affect

Metrics:

- Polarity (positive/negative/neutral)
- Valence and subjectivity
- Emotion dimensions (anger, fear, disgust, sadness, etc.)

Questions:

- Aggregate: is emotional tone amplified or dampened in mirrors?
- Pairwise: how large is the affect shift per pair?
- Keep/remove: do higher negative/anger levels associate with removal?

### 4) Toxicity / incivility / harassment

Metrics:

- Toxicity score
- Insult/profanity flags
- Threat/severe toxicity sub-scores (if tool supports this)

Questions:

- Aggregate: are toxicity levels preserved between base and mirror?
- Pairwise: where are the biggest toxicity deltas?
- Keep/remove: is toxicity one of the strongest predictors of `remove`?

### 5) Moralized language / normative framing

Metrics:

- Counts/density for moral vocabulary (rights, duty, justice, freedom, purity, etc.)
- Optional classifier-based moral foundation dimensions

Questions:

- Aggregate: do mirrors preserve moral framing intensity?
- Pairwise: which moral dimensions increase/decrease?
- Keep/remove: does stronger moralization correlate with removal?

### 6) Certainty, absolutism, and hedging

Metrics:

- Absolutist word rates (always, never, everyone, no one)
- Certainty markers (clearly, definitely, must)
- Hedging markers (might, maybe, perhaps, could)

Questions:

- Aggregate: do mirrors become more assertive or more hedged?
- Pairwise: what is the certainty shift per pair?
- Keep/remove: does absolutist or high-certainty language predict moderation decisions?

### 7) Identity-group and outgroup references

Metrics:

- Mentions of identity/political groups
- Outgroup-targeting indicators
- Ingroup/outgroup balance

Questions:

- Aggregate: are identity-group references more explicit in mirrors?
- Pairwise: which group references are added/dropped/swapped?
- Keep/remove: do explicit group-targeting features increase removal rates?

### 8) Topic and frame preservation

Metrics:

- Topic labels/distributions (embedding clustering or topic model)
- Keyphrase overlap in issue framing
- Frame-shift indicators

Questions:

- Aggregate: do base and mirror sets occupy similar topic distributions?
- Pairwise: does each mirror stay on the same issue frame as the base?
- Keep/remove: are frame shifts associated with moderation outcomes?

### 9) Lexical/syntactic overlap and paraphrase preservation

Metrics:

- Token overlap (Jaccard)
- N-gram overlap (ROUGE-style)
- Optional semantic overlap (BERTScore or equivalent)
- Optional shallow syntax overlap

Questions:

- Aggregate: how much surface-form structure is preserved overall?
- Pairwise: which pairs are low-preservation outliers?
- Keep/remove: do low-preservation mirrors get different moderation outcomes?

### 10) Embedding similarity and semantic distance

Metrics:

- Embeddings for base and mirror texts
- Cosine similarity / distance per pair
- Cluster membership and outlier scores

Questions:

- Aggregate: do base and mirror embeddings inhabit similar semantic regions?
- Pairwise: what is semantic similarity distribution across pairs?
- Keep/remove: are low-similarity pairs more likely to be removed?

---

## Recommended first-pass subset (fast + high value)

If you want a focused MVP before running all ten:

1. Length/compression
2. Readability
3. Toxicity/incivility
4. Lexical/paraphrase overlap
5. Embedding cosine similarity

This gives a strong combination of structural, interpretive, and semantic metrics with manageable implementation effort.

---

## Suggested output tables and plots

For each metric family, produce:

- **Summary table**: base mean, mirror mean, mean delta, paired significance test
- **Distribution plots**: base vs mirror histograms/densities
- **Pairwise plots**: scatter (`base_metric` vs `mirror_metric`) and delta histogram
- **Decision split plots**: metric distributions by `keep` vs `remove`
- **Outlier table**: top N pairs with largest deltas / smallest similarities

These outputs should be generated both overall and stratified by relevant metadata (e.g., phase, condition, sampled stance, toxicity bucket).
