# Part 2 free-response feature mining — production results

**Date:** 2026-08-05  
**Status:** Complete  
**Seed:** 42  
**Sample:** full usable corpus — **255 low** + **922 high** reflection rows (Likert-split user reflection feedback)  
**Smoke approval:** Step-6 smoke was explicitly approved before this production run.

## Budget

| Quantity | Value |
| -------- | ----- |
| Docs per feature-gen prompt | 10 |
| Low feature-gen prompts | **25** (5 leftover participant ids recorded, not sent) |
| High feature-gen prompts | **92** (2 leftover participant ids recorded, not sent) |
| Max features per prompt | 8 |
| Features embedded (actual) | **916** (189 low + 727 high) |
| Stage-1 QA rejected batches | **0** (all batches `usable`) |

## Models and methods

- LLM: `gpt-5.4-nano` (feature generation + HDBSCAN cluster labeling via `research_tools` runner)
- Embeddings: `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized (`shared/embeddings/bedrock.py`); embeds **feature** texts (`{name}: {value}. {rationale}`), not raw reflections
- Clustering: **both** HDBSCAN and KMeans; **labels / tables below use HDBSCAN only**; KMeans is comparison-only
- HDBSCAN noise policy: skip `cluster_id=-1` for labeling; noise counts recorded below
- HDBSCAN params (production): `min_cluster_size=5`, `min_samples=5`, `metric=euclidean`

## Cluster comparison PNGs

- `experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/clusters/low/cluster_hdbscan.png`
- `experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/clusters/low/cluster_kmeans.png`
- `experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/clusters/high/cluster_hdbscan.png`
- `experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/clusters/high/cluster_kmeans.png`

## Low

| Field | Value |
| ----- | ----- |
| Reflections sampled | 255 |
| Feature-gen batches | 25 (`leftover_participant_ids` length 5) |
| Features embedded | 189 |
| HDBSCAN clusters (excl. noise) | 2 |
| HDBSCAN noise | 103 (skipped for labeling) |
| KMeans selected \(k\) (comparison) | 2 |
| Stage-1 | `outputs/generated_features/low/outputs/2026_08_05-21:11:59.971897` |
| Stage-2 | `outputs/generated_embeddings/low/2026-08-05T21-14-34` |
| Stage-3 | `outputs/clusters/low/2026-08-05T21-15-11` |
| Stage-4 | `outputs/generated_labels/low/outputs/2026_08_05-21:15:16.139778` |

### Low HDBSCAN cluster labels

| cluster_id | n_members | cluster_label | definition |
| ---------: | --------: | ------------- | ---------- |
| 0 | 81 | Harm/toxicity thresholds within free speech | Participants set keep/remove boundaries based on specific harm, threats, violence, or dehumanizing/toxic language while treating ordinary strong opinions as permissible free speech. |
| 1 | 5 | Pair comparison barely influenced decisions | In these low-influence reflections, participants report keeping/removing based on general principles or per-post content quality rather than any meaningful comparison between the original and mirror pair. |

## High

| Field | Value |
| ----- | ----- |
| Reflections sampled | 922 |
| Feature-gen batches | 92 (`leftover_participant_ids` length 2) |
| Features embedded | 727 |
| HDBSCAN clusters (excl. noise) | 3 |
| HDBSCAN noise | 596 (skipped for labeling) |
| KMeans selected \(k\) (comparison) | 2 |
| Stage-1 | `outputs/generated_features/high/outputs/2026_08_05-21:15:29.337342` |
| Stage-2 | `outputs/generated_embeddings/high/2026-08-05T21-26-36` |
| Stage-3 | `outputs/clusters/high/2026-08-05T21-28-38` |
| Stage-4 | `outputs/generated_labels/high/outputs/2026_08_05-21:28:45.562172` |

### High HDBSCAN cluster labels

| cluster_id | n_members | cluster_label | definition |
| ---------: | --------: | ------------- | ---------- |
| 0 | 17 | Apply same moderation standard across both sides | Participants reported that seeing original-plus-mirror pairs helped them judge more consistently and fairly by applying identical moderation criteria regardless of political viewpoint. |
| 1 | 103 | Remove for threats and toxicity | High-influence reflections describe using a high bar for moderation that generally keeps opinions but removes posts when they become threatening, excessively vulgar, slanderous, or otherwise toxic/inflammatory. |
| 2 | 11 | Free speech with violence/threat exceptions | Participants endorse keeping most speech (including opposing opinions) while justifying removal only when content involves threats, intent to harm, or violence and sometimes closely related “bad language” or profanity. |

## Totals

| Metric | Value |
| ------ | ----- |
| Reflections | 1177 (255 low + 922 high) |
| Feature-gen prompts | 117 (25 + 92) |
| Features embedded | 916 |
| HDBSCAN clusters labeled | 5 (2 low + 3 high) |
| HDBSCAN noise skipped | 699 (103 low + 596 high) |
