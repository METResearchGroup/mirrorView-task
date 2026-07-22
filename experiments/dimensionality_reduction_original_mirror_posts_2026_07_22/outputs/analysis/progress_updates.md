## Build analysis table (original + mirror long)

- Posts: `8791` from PKR `Dataloader().load_training_dataframe()`
- Feature set: `original_and_mirror_long` / Titan `amazon.titan-embed-text-v2:0` dims=256
- Embedding cache: `/Users/mark/src/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/embedding_cache` (local `.npy` only; AWS not called)
- Cache hits=17582 misses=0
- Artifacts:
  - `/Users/mark/src/work/mirrorView-task/experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/analysis_table.parquet` — scalars + `embedding` list; rows=17582
  - `/Users/mark/src/work/mirrorView-task/experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/X_original_and_mirror.npy` — shape `(17582, 256)`
  - `/Users/mark/src/work/mirrorView-task/experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/analysis_meta.csv` — `post_id,text_role,is_mirrored,label`
  - `/Users/mark/src/work/mirrorView-task/experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/analysis_table_meta.json`

## Single shared post-level train/test split

- Seed=42, train_split=0.8, stratify_on=`label`
- lda_target=`is_mirrored` (not used for split)
- Artifact: `/Users/mark/src/work/mirrorView-task/experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/split_ids.json`
- n_posts_total=8791 n_train=7032 n_test=1759
- n_rows_train=14064 n_rows_test=3518 (exactly 2× post counts)
- Disjoint: train ∩ test post_ids = ∅; each post contributes both roles to one split
- Convenience join: `/Users/mark/src/work/mirrorView-task/experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/outputs/analysis/analysis_with_split.csv`
- Downstream agents must load these IDs; do **not** re-split.

