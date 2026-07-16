# outputs/analysis/clusters/

Reduced-space clustering of Qwen right/wrong in Titan PCA space (train-fit PCA-20 → k-means; shared split). Decision gate: diffuse (no stable high-lift / low-error islands).

**Most important files**

- `cluster_metrics.json` / `cluster_lift_table.csv` — per-cluster rates and lifts
- `pca2d_by_cluster.png` — core cluster plot
- `cluster_exemplars.md` — spot-check texts
- `k_selection.json` — silhouette vs k

| filename | description of what it’s for |
| --- | --- |
| `cluster_assignments.csv` | `post_id` → cluster id, split, error flag, PCA coords |
| `cluster_metrics.json` | Full clustering metrics + decision-gate verdict |
| `cluster_lift_table.csv` | Per-cluster n / error rate / lift (train & test) |
| `k_selection.json` | Silhouette scores over k and selected k |
| `pca2d_by_cluster.png` | PCA 2D colored by cluster assignment |
| `cluster_exemplars.md` | Human-readable exemplar posts for interesting clusters |
| `cluster_exemplars.csv` | Tabular exemplars |
| `kmeans_pca_model.joblib` | Fitted scaler / PCA / k-means pipeline |
| `progress_updates.md` | Clustering run log |
| `README.md` | This folder index |
