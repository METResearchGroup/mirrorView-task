# Baselines for Keep/Remove Prediction

This directory contains baseline experiments for understanding class balance and trivial predictors before model calibration and threshold tuning.

## What this computes

- Class balance for overall/train/test splits.
- Always-keep baseline.
- Always-remove baseline.
- Stratified-random baseline (sampled from train keep/remove prior).

All metrics are reported with a remove-focused view as well (treating `remove` as positive).

## Run

From repo root:

`PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/baseline/run_baselines.py --train-split 0.8 --seed 42`

## Outputs

Saved under:

`experiments/predict_keep_remove_2026_05_07/baseline/outputs/{timestamp}/`

Files:

- `metadata.json`
- `class_balance.json`
- `baseline_metrics.json`
- `test_predictions_majority_keep.csv`
- `test_predictions_majority_remove.csv`
- `test_predictions_stratified_random.csv`
