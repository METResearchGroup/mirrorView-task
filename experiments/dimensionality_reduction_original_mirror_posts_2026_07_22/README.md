# Dimensionality reduction: original vs mirrored Titan embeddings (2026-07-22)

PCA/LDA of **original** vs **mirrored** post texts in Titan 256-d space.
Each `post_id` contributes two rows (long `2N × 256` matrix). Reductions are fit
on **all** rows (no train/test split); plots are single-panel scatters colored by
original vs mirrored.

**Most important files**

- `RESULTS.md` — observed metrics and plot paths
- `spec.md` — frozen contracts
- `analyze/` — build_table → embed_2d
- `outputs/analysis/` — matrix, PNGs, summaries

| filename | description |
| --- | --- |
| `README.md` | This experiment index |
| `RESULTS.md` | Results writeup |
| `spec.md` | Schema / path / invariant contracts |
| `analyze/` | Pipeline scripts |
| `outputs/analysis/` | Artifacts |

## Prerequisites

- **Primary (required for happy path):** local Titan cache at  
  `experiments/predict_keep_remove_2026_07_01/embedding_cache/`  
  (`embeddings/*.npy`; ~17k files). **No Bedrock / no S3 / no DynamoDB.**
- **Optional backup only:**  
  `/Users/mark/Documents/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/embedding_cache/`
- Training CSV used by the PKR dataloader:  
  `experiments/predict_keep_remove_2026_07_01/keep_remove_results_2026_06_23.csv`

Scripts fail loud with a clear path error if neither cache is populated.

## Run analysis

```bash
# from repo root
PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/build_table.py
PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/embed_2d.py
```

Writes under `outputs/analysis/`:

- `analysis_meta.csv`, `X_original_and_mirror.npy`, `analysis_table.parquet`
- `pca_original_vs_mirrored.png`, `lda_original_vs_mirrored.png`
- `embeddings_2d.csv`, `reduction_summary.json`, `pca_variance_explained.json`

## Notes

- LDA / plot color target = `is_mirrored` (not keep/remove, not Qwen error).
- No train/test split; scaler / PCA / LDA fit on all rows.
- Does **not** write under `experiments/model_errors_analysis_2026_07_15/`.
