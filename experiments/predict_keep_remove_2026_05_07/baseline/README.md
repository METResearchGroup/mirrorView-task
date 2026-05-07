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

## Latest run details

Reference run:

- timestamp: `2026_05_07-18:22:38`
- train split: `0.8`
- seed: `42`
- target: `keep_remove_label`
- rows: `10600` train / `2650` test
- train keep prior: `0.6648113207547169`

### `class_balance.json` (how imbalanced is the task?)

- Overall:
  - `n=13250`
  - `keep=8766` (`0.6615849056603773`)
  - `remove=4484` (`0.33841509433962264`)
- Train:
  - `n=10600`
  - `keep=7047` (`0.6648113207547169`)
  - `remove=3553` (`0.335188679245283`)
- Test:
  - `n=2650`
  - `keep=1719` (`0.6486792452830189`)
  - `remove=931` (`0.35132075471698115`)

Interpretation:

- The linked-fate-only dataset remains keep-heavy (~65/35), but is less skewed than before.
- A naive classifier can get ~0.649 test accuracy by always predicting keep.
- Because we care about remove decisions, remove-focused metrics are essential.

### `baseline_metrics.json` (how strong are trivial baselines?)

`majority_keep`:

- Keep-as-positive:
  - accuracy `0.6486792452830189`
  - precision `0.6486792452830189`
  - recall `1.0`
  - f1 `0.7869182389937107`
- Remove-as-positive:
  - precision `0.0`
  - recall `0.0`
  - f1 `0.0`
- `roc_auc_keep=0.5`

Interpretation:

- This baseline exactly matches linked-fate test keep rate in accuracy.
- It is useless for remove detection (remove recall/f1 = 0).
- Any real model should beat this on remove-focused metrics.

`majority_remove`:

- Keep-as-positive:
  - accuracy `0.35132075471698115`
  - precision `0.0`
  - recall `0.0`
  - f1 `0.0`
- Remove-as-positive:
  - precision `0.35132075471698115`
  - recall `1.0`
  - f1 `0.5199664804469274`
- `roc_auc_keep=0.5`

Interpretation:

- This is the opposite extreme: catches all removes, but over-removes everything.
- Provides an upper-bound style recall baseline for remove (`1.0`) with poor precision.
- Useful sanity check for threshold policy tradeoffs.

`stratified_random` (sample by train keep prior):

- Keep-as-positive:
  - accuracy `0.5509433962264151`
  - precision `0.6518691588785047`
  - recall `0.6765561372880744`
  - f1 `0.6639839034205231`
- Remove-as-positive:
  - precision `0.34793650793650793`
  - recall `0.28893662728249194`
  - f1 `0.31570449678800856`
- `roc_auc_keep=0.5`

Interpretation:

- This approximates chance behavior under class imbalance.
- It is a better remove benchmark than majority_keep because it produces both classes.
- Models should exceed this on remove precision/recall/f1 and calibration quality.

### CSV predictions files

- `test_predictions_majority_keep.csv`
- `test_predictions_majority_remove.csv`
- `test_predictions_stratified_random.csv`

Each file includes:

- `post_id`
- `decision` (original label string)
- `keep_remove_label` (ground truth target)
- `predicted_label`
- `predicted_keep_probability`

Interpretation:

- These are useful for spot-checking error modes and computing any additional metrics offline.
- For calibration work, they provide a baseline comparison set against tuned model probabilities and thresholds.
