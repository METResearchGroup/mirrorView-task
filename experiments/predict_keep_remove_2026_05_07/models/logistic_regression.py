from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

# Basic analysis-label feature set. Keep this explicit so it is easy to reorder/tweak.
DEFAULT_FEATURE_COLUMNS: tuple[str, ...] = (
    "intergroup_clf_is_intergroup_original_text",
    "intergroup_clf_is_intergroup_mirrors",
    "prime_clf_is_prime_original_text",
    "prime_clf_is_prime_mirrors",
    "valence_clf_is_positive_original_text",
    "valence_clf_is_positive_mirrors",
    "length_compression_char_count_original_text",
    "length_compression_word_count_original_text",
    "length_compression_sentence_count_original_text",
    "length_compression_avg_sentence_length_original_text",
    "length_compression_punctuation_count_original_text",
    "length_compression_punctuation_density_original_text",
    "length_compression_char_count_mirrors",
    "length_compression_word_count_mirrors",
    "length_compression_sentence_count_mirrors",
    "length_compression_avg_sentence_length_mirrors",
    "length_compression_punctuation_count_mirrors",
    "length_compression_punctuation_density_mirrors",
    "readability_complexity_flesch_kincaid_grade_original_text",
    "readability_complexity_flesch_reading_ease_original_text",
    "readability_complexity_flesch_kincaid_grade_mirrors",
    "readability_complexity_flesch_reading_ease_mirrors",
    "sample_toxicity_type",
    "sampled_stance",
)


class LogisticRegressionModel:
    """Strategy for training and evaluating logistic regression on keep/remove."""

    model_name = "logistic_regression"

    def __init__(
        self,
        *,
        feature_columns: tuple[str, ...] = DEFAULT_FEATURE_COLUMNS,
        max_iter: int = 2000,
        random_state: int = 42,
    ) -> None:
        self.feature_columns = feature_columns
        self.max_iter = max_iter
        self.random_state = random_state
        self._encoded_feature_columns: list[str] | None = None

    def train(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        *,
        output_dir: Path,
        target_column: str = "keep_remove_label",
    ) -> dict[str, Any]:
        missing = [c for c in self.feature_columns if c not in train_df.columns]
        if missing:
            raise KeyError(f"Missing feature columns in train dataframe: {missing}")
        if target_column not in train_df.columns or target_column not in test_df.columns:
            raise KeyError(f"Missing target column: {target_column}")

        X_train = self._featurize_train(train_df)
        X_test = self._featurize_infer(test_df)
        y_train = train_df[target_column].astype(int)
        y_test = test_df[target_column].astype(int)

        model = LogisticRegression(
            max_iter=self.max_iter,
            random_state=self.random_state,
            solver="liblinear",
        )
        model.fit(X_train, y_train)

        y_pred_train = model.predict(X_train)
        y_prob_train = model.predict_proba(X_train)[:, 1]
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]

        train_metrics = {
            "accuracy": float(accuracy_score(y_train, y_pred_train)),
            "precision": float(precision_score(y_train, y_pred_train, zero_division=0)),
            "recall": float(recall_score(y_train, y_pred_train, zero_division=0)),
            "f1": float(f1_score(y_train, y_pred_train, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_train, y_prob_train)),
        }
        test_metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_prob)),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "model.pkl"
        with model_path.open("wb") as f:
            pickle.dump(model, f)

        if self._encoded_feature_columns is None:
            raise RuntimeError("Encoded feature columns were not recorded during train featurization.")

        coefficients = pd.DataFrame(
            {
                "feature": self._encoded_feature_columns,
                "coefficient": model.coef_[0].tolist(),
            }
        ).sort_values("coefficient", ascending=False)
        coefficients_path = output_dir / "feature_coefficients.csv"
        coefficients.to_csv(coefficients_path, index=False)

        predictions = test_df[["post_id", "decision", target_column]].copy()
        predictions["predicted_label"] = y_pred.astype(int)
        predictions["predicted_keep_probability"] = y_prob
        predictions_path = output_dir / "test_predictions.csv"
        predictions.to_csv(predictions_path, index=False)

        artifacts = {
            "model_path": str(model_path),
            "feature_coefficients_path": str(coefficients_path),
            "test_predictions_path": str(predictions_path),
        }

        report = {
            "model_name": self.model_name,
            "feature_columns": list(self.feature_columns),
            "target_column": target_column,
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "artifacts": artifacts,
        }
        report_path = output_dir / "training_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        artifacts["training_report_path"] = str(report_path)

        return {
            "model_name": self.model_name,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "artifacts": artifacts,
            "train_rows": int(len(train_df)),
            "test_rows": int(len(test_df)),
        }

    def _featurize_train(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df.loc[:, self.feature_columns].copy()
        X = pd.get_dummies(X, columns=["sample_toxicity_type", "sampled_stance"], dummy_na=False)
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors="coerce")
        X = X.fillna(0.0)
        self._encoded_feature_columns = list(X.columns)
        return X

    def _featurize_infer(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._encoded_feature_columns is None:
            raise RuntimeError("Train featurization must run before inference featurization.")

        X = df.loc[:, self.feature_columns].copy()
        X = pd.get_dummies(X, columns=["sample_toxicity_type", "sampled_stance"], dummy_na=False)
        X = X.reindex(columns=self._encoded_feature_columns, fill_value=0.0)
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors="coerce")
        X = X.fillna(0.0)
        return X
