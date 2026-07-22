# Dimensionality reduction on human keep/remove labels (2026-07-22)

Exploratory PCA/LDA visualization of Titan embeddings colored by **human** keep/remove labels (`label`: `0=keep`, `1=remove`) — not model correctness. Full-data fit (no train/test split); single scatter per plot.

**Most important files**

- `RESULTS.md` — plots + brief separability notes
- `analyze/` — build matrices + three view scripts
- `outputs/analysis/` — matrices, coords, six primary PNGs

| Path | Purpose |
| --- | --- |
| `analyze/build_table.py` | Load labels + Titan cache → `X_original.npy` / `X_mirrored.npy` |
| `analyze/reduction.py` | Full-data fit/transform + color palette + single-scatter helpers |
| `analyze/plot_original.py` | Original-only PCA/LDA |
| `analyze/plot_mirrored.py` | Mirrored-only PCA/LDA |
| `analyze/plot_both.py` | Stacked original+mirrored (dark=original, light=mirrored) |
| `outputs/analysis/{original,mirrored,both}/` | PNGs, `embeddings_2d.csv`, `reduction_summary.json` |

## Contracts

- Color / LDA target = human `label` only (`0=keep`, `1=remove`)
- No Bedrock/AWS calls — local Titan `.npy` cache only
- No train/test split — exploratory full-data fit
- Does not modify `experiments/model_errors_analysis_2026_07_15/`

### Color legend

| Role | Keep (`label=0`) | Remove (`label=1`) |
|------|------------------|--------------------|
| Single-view (original or mirrored) | `#2E7D32` green | `#C62828` red |
| Both-view, original (darker) | `#1B5E20` | `#B71C1C` |
| Both-view, mirrored (lighter) | `#81C784` | `#EF9A9A` |

Markers: keep=`o`, remove=`x`.

## Run

From repo root:

```bash
PYTHONPATH=. uv run python experiments/dimensionality_reduction_labels_2026_07_22/analyze/build_table.py
PYTHONPATH=. uv run python experiments/dimensionality_reduction_labels_2026_07_22/analyze/plot_original.py
PYTHONPATH=. uv run python experiments/dimensionality_reduction_labels_2026_07_22/analyze/plot_mirrored.py
PYTHONPATH=. uv run python experiments/dimensionality_reduction_labels_2026_07_22/analyze/plot_both.py
```

Labels source (read-only): `experiments/model_errors_analysis_2026_07_15/outputs/base_model_llm_labels.csv` (~8,791 rows; keep=5978 / remove=2813).

Embedding cache: worktree `experiments/predict_keep_remove_2026_07_01/embedding_cache` if populated, else main checkout at `/Users/mark/Documents/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/embedding_cache`.
