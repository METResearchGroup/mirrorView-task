# Results: original vs mirrored Titan PCA/LDA

**Experiment:** `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/`  
**Date:** 2026-07-22  
**Cache:** worktree `experiments/predict_keep_remove_2026_07_01/embedding_cache/` (local `.npy` only; no S3/Bedrock)

## Cohort

| Field | Value |
|-------|-------|
| n_posts | 8,791 |
| n_rows (2N) | 17,582 |
| n_train posts / rows | 7,032 / 14,064 |
| n_test posts / rows | 1,759 / 3,518 |
| Split | seed=42, 80/20, stratify on keep/remove `label` |
| LDA target | `is_mirrored` |

## PCA (train-fit)

| Metric | Value |
|--------|-------|
| PC1 explained variance | 2.91% |
| PC2 explained variance | 2.11% |
| PC1+PC2 cumsum | 5.02% |
| PCA-plane 2D logistic test accuracy (`is_mirrored`) | 0.625 |

Unsupervised PC1/PC2 capture little of 256-d Titan variance (expected). Original vs mirrored still overlap substantially in the PC plane (~62% 2D-logistic test acc).

## LDA (target=`is_mirrored`, train-fit)

| Metric | Value |
|--------|-------|
| Test Cohen-d (mirrored − original) | **1.480** |
| Test midpoint-threshold accuracy | **0.763** |
| Train Cohen-d | 1.512 |
| Train midpoint-threshold accuracy | 0.777 |

Original vs mirrored is a **strong** linear axis in Titan space — much stronger than the prior Qwen right/wrong LDA (~0.33 Cohen-d). Out-of-sample midpoint accuracy ~76% on held-out posts.

## Artifacts

- [`outputs/analysis/pca_original_vs_mirrored.png`](outputs/analysis/pca_original_vs_mirrored.png)
- [`outputs/analysis/lda_original_vs_mirrored.png`](outputs/analysis/lda_original_vs_mirrored.png)
- [`outputs/analysis/embeddings_2d.csv`](outputs/analysis/embeddings_2d.csv)
- [`outputs/analysis/reduction_summary.json`](outputs/analysis/reduction_summary.json)
- [`outputs/analysis/pca_variance_explained.json`](outputs/analysis/pca_variance_explained.json)

## Interpretation

Mirrors systematically shift Titan embedding geometry along a recoverable linear direction, even though unsupervised PCA of the stacked matrix shows heavy overlap. Stance/paraphrase flips are linearly separable at ~1.5σ class-mean separation on LD1; this does **not** imply keep/remove separability.
