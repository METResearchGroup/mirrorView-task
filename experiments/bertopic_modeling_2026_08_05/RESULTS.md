# BERTopic modeling results (original posts)

**Date:** 2026-08-05  
**Status:** Complete (production)

Smoke (`--sample-size 50`, seed 42) was run and reviewed before this full-corpus production run.

## Setup

| Item | Value |
|------|-------|
| Dataset | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` (~8791 modal posts) |
| Text role | `original` |
| Embeddings | Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`), 256-d, L2-normalized |
| Embedding cache | `outputs/embeddings/original/` — **8790** rows; **1** dropped (`bluesky_0650663eb2486d20261d5debdaff1b48272d35a79c26d4a8b93b793090039d79`) |
| Fit | BERTopic with `embedding_model=None`; embeddings passed into `fit_transform` |
| UMAP (fit) | `n_neighbors=15`, `n_components=5`, `min_dist=0.0`, `metric=cosine`, `random_state=42` |
| HDBSCAN | `min_cluster_size=15`, `metric=euclidean`, `cluster_selection_method=eom`, `prediction_data=True` |
| CountVectorizer | `stop_words=english`, `min_df=2` |
| Soft probs | `calculate_probabilities=True` |
| LLM labels | `gpt-5.4-nano` via `bertopic.representation.OpenAI` (post-hoc `update_topics`); noise topic `-1` skipped |
| Unanimous rule | `all_linked_fate_raters_same_decision` (overlays only; not used in fit) |

Keep/remove and unanimous labels are visualization overlays only.

## Production counts

| Metric | Value |
|--------|------:|
| Documents fitted | 8790 |
| Topics (excl. noise) | 53 |
| Noise (topic −1) | 3030 |
| Topics LLM-labeled | 53 |

## Artifact runs

| Stage | Path |
|-------|------|
| Embeddings | `experiments/bertopic_modeling_2026_08_05/outputs/embeddings/original/` |
| Topics | `experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/` |
| Labels | `experiments/bertopic_modeling_2026_08_05/outputs/labels/original/20260805T140017Z/` |
| Figures | `experiments/bertopic_modeling_2026_08_05/outputs/figures/original/20260805T140030Z/` |

### Figures

- `outputs/figures/original/20260805T140030Z/clusters_by_topic.{html,png}`
- `outputs/figures/original/20260805T140030Z/clusters_by_keep_remove.{html,png}`
- `outputs/figures/original/20260805T140030Z/clusters_by_unanimous.{html,png}`

### Smoke (pre-approval)

| Stage | Path |
|-------|------|
| Topics | `outputs/topics/original/20260805T135453Z/` (`sample_size=50`) |
| Labels | `outputs/labels/original/20260805T135735Z/` |
| Figures | `outputs/figures/original/20260805T135746Z/` |

## Sample topic labels (largest topics)

| topic_id | n_docs | llm_label |
|---------:|-------:|-----------|
| 0 | 1586 | Debate over U.S. gun rights and gun control (Second Amendment, NRA, and violence) |
| 1 | 947 | Climate policy and energy transition amid global crisis |
| 2 | 210 | Criticism of MAGA and related political beliefs |
| 3 | 201 | Criticism of Democrats vs Republicans (DNC/MAGA) and claims of dishonesty and weak agendas |
| 4 | 200 | Criticism of Republicans and GOP policies/actions |
| 5 | 179 | Deportation and illegal immigration debate |

Full table: `outputs/labels/original/20260805T140017Z/topic_labels.parquet`.
