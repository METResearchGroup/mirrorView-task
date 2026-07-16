# Model errors analysis (2026-07-15) — V0 labels CSV

Per-post correctness for the **primary classifier only**: Bedrock **Qwen3 Next 80B** (`bedrock/qwen3-next-80b-a3b`).

**Policy:** Do **not** call Bedrock / AWS / `api_baselines/*/train.py`. Use the copied `predictions.csv` artifact only.

## Produce the labels CSV

From the repo root (needs `pandas`):

```bash
cd experiments/model_errors_analysis_2026_07_15
uv run python collect/build_long_csv.py
```

Or separately:

```bash
uv run python collect/manifest.py
uv run python collect/build_long_csv.py
```

## Outputs

| Path | Description |
| --- | --- |
| `outputs/run_manifest.json` | Included classifier, ablation, source run dir |
| `outputs/base_model_llm_labels.csv` | Qwen labels + correctness (`family=bedrock`, one `classifier_id`) |

Schema columns: `post_id`, `original_text`, `mirrored_text`, `label`, `classifier_id`, `family`, `ablation`, `is_correct`.

Expected size: **8,791** rows (`classifier_id == bedrock/qwen3-next-80b-a3b`).

Source run: `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/qwen3-next-80b-a3b/outputs/2026_07_06-16:57:43/`. See `spec.md` § Primary correctness signal.

## V1 analysis (shared split → logistic + 2D)

```bash
# from repo root
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/v1_build_table.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/v1_split.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/v1_linear_separator.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/v1_embed_2d.py
PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/v1_cluster.py
```

Writes under `outputs/v1_bedrock/` (and `outputs/v1_bedrock/clusters/` for V1.4). Stakeholder writeup: **`RESULTS.md`**.

## Scope note

**V0** labels CSV, **V1** error-separability (shared split → logistic probe + PCA/LDA on `only_original` Titan), and **V1.4** reduced-space clustering are implemented. Hard-pair rate tables from the V0 checklist remain optional follow-up.
