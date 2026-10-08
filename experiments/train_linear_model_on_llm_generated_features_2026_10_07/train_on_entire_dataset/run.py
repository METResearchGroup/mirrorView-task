"""Fit both regressions on every upsampled split row and score every regular split row.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.run
"""

from __future__ import annotations

import json
from io import BytesIO

import joblib
import pandas as pd

from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.constants import (
    FEATURE_COLUMNS,
    FEATURE_OBJECT_KEY,
    ID_COLUMN,
    LABEL_COLUMN,
    OUTPUT_DIR,
    PACKAGE_DIR,
    PROPORTION_COLUMN,
    S3_BUCKET,
    S3_PREFIX,
)
from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.frames import (
    modeling_frame,
)
from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.models import (
    clip_proportion,
    coefficient_frame,
    fit_linear,
    fit_logistic,
    hard_remove_label,
    linear_metrics,
    logistic_metrics,
    remove_probability,
)
from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.report import (
    render_results,
)
from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from shared.data.dataloader import _use_lab_credentials_when_unset, load_dataset
from shared.data.registry import (
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
)

RESULTS_PATH = PACKAGE_DIR / "RESULTS.md"
TOP_COEFFICIENTS = 10


def prediction_frame(split_name: str, frame: pd.DataFrame, logistic, linear) -> pd.DataFrame:
    """Return one score row per modeling row, in the modeling-frame order."""
    raw = linear.predict(frame.loc[:, list(FEATURE_COLUMNS)].to_numpy(dtype=float))
    return pd.DataFrame(
        {
            ID_COLUMN: frame[ID_COLUMN].astype(str),
            "split": split_name,
            "y_remove": frame[LABEL_COLUMN].astype(int).to_numpy(),
            "p_remove": remove_probability(logistic, frame),
            "yhat_remove": hard_remove_label(logistic, frame),
            "y_proportion": frame[PROPORTION_COLUMN].astype(float).to_numpy(),
            "yhat_proportion_raw": raw,
            "yhat_proportion_clipped": clip_proportion(raw),
        }
    )


def largest_coefficients(frame: pd.DataFrame, limit: int = TOP_COEFFICIENTS) -> list[tuple[str, float]]:
    """Return the intercept, then the features with the largest absolute weights."""
    intercept = frame.loc[frame["feature"].eq("intercept")].iloc[0]
    weights = frame.loc[~frame["feature"].eq("intercept")].copy()
    weights["absolute"] = weights["coefficient"].abs()
    weights = weights.sort_values(["absolute", "feature"], ascending=[False, True])
    chosen = [(str(intercept["feature"]), float(intercept["coefficient"]))]
    for row in weights.head(limit).itertuples(index=False):
        chosen.append((str(row.feature), float(row.coefficient)))
    return chosen


