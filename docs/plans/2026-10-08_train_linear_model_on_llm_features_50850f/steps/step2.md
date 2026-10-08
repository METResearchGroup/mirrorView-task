# Step 2: Fit the logistic regression

## Proposal sections implemented

- Models, logistic regression
- Schema and key interfaces, `fit_logistic`
- Step 2, Fit the logistic regression

## Scope

- Caller: `experiments.train_linear_model_on_llm_generated_features_2026_10_07.src.part2_fit_logistic_model.fit.main`
- Task: Fit the confirmed logistic regression on the train frame from step 1 and upload the saved estimator.
- Out of scope: the linear regression, metric tables, and `RESULTS.md`.

## Files to inspect

- `/workspace/docs/plans/2026-10-08_train_linear_model_on_llm_features_50850f/proposal.md`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/shared/constants.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part1_load_data/load.py`
- `/workspace/experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/model.py`

## Files allowed to change

- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part2_fit_logistic_model/__init__.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part2_fit_logistic_model/fit.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests/test_logistic.py`

## Files forbidden to change

- `/workspace/experiments/simplified_predict_remove_2026_05_13/models/logistic_regression/model.py`
- `/workspace/experiments/train_linear_model_on_llm_generated_features_2026_10_07/src/part1_load_data/load.py`
- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`
- `/workspace/pyproject.toml`

## Contract

`fit_logistic(train: pd.DataFrame) -> LogisticRegression` reads the step 1 train frame. It does not read S3 and does not reorder rows.

The estimator is `sklearn.linear_model.LogisticRegression(solver="lbfgs", max_iter=1000, random_state=1)` with `class_weight` left unset. The feature matrix is `train.loc[:, FEATURE_COLUMNS]` as `int8`. The target is `train["keep_remove_label"]` as `int`.

`hard_remove_label(estimator, frame) -> np.ndarray` returns 1 when `predict_proba` for class 1 is greater than or equal to `LOGISTIC_THRESHOLD`, and 0 otherwise. Do not use `LogisticRegression.predict` for the stored hard label.

`main` loads `outputs/data/train.parquet` if it exists, otherwise downloads `S3_PREFIX + "data/train.parquet"`. It fits, writes `outputs/models/logistic_regression.joblib` with `joblib.dump`, and uploads that file to `S3_PREFIX + "models/logistic_regression.joblib"`, overwriting an existing object.

`main` prints one line. The four numbers are Python `round(value, 4)` on the train frame, using the 0.5 hard label:

```text
logistic_train_accuracy=0.6798 logistic_train_precision=0.6688 logistic_train_recall=0.7138 logistic_train_f1=0.6905 logistic_n_iter=24
```

Precision, recall, and F1 use `pos_label=1` and `zero_division=0`.

## Tests

Write `tests/test_logistic.py` first. Use a tiny frame with two separable binary columns so the test does not need S3.

The tests must show:

- `class_weight` is `None`, `solver` is `lbfgs`, `random_state` is 1, and `max_iter` is 1000.
- A probability of exactly 0.5 becomes hard label 1. Construct that case by calling `hard_remove_label` with a stub estimator whose `predict_proba` returns `[[0.5, 0.5]]` and whose `classes_` is `[0, 1]`.
- A probability of 0.49 becomes hard label 0.
- The feature matrix keeps the caller row order. A frame with duplicate `post_id` values still has one training row per input row.

## Implementation order

1. Add the failing tests and the empty package marker. Commit.
2. Implement `fit_logistic`, `hard_remove_label`, and `main`. Commit.

Suggested commit messages are `test: cover the modal-label logistic fit` and `feat: fit the modal-label logistic regression`.

## Verification

Run from `/workspace`:

```bash
PYTHONPATH=. uv run pytest experiments/train_linear_model_on_llm_generated_features_2026_10_07/tests/test_logistic.py -q
```

Expected: all tests passed, exit code 0.

Then, after step 1 has written the train frame:

```bash
PYTHONPATH=. uv run python -m experiments.train_linear_model_on_llm_generated_features_2026_10_07.src.part2_fit_logistic_model.fit
```

Expected stdout is exactly:

```text
logistic_train_accuracy=0.6798 logistic_train_precision=0.6688 logistic_train_recall=0.7138 logistic_train_f1=0.6905 logistic_n_iter=24
```

Fail the step if the line differs or if `LogisticRegressionKeepRemoveModel` is imported.
