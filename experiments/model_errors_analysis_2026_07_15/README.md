# Model errors analysis (2026-07-15)

Per-post correctness for Bedrock **Qwen3 Next 80B** (`bedrock/qwen3-next-80b-a3b`), plus linear separator / 2D reduction / clustering on original-post Titan embeddings. **Do not** call Bedrock — use the copied `predictions.csv` only.

**Most important files**

- `RESULTS.md` — stakeholder writeup (plots + metrics)
- `spec.md` — implementation spec
- `outputs/base_model_llm_labels.csv` — labels CSV
- `outputs/analysis/` — analysis artifacts
- `collect/`, `analyze/` — pipeline code

| filename | description of what it’s for |
| --- | --- |
| `README.md` | This experiment index |
| `RESULTS.md` | Results writeup with core images and metrics |
| `spec.md` | Full pipeline / schema / constraint spec |
| `collect/` | Build labels CSV from existing predictions |
| `analyze/` | Analysis table, shared split, linear separator, 2D, clustering |
| `outputs/` | Labels CSV, run manifest, and `analysis/` artifacts |

## Produce the labels CSV

```bash
cd experiments/model_errors_analysis_2026_07_15
uv run python collect/build_long_csv.py
```

Expected: **8,791** rows in `outputs/base_model_llm_labels.csv`. Source run: `.../qwen3-next-80b-a3b/outputs/2026_07_06-16:57:43/`.

## Run analysis

```bash
# from repo root
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/build_table.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/split.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/linear_separator.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/embed_2d.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/cluster.py
```

Writes under `outputs/analysis/` (clustering under `outputs/analysis/clusters/`).
