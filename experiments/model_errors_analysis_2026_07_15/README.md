# Model errors analysis (2026-07-15) — V0 long CSV

Long table of per-post correctness for the **primary classifier only**: Bedrock **Qwen3 Next 80B** (`bedrock/qwen3-next-80b-a3b`).

**Policy:** Do **not** call Bedrock / AWS / `api_baselines/*/train.py`. Use the copied `predictions.csv` artifact only.

## Produce the long CSV

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
| `outputs/classifier_post_results_long.csv` | Target long CSV (`family=bedrock`, one `classifier_id`) |

Schema columns: `post_id`, `original_text`, `mirrored_text`, `label`, `classifier_id`, `family`, `ablation`, `is_correct`.

Expected size: **8,791** rows (`classifier_id == bedrock/qwen3-next-80b-a3b`).

Source run: `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/qwen3-next-80b-a3b/outputs/2026_07_06-16:57:43/`. See `spec.md` § Primary correctness signal.

## Scope note

This directory currently implements **V0 collection through the long CSV** only. Hard-pair tables and V1 primary-classifier embedding separability are specified in `spec.md` but not implemented yet.
