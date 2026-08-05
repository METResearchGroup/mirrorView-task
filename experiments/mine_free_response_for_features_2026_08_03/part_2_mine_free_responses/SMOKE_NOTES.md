# Part 2 smoke notes (approval gate)

**Date:** 2026-08-05  
**Status:** Smoke complete — approved; production documented in `RESULTS.md`  
**Do not treat as production RESULTS.**

## Smoke settings

| Setting | Low | High |
| ------- | --- | ---- |
| Stage-1 sample size | 10 | 20 (seed 43; first seed-42 / n=10 smoke had 8 features, all HDBSCAN noise) |
| Docs per batch | 10 | 10 |
| Seed | 42 | 43 (Stage 1); Stage 2–4 seed 42 |
| Feature-gen batches | 1 | 2 |
| Features embedded | 7 | 16 |
| Stage-3 `min_cluster_size` | 5 (auto-lowered to 2 for n&lt;20) | **2** (explicit; default 5 left all 16 points as noise) |

## Artifact paths

### Low

| Stage | Path |
| ----- | ---- |
| 1 | `outputs/generated_features/low/outputs/2026_08_05-21:06:44.456706` |
| 2 | `outputs/generated_embeddings/low/2026-08-05T21-07-12` |
| 3 | `outputs/clusters/low/2026-08-05T21-07-26` |
| 4 | `outputs/generated_labels/low/outputs/2026_08_05-21:08:20.328434` |

HDBSCAN: 3 clusters, 0 noise. KMeans k=3 (comparison).

### High

| Stage | Path |
| ----- | ---- |
| 1 | `outputs/generated_features/high/outputs/2026_08_05-21:07:43.484931` |
| 2 | `outputs/generated_embeddings/high/2026-08-05T21-07-58` |
| 3 | `outputs/clusters/high/2026-08-05T21-08-17` |
| 4 | `outputs/generated_labels/high/outputs/2026_08_05-21:08:33.354578` |

HDBSCAN: 2 clusters, 4 noise. KMeans k=2 (comparison).

## Class-root PNGs

- `outputs/clusters/low/cluster_hdbscan.png`
- `outputs/clusters/low/cluster_kmeans.png`
- `outputs/clusters/high/cluster_hdbscan.png`
- `outputs/clusters/high/cluster_kmeans.png`

## Sample HDBSCAN labels

### Low

| cluster_id | n | label |
| ---------: | -: | ----- |
| 0 | 3 | Free speech permissive removal |
| 1 | 2 | Content screened via harm and explicit threats |
| 2 | 2 | Impartial debate-quality evaluation |

### High

| cluster_id | n | label |
| ---------: | -: | ----- |
| 0 | 10 | Civility and non-abusive content filter |
| 1 | 2 | Preference for factual, non-emotive content |

## Checklist

1. Stage-1 dirs for low and high: yes  
2. Stage-2 `embeddings.npy` + `features.jsonl` + `feature_ids.json`: yes  
3. Stage-3 assignments + class-root PNGs (both methods, both groups): yes  
4. Stage-4 labels for non-noise HDBSCAN clusters: yes  
5. Approved; production full-corpus run + `RESULTS.md` completed separately
