# Embeddings

Bedrock Titan text embeddings for the keep/remove experiment: generation, local caching, and feature vectors for classical ML (logistic regression and XGBoost).

## Files

| File | Purpose |
| --- | --- |
| `generate.py` | CLI to generate embeddings for all posts, upload to S3, and verify via DynamoDB. Thin wrapper around `experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py` using `data/dataloader.py`. |
| `cache_loader.py` | Load embeddings from DynamoDB → S3 with a local disk cache (`embeddings/*.npy`). Used by all embedding-based train scripts. |
| `features/concat_cosine.py` | Baseline ablation: `concat(orig_emb, mirror_emb, cosine_similarity)` → shape `(513,)`. |
| `features/difference.py` | Ablation: elementwise `orig_emb - mirror_emb` only → shape `(256,)`. |
| `features/only_original.py` | Ablation: `orig_emb` only → shape `(256,)`. |

## Run

Generate embeddings (from repo root):

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/embeddings/generate.py --limit 2
```

Train scripts import from `experiments.predict_keep_remove_2026_07_01.embeddings` (or the submodules under `embeddings.features`).

## Consumers

- `models/logistic_regression/train*.py`
- `models/xgboost/train*.py`
