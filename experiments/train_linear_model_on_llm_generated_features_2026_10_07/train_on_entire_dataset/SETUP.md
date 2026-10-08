# Setup

## Data

Training rows come from `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS`. Test rows come from `STUDY_2_KEEP_REMOVE_SPLIT_LABELS`. Load both with `shared.data.dataloader.load_dataset`.

The predictors are the 30 binary columns in `s3://mirrorview-experimental-artifacts/experiments/study_2_llm_based_feature_extraction_2026_09_29/step6_label_posts_with_features/post_feature_labels.parquet`.

## Outputs

Fitted models, frames, and metric files upload to `s3://mirrorview-experimental-artifacts/experiments/train_linear_model_on_llm_generated_features_2026_10_07/train_on_entire_dataset/`.

## Command

```bash
PYTHONPATH=. uv run python -m experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.run
```
