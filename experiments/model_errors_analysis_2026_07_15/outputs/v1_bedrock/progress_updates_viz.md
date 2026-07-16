# V1.3B progress — 2D PCA / LDA visualization

## 2026-07-15 21:04 CDT — kickoff

- Spec V1.3B: standardize → PCA(2D) + LDA (binary → 1 discriminant; project sensibly) fit on **train only**, transform train+test.
- Will load existing `split_ids.json` (seed=42, train=7032, test=1759) — **no re-split**.
- Features: `X_only_original.npy` (256-d Titan).
- Color/label by right vs wrong (`is_correct` / `is_error`).
- Will **not** train logistic (V1.3A) or call Bedrock.
- Own progress file only (`progress_updates_viz.md`); not touching `progress_updates.md`.
## 2026-07-15 21:05:53 — V1.3B start

- Loading `X_only_original.npy`, `analysis_meta.csv`, `split_ids.json`
- No re-split; no Bedrock; no 256-d logistic (V1.3A owns that).

## 2026-07-15 21:05:53 — fit reductions (train only)

- n_train=7032 n_test=1759 dim=256
- StandardScaler → PCA(2) → LDA(1) + residual PCA(1) for LDA y-axis

## 2026-07-15 21:05:55 — artifacts written

- PCA plot: `pca_right_vs_wrong.png` / `pca_scatter.png`
- LDA plot: `lda_right_vs_wrong.png` / `lda_scatter.png`
- Coords: `embeddings_2d.csv` (8791 rows)
- Summary: `reduction_summary.json`, `pca_variance_explained.json`
- PCA var: PC1=2.90%, PC2=2.15% (cumsum=5.05%)
- PCA-plane 2D-logistic test acc (viz overlay only): 0.562
- LDA test LD1 Cohen-d (wrong−correct): 0.329; midpoint thr acc=0.567

### Visual separability (brief)

- PCA: first two PCs capture limited variance of 256-d Titan; right/wrong clouds are heavily overlapping in the PC plane (see test 2D-logistic acc near chance if low).
- LDA: supervised 1D projection maximizes class separation on **train**; test Cohen-d / midpoint accuracy indicate how much of that linear structure holds out-of-sample.


## 2026-07-15 21:06 — V1.3B complete

- Status: done. Leakage-safe fit-on-train / transform-all.
- Issues: none. Did not touch split, Bedrock, or V1.3A progress/metrics.
- Takeaway: PCA plane shows almost no right/wrong structure (~5% variance, ~0.56 2D-logistic test acc). LDA LD1 shows mild train separation (d≈0.56) that shrinks on test (d≈0.33, midpoint acc≈0.57) — weak but nonzero linear signal along the supervised axis.
