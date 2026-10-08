# Step 4: Score both models and write the tables

## Proposal sections implemented

- Models, the 0 to 1 limit and the positive class
- Schema and key interfaces, prediction frame and coefficient tables
- Step 4, Score both models and write the tables
- Expected results

## Scope

- Caller: `experiments.train_linear_model_on_llm_generated_features_2026_10_07.src.part4_analyze.analyze.main`
- Task: Score the train and test frames with both saved estimators, upload the analysis files, and write `RESULTS.md`.
- Out of scope: refitting either model and changing the holdout.

## Files to inspect

- `/workspace/docs/plans/2026-10-08_train_linear_model_on_llm_features_50850f/proposal.md`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part2_fit_logistic_model/fit.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part3_fit_linear_regression_model/fit.py`
- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py`

## Files allowed to change

- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part4_analyze/__init__.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part4_analyze/analyze.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/RESULTS.md`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests/test_analyze.py`

## Files forbidden to change

- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part1_load_data/load.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part2_fit_logistic_model/fit.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part3_fit_linear_regression_model/fit.py`
- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py`

## Contract

`score_frames(train, test, logistic, linear) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]` returns the prediction frame, the logistic metric frame, and the linear metric frame. It does not read S3 and does not refit.

The prediction frame has one row per train row and one row per test row, train rows first, with the source row order inside each split. Columns are `post_id`, `split`, `y_remove`, `p_remove`, `yhat_remove`, `y_proportion`, `yhat_proportion_raw`, and `yhat_proportion_clipped`.

`yhat_remove` uses `hard_remove_label` from step 2. `yhat_proportion_raw` is `LinearRegression.predict`. `yhat_proportion_clipped` is `numpy.clip(raw, 0.0, 1.0)`.

The logistic metric frame has one train row and one test row. Columns are `split`, `sample_count`, `accuracy`, `precision`, `recall`, `f1`, and `constant_keep_accuracy`. Precision, recall, and F1 use `pos_label=1` and `zero_division=0`. `constant_keep_accuracy` is the share of rows whose `y_remove` is 0.

The linear metric frame has one train row and one test row. Columns are `split`, `sample_count`, `mae`, `rmse`, `r2`, and `outside_count`. MAE, RMSE, and R^2 are computed on `yhat_proportion_clipped`. `outside_count` counts raw predictions strictly below 0 or strictly above 1.

Coefficient frames have columns `feature` and `coefficient`. The first data row is `intercept`. The remaining rows follow `FEATURE_COLUMNS`. Logistic coefficients are `estimator.coef_[0]`. Linear coefficients are `estimator.coef_`.

`main` loads local parquet and joblib files when they exist, and otherwise downloads the step 1 through step 3 keys. It writes and uploads:

- `analysis/predictions.parquet`
- `analysis/logistic_coefficients.csv`
- `analysis/linear_coefficients.csv`
- `analysis/logistic_metrics.csv`
- `analysis/linear_metrics.csv`

Uploads overwrite existing objects. `main` then replaces `RESULTS.md` with the tables below. Readable feature names in that file come from `LABEL_TO_DETAIL` at write time. They are not stored in the coefficient CSV.

`main` prints:

```text
logistic_test_accuracy=0.6549 logistic_test_precision=0.4154 logistic_test_recall=0.7105 logistic_test_f1=0.5243 linear_test_mae=0.1624 linear_test_rmse=0.1907 linear_test_r2=0.0497 linear_test_outside=0
```

Each decimal is Python `round(value, 4)`.

`RESULTS.md` must contain:

- A logistic table with the train row accuracy 0.6798, precision 0.6688, recall 0.7138, F1 0.6905, and the test row accuracy 0.6549, precision 0.4154, recall 0.7105, F1 0.5243.
- The sentence that test accuracy 0.6549 is below the constant-keep accuracy 0.7324, and that test remove F1 0.5243 is above the constant-keep F1 of 0.
- A linear table with train MAE 0.1598, RMSE 0.1902, R^2 0.2092, and test MAE 0.1624, RMSE 0.1907, R^2 0.0497.
- The outside counts 0 of 11,663 train predictions and 0 of 1,988 test predictions.
- The ten logistic coefficients and ten linear coefficients with the largest absolute value, with the `LABEL_TO_DETAIL` name beside the column key.

## Tests

Write `tests/test_analyze.py` first. Build a two-row train frame and a two-row test frame, fit both estimators on the train frame, and call `score_frames`.

The tests must show:

- The prediction frame has train rows before test rows, and `split` is only `train` or `test`.
- A raw prediction of -0.2 is stored as -0.2 and clipped to 0. A raw prediction of 1.2 is stored as 1.2 and clipped to 1. Use a stub linear estimator for this case.
- Logistic F1 on a hand-built confusion matrix matches `sklearn.metrics.f1_score` with `pos_label=1` and `zero_division=0`.
- `constant_keep_accuracy` on labels `[0, 0, 1]` is `2 / 3`.
- The intercept is the first coefficient row, and there is one later row per feature column.

## Implementation order

1. Add the failing tests and the empty package marker. Commit.
2. Implement `score_frames` and the coefficient builder. Commit.
3. Implement `main`, the S3 uploads, and the `RESULTS.md` writer. Commit.

Suggested commit messages are `test: cover regression scoring`, `feat: score the two feature regressions`, and `feat: publish the feature regression results`.

## Verification

Run from `/workspace`:

```bash
PYTHONPATH=. uv run pytest experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests -q
```

Expected: all experiment tests passed, exit code 0.

Then, after steps 1 through 3 have written their outputs:

```bash
PYTHONPATH=. uv run python -m experiments.train_linear_model_on_llm_generated_features_2026_10_07.src.part4_analyze.analyze
```

Expected stdout is exactly:

```text
logistic_test_accuracy=0.6549 logistic_test_precision=0.4154 logistic_test_recall=0.7105 logistic_test_f1=0.5243 linear_test_mae=0.1624 linear_test_rmse=0.1907 linear_test_r2=0.0497 linear_test_outside=0
```

Also require `git check-ignore -v experiments/train_linear_model_on_llm_generated_features_2026_10_07/outputs/data/train.parquet` to report the experiment `.gitignore`. Fail the step if `RESULTS.md` lacks the constant-keep accuracy 0.7324, or if a forbidden file changed.
