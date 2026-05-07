# Predicting which pairs of posts to keep/remove

The goal here is to create a model to overfit on our initial pilot data. We want to see what it would look like (in terms of problem setup, loss, etc.) to train a model to predict the keep/remove decisions. By creating a v1 that's overfit on our initial pilot data, we can make informed decisions about how much data we need, how to design the problem, etc.

The output in question is the binary keep/remove decision, for each pair of posts.

Some ideas for features:

- Embeddings: original text embeddings, mirrored text embeddings.
- Text features: We can repurpose labels from `experiments/mirrors_content_analysis_2026_04_24/`.
- User features: political party, condition, gender, age

Models:

- Simple: logistic regression, XGBoost. Would be limited to using the non-embedding features, but that's OK.
- Complex: transformer-based NN models + classification head.

## Implementation

Current setup (v1 baseline):

- Target: `keep_remove_label` (`1=keep`, `0=remove`).
- Split: random row split, `train_split=0.8`, `seed=42`.
- Models trained via CLI:
  - `PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/train.py --model logistic_regression --seed 42`
  - `PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/train.py --model xgboost --seed 42`

Feature set used by both Logistic Regression and XGBoost (non-embedding):

- Intergroup classifier labels: original + mirror.
- PRIME classifier labels: original + mirror.
- Valence classifier labels: original + mirror.
- Length/compression metrics (original + mirror):
  - char count, word count, sentence count, avg sentence length, punctuation count, punctuation density.
- Readability metrics (original + mirror):
  - Flesch-Kincaid grade, Flesch reading ease.

This corresponds to 22 numeric analysis-derived features total.

### Results so far

Logistic Regression (`models/outputs/2026_05_07-17:58:48`):

- Train:
  - accuracy: `0.677602`
  - precision: `0.677561`
  - recall: `0.998666`
  - f1: `0.807358`
  - roc_auc: `0.566377`
- Test:
  - accuracy: `0.677789`
  - precision: `0.678277`
  - recall: `0.997979`
  - f1: `0.807641`
  - roc_auc: `0.554978`

XGBoost (`models/outputs/2026_05_07-18:00:58`):

- Train:
  - accuracy: `0.703934`
  - precision: `0.708795`
  - recall: `0.954495`
  - f1: `0.813498`
  - roc_auc: `0.666400`
- Test:
  - accuracy: `0.692480`
  - precision: `0.702810`
  - recall: `0.946547`
  - f1: `0.806669`
  - roc_auc: `0.618905`

Notes:

- XGBoost improves over logistic regression on test accuracy and ROC-AUC with the same feature set.
- Recall is high for both models, suggesting a tendency toward predicting `keep`; calibration/threshold tuning is a likely next step.
