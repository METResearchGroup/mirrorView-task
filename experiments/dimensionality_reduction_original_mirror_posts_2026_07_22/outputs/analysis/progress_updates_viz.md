## 2026-07-22 12:40:42 — 2D reduction start

- Loading `X_original_and_mirror.npy`, `analysis_meta.csv`, `split_ids.json`
- No re-split; no Bedrock; LDA target = is_mirrored.

## 2026-07-22 12:40:42 — fit reductions (train only)

- n_train_rows=14064 n_test_rows=3518 dim=256
- StandardScaler → PCA(2) → LDA(1; y=is_mirrored) + residual PCA(1)

## 2026-07-22 12:40:43 — artifacts written

- PCA plot: `pca_original_vs_mirrored.png`
- LDA plot: `lda_original_vs_mirrored.png`
- Coords: `embeddings_2d.csv` (17582 rows)
- Summary: `reduction_summary.json`, `pca_variance_explained.json`
- PCA var: PC1=2.91%, PC2=2.11% (cumsum=5.02%)
- PCA-plane 2D-logistic test acc (viz overlay only): 0.625
- LDA test LD1 Cohen-d (mirrored−original): 1.480; midpoint thr acc=0.763

