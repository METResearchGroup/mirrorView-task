# Proposal: Fit a logistic regression and a linear regression on the Study 2 LLM features

Scope: [issue 358](https://github.com/METResearchGroup/mirrorView-task/issues/358). The covered work is the experiment folder, the train and test rows, the two regressions, and the result tables. Feature mining and the 0 or 1 feature labels stay in [issue 321](https://github.com/METResearchGroup/mirrorView-task/issues/321) and [PR 323](https://github.com/METResearchGroup/mirrorView-task/pull/323). The split-label table stays in [issue 325](https://github.com/METResearchGroup/mirrorView-task/issues/325) and [PR 328](https://github.com/METResearchGroup/mirrorView-task/pull/328). The upsampled copies stay in [issue 338](https://github.com/METResearchGroup/mirrorView-task/issues/338) and [PR 343](https://github.com/METResearchGroup/mirrorView-task/pull/343).

## Overview

You fit two models on the 30 binary LLM features for Study 2 posts that already have a split keep and remove vote. The logistic regression predicts the modal label, which is keep or remove. The linear regression predicts the share of the five votes that are remove, and you limit each prediction to the range 0 to 1. You fit both models on the upsampled split-label rows, and you score both models on regular split-label rows that were held out of fitting. You write accuracy, precision, recall, and F1 for the logistic regression, and MAE, RMSE, and R^2 for the linear regression, in `RESULTS.md`.

## Cross-cutting concerns

### Posts and labels

The posts come from two registered tables that other Study 2 work already loads with `shared.data.dataloader.load_dataset`. `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS` is the training pool. `STUDY_2_KEEP_REMOVE_SPLIT_LABELS` is the scoring pool. Every row in both tables has five labelers, and every row has 1, 2, 3, or 4 remove votes.

I loaded both tables from S3 on October 8, 2026.

| Registry name | Role | Rows | Keep rows | Remove rows | Unique `post_id` |
| --- | --- | ---: | ---: | ---: | ---: |
| `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS` | Training pool | 14,562 | 7,281 | 7,281 | 9,941 |
| `STUDY_2_KEEP_REMOVE_SPLIT_LABELS` | Scoring pool | 9,941 | 7,281 | 2,660 | 9,941 |

The two tables contain the same 9,941 posts. The upsampled table has every regular row. It also has 4,621 copied remove rows, which brings both classes to 7,281 rows. `shared.utils.upsample.upsample_df` wrote those copies with seed 1. Keep has no copied rows. A copied row has the same `post_id` as its source row, so one remove post can appear more than once.

`keep_remove_label` is 0 for keep and 1 for remove. With five labelers, the modal label is remove when `n_remove` is 3 or 4, and it is keep when `n_remove` is 1 or 2. The linear target is `n_remove / n_raters`. On the regular table that quotient is 0.2, 0.4, 0.6, or 0.8, and it matched `1 - keep_rate` on every row. The regular remove-vote counts are 4,244 ones, 3,037 twos, 1,777 threes, and 883 fours.

### Train and test posts

Because every regular post is already in the upsampled table, you take the test posts out of the training rows before you fit. You hold out 20 percent of the unique posts in each modal class, which is the unique-id rule [issue 337](https://github.com/METResearchGroup/mirrorView-task/issues/337) describes for its upsampled tables. The LoRA experiment in that issue is absent from the repo, so you draw the posts in this experiment. The draw uses only the split-label tables.

You draw the holdout with `numpy.random.default_rng(1)`. You sort the post ids in each class. You draw the keep ids first, and you draw the remove ids only after the keep draw is finished. The test count in a class is `math.floor(0.20 * n)`. I ran that draw on October 8, 2026 in a script that is not committed.

| Set | Rows | Keep | Remove | Unique `post_id` |
| --- | ---: | ---: | ---: | ---: |
| Train, upsampled rows outside the holdout | 11,663 | 5,825 | 5,838 | 7,953 |
| Test, regular rows inside the holdout | 1,988 | 1,456 | 532 | 1,988 |

No post id is in both sets. The test frame has one row per post. The train frame can repeat a remove post, and each repeat has the same feature values. A prediction that always says keep is correct on 1,456 of the 1,988 test posts, so its accuracy is 0.7324. Its remove F1 is 0, because it never says remove.

### Features

Once the train posts and test posts are chosen, you join each post to the feature columns. The predictors are the 30 `is_*` columns in the feature table from PR 323. The object key is `experiments/study_2_llm_based_feature_extraction_2026_09_29/step6_label_posts_with_features/post_feature_labels.parquet`, built from `S3_PREFIX` and `POST_FEATURE_LABELS_KEY` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py`. The bucket is `mirrorview-experimental-artifacts`.

I downloaded that object on October 8, 2026. The object is 6,361,878 bytes and has 20,000 rows, with one row per post. Every feature value is 0 or 1. The column names match the keys of `LABEL_TO_DETAIL` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py`. All 9,941 split posts join to a feature row, and every joined feature cell is filled. `apply_threshold` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step6_label_posts_with_features/threshold.py` wrote those 0 and 1 values from the Jev probabilities at a cutoff of 0.7. The model column order is `sorted(LABEL_TO_DETAIL)`.

### Models

You fit the two regressions issue 358 names on the 30 columns above. The logistic model is `sklearn.linear_model.LogisticRegression(solver="lbfgs", max_iter=1000, random_state=1)`. You leave `class_weight` unset, because the 11,663 train rows are already 5,825 keep and 5,838 remove. The positive class is remove, which means precision, recall, and F1 treat a remove prediction as the event you are counting. The hard label is remove when the predicted remove probability is at least 0.5. On the prototype train scores and test scores, no probability was exactly 0.5, so the 0.5 rule matches `LogisticRegression.predict` for the numbers below. The fit used 24 iterations.

The linear model is `sklearn.linear_model.LinearRegression(fit_intercept=True)`. You fit it to `remove_proportion`. Before you score a prediction, you limit it to the range 0 to 1 with `numpy.clip`, and you also store the unlimited prediction. On the prototype, 0 of 11,663 train predictions and 0 of 1,988 test predictions were outside that range, so the limit did not change MAE, RMSE, or R^2.

`pyproject.toml` already requires `scikit-learn>=1.8.0`, `joblib>=1.5.3`, numpy as a scikit-learn dependency, and `pyarrow>=20.0.0`. The listed packages cover the fit and the save. You save each fitted estimator with `joblib`.

The fit calls `sklearn.linear_model.LogisticRegression` directly. `LogisticRegressionKeepRemoveModel` in `experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/model.py` is the embedding experiment's wrapper, and it sets `class_weight` and `random_state=42`.

### Reuse and import direction

Root `shared/` imports nothing from this experiment, and the feature experiment imports nothing from this experiment. The new code reads the registered upsampled CSV that `upsample_df` already wrote.

| Existing code | Symbols this experiment uses |
| --- | --- |
| `shared/data/dataloader.py` | `load_dataset` |
| `shared/data/registry.py` | `STUDY_2_KEEP_REMOVE_SPLIT_LABELS`, `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS` |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py` | `S3_BUCKET`, `S3_PREFIX`, `POST_FEATURE_LABELS_KEY` |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py` | `LABEL_TO_DETAIL` |
| `lib/aws/s3.py` | `S3.get_bytes`, `S3.upload_bytes` |

### Storage

The pull request contains Python and Markdown. You upload the frames, the fitted models, and the prediction files to S3 under the prefix below. A local `outputs/` directory is gitignored, on the same pattern as the feature experiment.

## File structure

### Repository

```text
docs/plans/2026-10-08_train_linear_model_on_llm_features_50850f/
  proposal.md                         this proposal

experiments/train_linear_model_on_llm_generated_features_2026_10_07/
  README.md                           title, plus pointers to SETUP.md and RESULTS.md
  SETUP.md                            source tables, feature object, and output keys
  RESULTS.md                          metric tables written by part 4
  .gitignore                          ignores outputs/
  __init__.py
  shared/
    __init__.py
    constants.py                      experiment name, S3 prefix, seed, test fraction, 0.5 cutoff
  src/
    __init__.py
    part1_load_data/
      __init__.py
      load.py                         draw the holdout, join features, write train and test frames
    part2_fit_logistic_model/
      __init__.py
      fit.py                          fit and save the logistic regression
    part3_fit_linear_regression_model/
      __init__.py
      fit.py                          fit and save the linear regression
    part4_analyze/
      __init__.py
      analyze.py                      score both models and write RESULTS.md
```

`experiments/study_2_llm_based_feature_extraction_2026_09_29/`, `shared/data/registry.py`, and `shared/utils/upsample.py` stay unchanged. The issue's folder name keeps the date `2026_10_07`.

### S3

```text
s3://mirrorview-experimental-artifacts/experiments/train_linear_model_on_llm_generated_features_2026_10_07/
  data/
    train.parquet                     upsampled rows outside the holdout, plus the 30 features
    test.parquet                      regular rows inside the holdout, plus the 30 features
    split_manifest.json               seed, counts, feature key, and sorted test post ids
  models/
    logistic_regression.joblib
    linear_regression.joblib
  analysis/
    predictions.parquet               train and test scores for both models
    logistic_coefficients.csv
    linear_coefficients.csv
    logistic_metrics.csv
    linear_metrics.csv
```

## Schema and key interfaces

Each record below is a parquet, JSON, or CSV file. Part 1, part 2, and part 3 pass pandas frames and the fitted sklearn estimators.

| Record | Lives in | Role |
| --- | --- | --- |
| Modeling frame | `data/train.parquet` and `data/test.parquet` (**new**) | One modeling row per training or test observation. |
| Split manifest | `data/split_manifest.json` (**new**) | The holdout draw and the feature object it joined. |
| Prediction frame | `analysis/predictions.parquet` (**new**) | One score row per train row and per test row. |
| Coefficient table | `analysis/logistic_coefficients.csv` and `analysis/linear_coefficients.csv` (**new**) | One weight per feature, plus the intercept. |
| `LogisticRegression` | `sklearn.linear_model` (**reused**) | Saved at `models/logistic_regression.joblib`. |
| `LinearRegression` | `sklearn.linear_model` (**reused**) | Saved at `models/linear_regression.joblib`. |

The modeling frame stores `post_id`, `keep_remove_label`, `n_remove`, `n_raters`, `remove_proportion`, and the 30 feature columns. The post text and the other source columns stay in the registered CSVs and in the feature parquet.

The split manifest stores `seed`, `test_fraction`, `class_order`, `train_dataset`, `test_dataset`, `feature_object_key`, `feature_columns`, `train_row_count`, `test_row_count`, and `test_post_ids`. `test_post_ids` is sorted, so a later run can check the draw without depending on a future NumPy change.

The prediction frame stores `post_id`, `split`, `y_remove`, `p_remove`, `yhat_remove`, `y_proportion`, `yhat_proportion_raw`, and `yhat_proportion_clipped`. `split` is `train` or `test`.

Each coefficient CSV stores `feature` and `coefficient`. The intercept is a row whose `feature` is `intercept`. You look up the readable name in `LABEL_TO_DETAIL` while you write `RESULTS.md`.

```python
def build_frames() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return the train frame, the test frame, and the split manifest."""

def fit_logistic(train: pd.DataFrame) -> LogisticRegression:
    """Fit the modal-label logistic regression on the train frame."""

def fit_linear(train: pd.DataFrame) -> LinearRegression:
    """Fit the remove-proportion linear regression on the train frame."""

def write_results(
    train: pd.DataFrame,
    test: pd.DataFrame,
    logistic: LogisticRegression,
    linear: LinearRegression,
) -> None:
    """Score both frames and write the analysis objects and RESULTS.md."""
```

## Steps

### Step 1: Join the split posts to the feature table

You load the two registered label tables, and you download the feature parquet. You draw the test post ids and join the 30 feature columns. You then upload `train.parquet`, `test.parquet`, and `split_manifest.json`.

### Step 2: Fit the logistic regression

You load `train.parquet` and fit `LogisticRegression` on the 30 feature columns and `keep_remove_label`. You then upload `logistic_regression.joblib`.

### Step 3: Fit the linear regression

You load the same train frame and fit `LinearRegression` on the 30 feature columns and `remove_proportion`. You then upload `linear_regression.joblib`. You limit a prediction to 0 through 1 when you score the model.

### Step 4: Score both models and write the tables

You score the train frame and the test frame. You upload the prediction parquet, the coefficient CSVs, and the metric CSVs. You also write the metrics into `RESULTS.md`. You report accuracy, precision, recall, and F1 on the test posts, with remove as the positive class, because the zero-shot and few-shot Study 2 tables report those four metrics the same way. You also write the train metrics, so the fitting-row scores sit beside the held-out scores.

## Expected results

The numbers below come from an uncommitted prototype that I ran on October 8, 2026. The prototype used the holdout, the 30 binary columns, and the two estimators named above. Downloading the tables and fitting both models took 5.1 seconds. There is no paid model call, so the token count is 0 and the model cost is $0. The later S3 uploads were outside that timing.

| Model | Split | Accuracy | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| Logistic regression | Train | 0.6798 | 0.6688 | 0.7138 | 0.6905 |
| Logistic regression | Test | 0.6549 | 0.4154 | 0.7105 | 0.5243 |

The test accuracy of 0.6549 is below the 0.7324 accuracy of always predicting keep. The test remove F1 of 0.5243 is above the 0 F1 of the constant keep prediction.

| Model | Split | MAE | RMSE | R^2 | Predictions outside 0 to 1 |
| --- | --- | ---: | ---: | ---: | ---: |
| Linear regression | Train | 0.1598 | 0.1902 | 0.2092 | 0 of 11,663 |
| Linear regression | Test | 0.1624 | 0.1907 | 0.0497 | 0 of 1,988 |

The clipped and unclipped linear scores are the same, because no prototype prediction fell outside 0 to 1. A later fit can still produce a value outside that range, and the stored clipped column is the one `RESULTS.md` reports.

## Decisions to confirm

1. **Hold out 20 percent of the unique posts in each modal class, with seed 1.** The upsampled table already contains every regular post, so fitting on all 14,562 upsampled rows and scoring all 9,941 regular rows scores posts the model has seen. The holdout above leaves 11,663 train rows and 1,988 test rows, with no shared `post_id`. The same prototype, fit on every upsampled row and scored on every regular row, had test accuracy 0.6627 and test remove F1 0.5266. The alternative is the full-table fit.
2. **Use the 30 binary columns in `post_feature_labels.parquet`.** The 30 columns are the feature labels from PR 323. They match `LABEL_TO_DETAIL`, and every split post joins. The alternative is the Jev probabilities in `jev_probabilities.parquet`, which is 1,011,383 bytes in the same folder.
3. **Fit `LinearRegression` and limit scored predictions to 0 through 1.** Issue 358 asks for a linear regression of the remove proportion. On the prototype the limit changed no score. The alternative is a binomial GLM from `statsmodels`, which keeps the fitted mean inside 0 to 1 during fitting and is a different model.
