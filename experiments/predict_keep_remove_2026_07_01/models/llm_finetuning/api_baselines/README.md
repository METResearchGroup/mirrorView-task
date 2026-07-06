# Experiment 3 Step 1 — Bedrock Zero-Shot Baselines

Zero-shot keep/remove classification for four open-weight models on AWS Bedrock, using the study linked-fate prompt with blinded Post 1/Post 2 shuffle.

## Prerequisites

1. AWS credentials with Bedrock access in `us-east-2` (`lib/constants.py` → `BEDROCK_REGION`).
2. Enable these model IDs in the Bedrock console:
   - `mistral.ministral-3-8b-instruct`
   - `mistral.ministral-3-14b-instruct`
   - `qwen.qwen3-32b-v1:0`
   - `qwen.qwen3-next-80b-a3b`
3. Verify access:

```bash
aws bedrock list-foundation-models --region us-east-2 \
  --query "modelSummaries[?contains(modelId, 'ministral')].modelId" --output table
```

## Cost warning

Each full run scores **~8,791 Bedrock requests** (80/20 stratified split, `seed=42`). Running all four models is ~35k requests total. Use `--limit 8` for smoke tests.

## Smoke test

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/ministral-3-8b-instruct/train.py --limit 8 --max-concurrency 2
```

Expect exit code `0` and a run directory under `ministral-3-8b-instruct/outputs/<timestamp>/` with:

- `train_predictions.csv` / `test_predictions.csv` (columns: `message_id`, `keep_remove_label`, `predicted_label`)
- `metrics.json` (`train_metrics` / `test_metrics` with `accuracy`, `precision`, `recall`, `f1` only)
- `metadata.json` (`bedrock_model_id`, `post_shuffle_seed`, `n_train`, `n_test`, `status`)

## Full runs (per model)

Run from repo root:

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/ministral-3-8b-instruct/train.py --max-concurrency 2

PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/ministral-3-14b-instruct/train.py --max-concurrency 2

PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/qwen3-32b/train.py --max-concurrency 2

PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/qwen3-next-80b-a3b/train.py --max-concurrency 2
```

### CLI options (all variants)

| Flag | Default | Description |
|------|---------|-------------|
| `--train-split` | `0.8` | Stratified train fraction |
| `--seed` | `42` | Split + shuffle seed |
| `--limit` | none | Subsample rows per split (smoke) |
| `--max-concurrency` | `2` | Concurrent Bedrock requests |
| `--temperature` | `0.0` | Sampling temperature |
| `--resume` | none | Resume an incomplete run directory |

## Resume semantics

Re-run with `--resume <run_dir>` to skip `message_id`s already in the prediction CSVs. Safe to retry after interruption; completed rows are not re-requested.

## Aggregate artifacts

After at least one completed run:

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/plot_results.py

PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/summarize_results.py
```

- `plot_results.py` → `outputs/plot_results/<timestamp>/` with `summary.json` and `accuracy.png`, `precision.png`, `recall.png`, `f1.png`
- `summarize_results.py` → `aggregate_outputs/` CSV/MD + updates `HOW_TO_TRAIN_LANGUAGE_MODELS.md` (`LLM_FINETUNING_BASELINE_RESULTS_TABLE` marker)

## Layout

```text
api_baselines/
  README.md
  schemas.py, constants.py, client.py, dataset.py, prompts.py, runner.py
  plot_results.py, summarize_results.py
  ministral-3-8b-instruct/train.py
  ministral-3-14b-instruct/train.py
  qwen3-32b/train.py
  qwen3-next-80b-a3b/train.py
  outputs/plot_results/
```

Shared prompt lives in `prompts.py` (study template with deterministic Post 1/Post 2 shuffle). Leaf `train.py` files only wire model IDs to `run_bedrock_baseline_variant`.
