## 2026-07-16 02:40:16 UTC — cluster investigation start

- Shared split: `outputs/analysis/split_ids.json` (no re-split)
- Features: `outputs/analysis/X_only_original.npy`
- No Bedrock calls.

## 2026-07-16 02:40:16 UTC — PCA fit (train only)

- n_components=20 (target cumvar>=0.5, clip [10,20])
- cum explained variance (train)=0.2585
- PC1/PC2 for viz: [0.028978916958255545, 0.021471349392434145]

## 2026-07-16 02:40:19 UTC — k selection

- k range=[5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]; selected_k=7
- silhouette@k: k=5:0.0928, k=6:0.0935, k=7:0.0954, k=8:0.0929, k=9:0.0863, k=10:0.0851, k=11:0.0852, k=12:0.0860, k=13:0.0875, k=14:0.0835, k=15:0.0839

## 2026-07-16 02:40:37 UTC — cluster investigation (rerun log)

- Shared split: `outputs/analysis/split_ids.json` (no re-split)
- Features: `outputs/analysis/X_only_original.npy`
- No Bedrock calls.

## 2026-07-16 02:40:37 UTC — PCA fit (train only)

- n_components=20 (target cumvar>=0.5, clip [10,20])
- cum explained variance (train)=0.2585
- PC1/PC2 for viz: [0.028978916958255545, 0.021471349392434145]

## 2026-07-16 02:40:39 UTC — k selection

- k range=[5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]; selected_k=7
- silhouette@k: k=5:0.0928, k=6:0.0935, k=7:0.0954, k=8:0.0929, k=9:0.0863, k=10:0.0851, k=11:0.0852, k=12:0.0860, k=13:0.0875, k=14:0.0835, k=15:0.0839

## 2026-07-16 02:40:41 UTC — results

- selected_k=7 train_silhouette=0.0954
- stability pairwise ARI mean=0.9704099777293932
- max_test_lift=1.1210778092963074 min_test_lift=0.7734265025807278
- decision_gate **diffuse**: No cluster with stable test enrichment or sparse-error island (criteria: test n>=15, |train−test rate|<=0.08, lift>=1.25 or <=0.7). Conclude errors are diffuse in Titan PCA space.
- 256d sanity max_test_lift=1.1422619150742364 min_test_lift=0.8045258199921905

## 2026-07-16 02:40:41 UTC — artifacts

- `outputs/analysis/clusters/cluster_assignments.csv`
- `outputs/analysis/clusters/cluster_metrics.json`
- `outputs/analysis/clusters/cluster_lift_table.csv`
- `outputs/analysis/clusters/k_selection.json`
- `outputs/analysis/clusters/pca2d_by_cluster.png`
- `outputs/analysis/clusters/cluster_exemplars.md`
- `outputs/analysis/clusters/kmeans_pca_model.joblib`

- Status: **complete** (no Bedrock; shared split only)
