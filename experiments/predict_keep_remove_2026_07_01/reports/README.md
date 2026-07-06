# Reports

Figures and tables for `results.md`. Generators read experiment outputs (metrics JSON, `results.md` LaTeX tables, or local embedding cache) and write PNG + JSON under `reports/outputs/<name>/<timestamp>/`.

## Layout

| Path | Purpose |
| --- | --- |
| `parse_results_md.py` | Parse LaTeX `array` metric tables from `results.md`. |
| `plot_style.py` | Shared colors, metric order, and label helpers. |
| `paths.py` | Experiment/report path constants and `make_output_dir()`. |
| `generate/cosine_histogram.py` | Histogram of original vs mirror embedding cosine similarity. |
| `generate/dataset_metrics.py` | Print dataset overview stats for the results writeup. |
| `generate/study_2_ablations_bargraph.py` | Study 2 ablation test-set metrics bar chart. |
| `generate/test_metrics_linegraph.py` | Study 1 feature-engineering vs embeddings line graph. |
| `outputs/` | Generated figures (timestamped subfolders). |

## Run (from repo root)

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/reports/generate/dataset_metrics.py
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/reports/generate/test_metrics_linegraph.py
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/reports/generate/study_2_ablations_bargraph.py
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/reports/generate/cosine_histogram.py
```

Cosine histogram requires a populated `embedding_cache/` (or pass `--embedding-cache-dir`).

## Adding a new plot

1. Add shared parsing/styling to `parse_results_md.py` or `plot_style.py` if needed.
2. Add a script under `generate/`.
3. Write outputs via `make_output_dir()` so artifacts land in `reports/outputs/`.
4. Link the PNG in `results.md`.
