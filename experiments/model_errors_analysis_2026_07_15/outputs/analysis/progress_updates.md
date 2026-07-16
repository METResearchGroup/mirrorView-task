# Data prep — progress updates

Scope: analysis table + shared split only. No training / 2D viz / Bedrock re-runs.

## Build analysis table

- Labels: `outputs/base_model_llm_labels.csv` (8791 rows, `bedrock/qwen3-next-80b-a3b` only)
- Feature set: `only_original` / Titan `amazon.titan-embed-text-v2:0` dims=256
- Embedding cache: `/Users/mark/Documents/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/embedding_cache` (local `.npy` only; **AWS not called**)
- Cache hits=8791 misses=0 (full coverage; no DynamoDB/S3 fallback needed)
- Artifacts (under `outputs/analysis/`):
  - `analysis_table.parquet` — columns `post_id,label,is_correct,is_error,embedding`; `embedding` length-256 float64; **rows=8791**
  - `X_only_original.npy` — shape **`(8791, 256)`**
  - `analysis_meta.csv` — scalar columns only (`post_id,label,is_correct,is_error`)
  - `analysis_table_meta.json` — loader / cache metadata
- `is_error` rate: 0.3585 (correct=5639, error=3152)

## Single shared train/test split

- Seed=42, `train_split=0.8`, stratify_on=`is_error`
- Artifact: `outputs/analysis/split_ids.json`
- **n_total=8791**, **n_train=7032**, **n_test=1759**
- Disjoint: train ∩ test = ∅; union covers analysis set
- `is_error` rates: overall=0.3585, train=0.3585, test=0.3587
- Convenience join: `outputs/analysis/analysis_with_split.csv` (`post_id,label,is_correct,is_error,split`)
- Downstream agents must load these IDs; do **not** re-split.

## How to rebuild

```bash
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/build_table.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/split.py
```

## Blockers

- None for analysis table / shared split. Worktree has no local `embedding_cache/`; used main-repo cache (gitignored, 17,370 `.npy` files). 100% local hits.
- Did **not** call Bedrock / Converse / `api_baselines/*/train.py`.
