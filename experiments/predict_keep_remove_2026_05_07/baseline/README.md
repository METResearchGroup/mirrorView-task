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

- timestamp: `2026_05_07-18:09:55`
- train split: `0.8`
- seed: `42`
- target: `keep_remove_label`
- rows: `32128` train / `8032` test
- train keep prior: `0.6764815737051793`

### `class_balance.json` (how imbalanced is the task?)

- Overall:
  - `n=40160`
  - `keep=27178` (`0.6767430278884462`)
  - `remove=12982` (`0.3232569721115538`)
- Train:
  - `n=32128`
  - `keep=21734` (`0.6764815737051793`)
  - `remove=10394` (`0.3235184262948207`)
- Test:
  - `n=8032`
  - `keep=5444` (`0.6777888446215139`)
  - `remove=2588` (`0.32221115537848605`)

Interpretation:

- The dataset is strongly keep-heavy (~68/32).
- A naive classifier can get ~0.678 test accuracy by always predicting keep.
- Because we care about remove decisions, remove-focused metrics are essential.

### `baseline_metrics.json` (how strong are trivial baselines?)

`majority_keep`:

- Keep-as-positive:
  - accuracy `0.6777888446215139`
  - precision `0.6777888446215139`
  - recall `1.0`
  - f1 `0.8079548827545265`
- Remove-as-positive:
  - precision `0.0`
  - recall `0.0`
  - f1 `0.0`
- `roc_auc_keep=0.5`

Interpretation:

- This baseline exactly matches test keep rate in accuracy.
- It is useless for remove detection (remove recall/f1 = 0).
- Any real model should beat this on remove-focused metrics.

`majority_remove`:

- Keep-as-positive:
  - accuracy `0.32221115537848605`
  - precision `0.0`
  - recall `0.0`
  - f1 `0.0`
- Remove-as-positive:
  - precision `0.32221115537848605`
  - recall `1.0`
  - f1 `0.4873822975517891`
- `roc_auc_keep=0.5`

Interpretation:

- This is the opposite extreme: catches all removes, but over-removes everything.
- Provides an upper-bound style recall baseline for remove (`1.0`) with poor precision.
- Useful sanity check for threshold policy tradeoffs.

`stratified_random` (sample by train keep prior):

- Keep-as-positive:
  - accuracy `0.5697211155378487`
  - precision `0.6811884797666788`
  - recall `0.6864437913299045`
  - f1 `0.6838060384263495`
- Remove-as-positive:
  - precision `0.32953652788688137`
  - recall `0.32418856259659967`
  - f1 `0.32684067004285156`
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
