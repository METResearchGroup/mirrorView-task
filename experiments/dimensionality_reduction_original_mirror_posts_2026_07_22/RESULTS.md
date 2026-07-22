# Results: original vs mirrored Titan PCA/LDA

**Experiment:** `experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/`  
**Date:** 2026-07-22  
**Cache:** worktree `experiments/predict_keep_remove_2026_07_01/embedding_cache/` (local `.npy` only; no S3/Bedrock)

## Cohort

| Field | Value |
|-------|-------|
| n_posts | 8,791 |
| n_rows (2N) | 17,582 |
| Fit | all rows (no train/test split) |
| LDA target | `is_mirrored` |

## PCA (fit on all rows)

| Metric | Value |
|--------|-------|
| PC1 explained variance | 2.90% |
| PC2 explained variance | 2.10% |
| PC1+PC2 cumsum | 5.00% |
| PCA-plane 2D logistic accuracy (`is_mirrored`) | 0.623 |

Unsupervised PC1/PC2 capture little of 256-d Titan variance (expected). Original vs mirrored still overlap substantially in the PC plane (~62% 2D-logistic acc).

## LDA (target=`is_mirrored`, fit on all rows)

| Metric | Value |
|--------|-------|
| Cohen-d (mirrored − original) | **1.511** |
| Midpoint-threshold accuracy | **0.776** |

Original vs mirrored is a **strong** linear axis in Titan space — much stronger than the prior Qwen right/wrong LDA (~0.33 Cohen-d). Midpoint accuracy ~78% on the full cohort.

## Artifacts

- [`outputs/analysis/pca_original_vs_mirrored.png`](outputs/analysis/pca_original_vs_mirrored.png) — single panel
- [`outputs/analysis/lda_original_vs_mirrored.png`](outputs/analysis/lda_original_vs_mirrored.png) — single panel
- [`outputs/analysis/embeddings_2d.csv`](outputs/analysis/embeddings_2d.csv)
- [`outputs/analysis/reduction_summary.json`](outputs/analysis/reduction_summary.json)
- [`outputs/analysis/pca_variance_explained.json`](outputs/analysis/pca_variance_explained.json)

## Interpretation

Mirrors systematically shift Titan embedding geometry along a recoverable linear direction, even though unsupervised PCA of the stacked matrix shows heavy overlap. Stance/paraphrase flips are linearly separable at ~1.5σ class-mean separation on LD1; this does **not** imply keep/remove separability.