def main() -> None:
    """Load both full tables, fit both models, write RESULTS.md, and upload artifacts."""
    _use_lab_credentials_when_unset()
    train = modeling_frame(
        load_dataset(UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS, low_memory=False),
        _load_features(),
    )
    test = modeling_frame(
        load_dataset(STUDY_2_KEEP_REMOVE_SPLIT_LABELS, low_memory=False),
        _load_features(),
    )
    logistic = fit_logistic(train)
    linear = fit_linear(train)
    train_predictions = prediction_frame("train", train, logistic, linear)
    test_predictions = prediction_frame("test", test, logistic, linear)
    logistic_train = logistic_metrics(
        train_predictions["y_remove"].to_numpy(),
        train_predictions["yhat_remove"].to_numpy(),
    )
    logistic_test = logistic_metrics(
        test_predictions["y_remove"].to_numpy(),
        test_predictions["yhat_remove"].to_numpy(),
    )
    linear_train = linear_metrics(
        train_predictions["y_proportion"].to_numpy(),
        train_predictions["yhat_proportion_raw"].to_numpy(),
    )
    linear_test = linear_metrics(
        test_predictions["y_proportion"].to_numpy(),
        test_predictions["yhat_proportion_raw"].to_numpy(),
    )
    logistic_coefficients = coefficient_frame(
        FEATURE_COLUMNS,
        float(logistic.intercept_[0]),
        logistic.coef_[0],
    )
    linear_coefficients = coefficient_frame(
        FEATURE_COLUMNS,
        float(linear.intercept_),
        linear.coef_,
    )
    shared_posts = len(set(test[ID_COLUMN].astype(str)) & set(train[ID_COLUMN].astype(str)))
    results = render_results(
        train_rows=len(train),
        test_rows=len(test),
        train_keep=int(train[LABEL_COLUMN].eq(0).sum()),
        train_remove=int(train[LABEL_COLUMN].eq(1).sum()),
        test_keep=int(test[LABEL_COLUMN].eq(0).sum()),
        test_remove=int(test[LABEL_COLUMN].eq(1).sum()),
        shared_posts=shared_posts,
        logistic_train=logistic_train,
        logistic_test=logistic_test,
        linear_train=linear_train,
        linear_test=linear_test,
        logistic_coefficients=largest_coefficients(logistic_coefficients),
        linear_coefficients=largest_coefficients(linear_coefficients),
    )
    RESULTS_PATH.write_text(results, encoding="utf-8")
    _write_outputs(
        train,
        test,
        train_predictions,
        test_predictions,
        logistic,
        linear,
        logistic_coefficients,
        linear_coefficients,
        logistic_train,
        logistic_test,
        linear_train,
        linear_test,
    )
    print(
        "logistic_test_accuracy="
        f"{logistic_test['accuracy']:.4f} "
        "logistic_test_precision="
        f"{logistic_test['precision']:.4f} "
        "logistic_test_recall="
        f"{logistic_test['recall']:.4f} "
        "logistic_test_f1="
        f"{logistic_test['f1']:.4f} "
        "linear_test_mae="
        f"{linear_test['mae']:.4f} "
        "linear_test_rmse="
        f"{linear_test['rmse']:.4f} "
        "linear_test_r2="
        f"{linear_test['r2']:.4f} "
        f"linear_test_outside={int(linear_test['outside_count'])} "
        f"shared_posts={shared_posts}"
    )


def _load_features() -> pd.DataFrame:
    store = S3(S3_BUCKET, region_name=DEFAULT_REGION_NAME)
    return pd.read_parquet(BytesIO(store.get_bytes(FEATURE_OBJECT_KEY)))


def _write_outputs(
    train: pd.DataFrame,
    test: pd.DataFrame,
    train_predictions: pd.DataFrame,
    test_predictions: pd.DataFrame,
    logistic,
    linear,
    logistic_coefficients: pd.DataFrame,
    linear_coefficients: pd.DataFrame,
    logistic_train: dict[str, float],
    logistic_test: dict[str, float],
    linear_train: dict[str, float],
    linear_test: dict[str, float],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "data/train.parquet": _parquet_bytes(train),
        "data/test.parquet": _parquet_bytes(test),
        "analysis/predictions.parquet": _parquet_bytes(
            pd.concat([train_predictions, test_predictions], ignore_index=True)
        ),
        "analysis/logistic_coefficients.csv": _csv_bytes(logistic_coefficients),
        "analysis/linear_coefficients.csv": _csv_bytes(linear_coefficients),
        "analysis/logistic_metrics.json": _json_bytes({"train": logistic_train, "test": logistic_test}),
        "analysis/linear_metrics.json": _json_bytes({"train": linear_train, "test": linear_test}),
        "models/logistic_regression.joblib": _joblib_bytes(logistic),
        "models/linear_regression.joblib": _joblib_bytes(linear),
    }
    store = S3(S3_BUCKET, region_name=DEFAULT_REGION_NAME)
    for relative_key, body in files.items():
        path = OUTPUT_DIR / relative_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        store.upload_bytes(f"{S3_PREFIX}{relative_key}", body)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def _joblib_bytes(estimator) -> bytes:
    buffer = BytesIO()
    joblib.dump(estimator, buffer)
    return buffer.getvalue()


if __name__ == "__main__":
    main()
