# Model errors analysis (2026-07-15) — V0 long CSV

Aggregate Bedrock zero-shot + OpenAI `llm_api` predictions into one long table for hard-pair analysis.

**Policy:** Do **not** call Bedrock / AWS / `api_baselines/*/train.py`. Use copied `predictions.csv` artifacts only.

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
| `outputs/run_manifest.json` | Included classifiers, ablations, source run dirs |
| `outputs/classifier_post_results_long.csv` | Target long CSV (`family` ∈ {`bedrock`, `llm_api`}) |

Schema columns: `post_id`, `original_text`, `mirrored_text`, `label`, `classifier_id`, `family`, `ablation`, `is_correct`.

Expected size: 6 classifiers × 8791 posts = **52,746** rows.

## Scope note

This directory currently implements **V0 collection through the long CSV** only. Hard-pair tables and V1 Bedrock embedding separability are specified in `spec.md` but not implemented yet.
