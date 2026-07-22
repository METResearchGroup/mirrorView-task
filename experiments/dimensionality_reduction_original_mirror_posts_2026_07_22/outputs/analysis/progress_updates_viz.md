## 2026-07-22 15:14:45 — 2D reduction start

- Loading `X_original_and_mirror.npy`, `analysis_meta.csv`
- Fit on all rows; no train/test split; no Bedrock; LDA target = is_mirrored.

## 2026-07-22 15:14:45 — fit reductions (all rows)

- n_rows=17582 n_posts=8791 dim=256
- StandardScaler → PCA(2) → LDA(1; y=is_mirrored) + residual PCA(1)

## 2026-07-22 15:14:46 — artifacts written

- PCA plot: `pca_original_vs_mirrored.png` (single panel)
- LDA plot: `lda_original_vs_mirrored.png` (single panel)
- Coords: `embeddings_2d.csv` (17582 rows)
- Summary: `reduction_summary.json`, `pca_variance_explained.json`
- PCA var: PC1=2.90%, PC2=2.10% (cumsum=5.00%)
- PCA-plane 2D-logistic acc (viz overlay only): 0.623
- LDA LD1 Cohen-d (mirrored−original): 1.511; midpoint thr acc=0.776
