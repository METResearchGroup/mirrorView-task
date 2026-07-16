# outputs/

Experiment artifacts for Qwen3 Next 80B labels and downstream Titan-space analysis.

**Most important files / dirs**

- `base_model_llm_labels.csv` — per-post correctness labels
- `run_manifest.json` — source run metadata
- `analysis/` — shared split, linear separator, 2D reduction, clustering

| filename | description of what it’s for |
| --- | --- |
| `base_model_llm_labels.csv` | Primary labels CSV: one row per post with `is_correct` for `bedrock/qwen3-next-80b-a3b` |
| `run_manifest.json` | Manifest of the included classifier run (path, ablation, expected rows) |
| `analysis/` | Nested analysis outputs (table, split, logistic, PCA/LDA, clusters) |
| `README.md` | This folder index |
