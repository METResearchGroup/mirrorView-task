# outputs/analysis/

Joined Qwen labels + original-post Titan features, shared train/test split, linear separator, and 2D PCA/LDA visualizations. Nested `clusters/` holds reduced-space clustering.

**Most important files**

- `analysis_table.parquet` / `X_only_original.npy` — features + labels
- `split_ids.json` — shared train/test IDs
- `linear_separator_metrics.json` — logistic probe metrics
- `pca_right_vs_wrong.png`, `lda_right_vs_wrong.png` — core 2D plots
- `clusters/` — clustering lift / exemplars

| filename | description of what it’s for |
| --- | --- |
| `analysis_table.parquet` | Joined table: labels + 256-d `only_original` embeddings |
| `analysis_table_meta.json` | Loader / cache metadata for the analysis table |
| `analysis_meta.csv` | Scalar columns only (`post_id`, `label`, `is_correct`, `is_error`) |
| `analysis_with_split.csv` | Convenience join of meta + `train`/`test` split |
| `X_only_original.npy` | Dense `(8791, 256)` Titan feature matrix |
| `split_ids.json` | Stratified shared train/test post IDs (`seed=42`) |
| `linear_separator_metrics.json` | Train/test logistic metrics (primary) |
| `logistic_metrics.json` | Alias of `linear_separator_metrics.json` |
| `linear_separator_model.joblib` | Fitted `StandardScaler` + balanced logistic pipeline |
| `linear_separator_coefficients.csv` | Per-dimension logistic coefficients |
| `linear_separator_predictions.csv` | Per-post train/test predictions / scores |
| `pca_right_vs_wrong.png` | Primary PCA scatter (right vs wrong) |
| `pca_scatter.png` | Alias of the PCA plot |
| `lda_right_vs_wrong.png` | Primary LDA scatter (right vs wrong) |
| `lda_scatter.png` | Alias of the LDA plot |
| `embeddings_2d.csv` | Per-post PC1/PC2 / LD coords + split labels |
| `reduction_summary.json` | PCA/LDA numeric summary + artifact paths |
| `pca_variance_explained.json` | PC1/PC2 explained variance |
| `progress_updates.md` | Data-prep / split progress log |
| `progress_updates_train.md` | Linear separator training progress log |
| `progress_updates_viz.md` | 2D reduction progress log |
| `clusters/` | Reduced-space clustering artifacts (see nested README) |
| `README.md` | This folder index |
