# ModernBERT keep/remove classifier

Head-only [`answerdotai/ModernBERT-base`](https://huggingface.co/answerdotai/ModernBERT-base) binary classifier (`remove=1`, `keep=0`) on **original post text only**. Weighted CE (`remove=2.0`), stratified **80/10/10** train/val/test. Stack: HF `Trainer`, W&B, optional SageMaker (`ml.g4dn.xlarge`, `us-east-2`) with assets under `s3://jspsych-mirror-view-4/modernbert-training/`.

## Run (from repo root)

Requires `WANDB_API_KEY` (train / SageMaker). `SAGEMAKER_ROLE_ARN` for remote launch only.

```bash
uv sync --extra modernbert-training

PYTHONPATH=. uv run --extra modernbert-training python experiments/predict_keep_remove_2026_07_01/models/modernbert/train.py \
  --config experiments/predict_keep_remove_2026_07_01/models/modernbert/configs/modernbert_base.yaml

PYTHONPATH=. uv run --extra modernbert-training python experiments/predict_keep_remove_2026_07_01/models/modernbert/evaluate.py \
  --run-dir experiments/predict_keep_remove_2026_07_01/models/modernbert/artifacts/modernbert-base/<timestamp>

PYTHONPATH=. uv run --extra modernbert-training python experiments/predict_keep_remove_2026_07_01/models/modernbert/threshold_analysis.py \
  --run-dir experiments/predict_keep_remove_2026_07_01/models/modernbert/artifacts/modernbert-base/<timestamp>

PYTHONPATH=. uv run --extra modernbert-training python experiments/predict_keep_remove_2026_07_01/models/modernbert/predict.py \
  --run-dir experiments/predict_keep_remove_2026_07_01/models/modernbert/artifacts/modernbert-base/<timestamp> \
  --text "example political post"

PYTHONPATH=. uv run --extra modernbert-training python experiments/predict_keep_remove_2026_07_01/models/modernbert/launch_sagemaker.py \
  --config experiments/predict_keep_remove_2026_07_01/models/modernbert/configs/modernbert_base.yaml
```

Smoke: add `--limit 32 --num-train-epochs 1` to `train.py`.

## Artifacts

Under `artifacts/modernbert-base/<timestamp>/`:

- `metrics.json` — train/val/test metrics at threshold `0.5`
- `train_predictions.csv`, `val_predictions.csv`, `test_predictions.csv`
- `calibration.json` — thresholds `0.1`–`0.9` on val/test (from `evaluate.py`)
- HF model/tokenizer, `metadata.json`
