# Step 3: Fit the linear regression

## Proposal sections implemented

- Models, linear regression
- Schema and key interfaces, `fit_linear`
- Step 3, Fit the linear regression

## Scope

- Caller: `experiments.train_linear_model_on_llm_generated_features_2026_10_07.src.part3_fit_linear_regression_model.fit.main`
- Task: Fit the confirmed linear regression on the same train frame and upload the saved estimator.
- Out of scope: logistic fitting, metric tables, and `RESULTS.md`. The 0 to 1 limit is applied by the scorer in step 4, not during this fit.

## Files to inspect

- `/workspace/docs/plans/2026-10-08_train_linear_model_on_llm_features_50850f/proposal.md`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/shared/constants.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part1_load_data/load.py`

## Files allowed to change

- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part3_fit_linear_regression_model/__init__.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part3_fit_linear_regression_model/fit.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests/test_linear.py`

## Files forbidden to change

- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part1_load_data/load.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part2_fit_logistic_model/fit.py`
- `/workspace/pyproject.toml`
- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`

## Contract

`fit_linear(train: pd.DataFrame) -> LinearRegression` uses `sklearn.linear_model.LinearRegression(fit_intercept=True)`. The feature matrix is `train.loc[:, FEATURE_COLUMNS]` as `float`. The target is `train["remove_proportion"]` as `float`. Do not reorder rows. Do not clip inside `fit_linear`.

`main` loads the same train parquet as step 2, local file first and S3 second. It writes `outputs/models/linear_regression.joblib` with `joblib.dump` and uploads it to `S3_PREFIX + "models/linear_regression.joblib"`, overwriting an existing object.

`main` prints the unclipped train scores. MAE, RMSE, and R^2 use `sklearn.metrics.mean_absolute_error`, `sklearn.metrics.root_mean_squared_error`, and `sklearn.metrics.r2_score`. Each displayed number is Python `round(value, 4)`. `outside` counts predictions strictly below 0 or strictly above 1.

```text
linear_train_mae=0.1598 linear_train_rmse=0.1902 linear_train_r2=0.2092 linear_train_outside=0
```

## Tests

Write `tests/test_linear.py` first. Use an in-memory frame whose `remove_proportion` is a known linear function of one feature column, with the other feature columns set to 0.

The tests must show:

- `fit_intercept` is `True`.
- The fitted prediction on the training rows matches the constructed target within `1e-8`.
- `fit_linear` returns the raw estimator prediction. A target outside 0 to 1 is allowed in this unit test, and the returned prediction is not clipped.
- Duplicate input rows remain duplicate training rows.

## Implementation order

1. Add the failing tests and the empty package marker. Commit.
2. Implement `fit_linear` and `main`. Commit.

Suggested commit messages are `test: cover the remove-share linear fit` and `feat: fit the remove-share linear regression`.

## Verification

Run from `/workspace`:

```bash
PYTHONPATH=. uv run pytest experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests/test_linear.py -q
```

Expected: all tests passed, exit code 0.

Then, after step 1 has written the train frame:

```bash
PYTHONPATH=. uv run python -m experiments.train_linear_model_on_llm_generated_features_2026_10_07.src.part3_fit_linear_regression_model.fit
```

Expected stdout is exactly:

```text
linear_train_mae=0.1598 linear_train_rmse=0.1902 linear_train_r2=0.2092 linear_train_outside=0
```

Fail the step if the line differs or if `statsmodels` is imported.
