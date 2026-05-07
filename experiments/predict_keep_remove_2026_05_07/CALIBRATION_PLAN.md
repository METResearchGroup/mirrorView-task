# Calibration and Threshold Plan (Remove-Focused)

## Objective

Optimize decision quality for the `remove` action, since this is the key outcome of interest.

Current label encoding:

- `keep_remove_label = 1` means keep
- `keep_remove_label = 0` means remove

For calibration/threshold work, treat **remove as the positive class** in reporting.

---

## Why this is needed

- Class balance is skewed toward keep (~68% keep, ~32% remove).
- A model can achieve solid accuracy by overpredicting keep.
- We care most about correctly identifying remove decisions.

Therefore, default threshold `0.5` and raw probabilities are not sufficient.

---

## Metrics to prioritize

Primary (remove-focused):

- `recall_remove`: Of actual removes, how many we catch.
- `precision_remove`: Of predicted removes, how many are truly remove.
- `f1_remove`: Harmonic mean of precision/recall for remove.
- `balanced_accuracy`: Average recall across keep/remove.
- `pr_auc_remove`: Precision-recall AUC for remove (especially useful under imbalance).

Secondary:

- ROC-AUC (class-agnostic ranking quality).
- Calibration quality:
  - Brier score
  - reliability curve / ECE-style bin analysis.

---

## Data split policy

Use a 3-way split for threshold + calibration:

1. `train`: fit base model.
2. `calibration/validation`: fit calibrator and select threshold.
3. `test`: final locked evaluation only.

Do not tune threshold on test.

---

## Calibration workflow

1. Train base model on `train`.
2. Get raw probabilities on calibration fold.
3. Fit calibrator on calibration fold:
   - Start with sigmoid/Platt scaling.
   - Optionally compare isotonic regression.
4. Apply calibrator to get calibrated probabilities.
5. Evaluate probability quality (Brier + reliability plots/tables).

---

## Threshold tuning workflow (remove-focused)

Given calibrated probabilities:

1. Convert to remove probability:
   - `p_remove = 1 - p_keep`
2. Sweep threshold grid, e.g. `0.05 ... 0.95`.
3. For each threshold, compute remove-focused metrics.
4. Pick threshold by explicit policy, e.g.:
   - maximize `f1_remove`, or
   - maximize `balanced_accuracy` with constraint `recall_remove >= target`.
5. Lock threshold and evaluate once on test.

---

## Suggested policy (default)

Start with:

- Tune threshold to maximize `f1_remove` on calibration split.
- Report accompanying `recall_remove` and `precision_remove`.
- If moderation risk prefers catching removes, switch to constraint-based policy:
  - maximize precision_remove subject to `recall_remove >= 0.80` (example target).

---

## Artifacts to store under `experiments/predict_keep_remove_2026_05_07/calibration/outputs/{timestamp}/`

- `metadata.json`
- `calibration_metrics.json` (Brier, ECE-style bins, etc.)
- `threshold_sweep.csv` (one row per threshold)
- `selected_threshold.json` (policy + selected threshold + validation metrics)
- `test_metrics_at_selected_threshold.json`
- `calibrated_test_predictions.csv`

---

## Baseline comparisons to include in all reports

At minimum, compare against:

- Always keep baseline.
- Always remove baseline.
- Stratified random baseline using train prior.

For each baseline, report remove-focused metrics so gains are interpretable.
