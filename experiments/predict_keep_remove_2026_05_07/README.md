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
- Data filter: only linked-fate moderation rows (`evaluation_mode == linked_fate`), then keep/remove decisions.
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
- Experimental context features:
  - `sample_toxicity_type` (categorical; one-hot encoded in model featurization)
  - `sampled_stance` (categorical; one-hot encoded in model featurization)

This corresponds to the original 22 analysis-derived features plus 2 linked-fate context features.

### Results so far

Logistic Regression (`models/outputs/2026_05_07-18:22:53`):

- Train:
  - accuracy: `0.698962`
  - precision: `0.738910`
  - recall: `0.846176`
  - f1: `0.788913`
  - roc_auc: `0.675355`
- Test:
  - accuracy: `0.694717`
  - precision: `0.724802`
  - recall: `0.853403`
  - f1: `0.783863`
  - roc_auc: `0.678199`

XGBoost (`models/outputs/2026_05_07-18:22:57`):

- Train:
  - accuracy: `0.736981`
  - precision: `0.756227`
  - recall: `0.891869`
  - f1: `0.818466`
  - roc_auc: `0.777310`
- Test:
  - accuracy: `0.692830`
  - precision: `0.717235`
  - recall: `0.869110`
  - f1: `0.785902`
  - roc_auc: `0.702111`

Notes:

- XGBoost still edges logistic regression on test ROC-AUC, with very similar test accuracy.
- Restricting to linked-fate rows and adding `sample_toxicity_type`/`sampled_stance` materially improved separability over the prior setup.
