## Build analysis table (original + mirror long)

- Posts: `8791` from PKR `Dataloader().load_training_dataframe()`
- Feature set: `original_and_mirror_long` / Titan `amazon.titan-embed-text-v2:0` dims=256
- Embedding cache: `/Users/mark/src/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/embedding_cache` (local `.npy` only; AWS not called)
- Cache hits=17582 misses=0
- Artifacts:
  - `analysis_table.parquet` — scalars + `embedding` list; rows=17582
  - `X_original_and_mirror.npy` — shape `(17582, 256)`
  - `analysis_meta.csv` — `post_id,text_role,is_mirrored,label`
  - `analysis_table_meta.json`

## Amendment — train/test split removed (2026-07-22)

- Deleted `analyze/split.py`, `split_lib.py`, `tests/`, and split artifacts (`split_ids.json`, `analysis_with_split.csv`).
- Schema helper moved to `analyze/schema.py`.
- Pipeline is `build_table.py` → `embed_2d.py` only; reductions fit on all rows; single-panel plots.
