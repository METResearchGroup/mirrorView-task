# Calibration Pipeline (keep/remove)

This folder contains the calibration and threshold-selection pipeline for
`experiments/predict_keep_remove_2026_05_07`.

## Run

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/calibration/run_calibration.py run \
  --model xgboost \
  --calibrator sigmoid \
  --threshold-policy max_f1_remove \
  --seed 42
```

## Outputs

Each run writes to:

`experiments/predict_keep_remove_2026_05_07/calibration/outputs/{timestamp}/`

Artifacts:

- `metadata.json`
- `calibration_metrics.json`
- `calibration_bins_raw.csv`
- `calibration_bins_calibrated.csv`
- `threshold_sweep.csv`
- `selected_threshold.json`
- `test_metrics_at_selected_threshold.json`
- `calibrated_test_predictions.csv`
- `reliability_curve.png`
- `threshold_sweep_curve.png`
- `calibration_metrics_over_time.png`
