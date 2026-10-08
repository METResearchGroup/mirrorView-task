"""Render the full-table regression scores as markdown."""

from __future__ import annotations

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.label_to_detail import (
    LABEL_TO_DETAIL,
)


def _four(value: float) -> str:
    return f"{value:.4f}"


def _count(value: float) -> str:
    return f"{int(value):,}"


def render_results(
    train_rows: int,
    test_rows: int,
    train_keep: int,
    train_remove: int,
    test_keep: int,
    test_remove: int,
    shared_posts: int,
    logistic_train: dict[str, float],
    logistic_test: dict[str, float],
    linear_train: dict[str, float],
    linear_test: dict[str, float],
    logistic_coefficients: list[tuple[str, float]],
    linear_coefficients: list[tuple[str, float]],
) -> str:
    """Return the RESULTS.md body for the full split-label tables."""
    logistic_table = _logistic_table(logistic_train, logistic_test)
    linear_table = _linear_table(linear_train, linear_test)
    return "\n".join(
        [
            "# Train and test on the entire split-label tables",
            "",
            "Training uses every row of `UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS`. Testing uses every row of `STUDY_2_KEEP_REMOVE_SPLIT_LABELS`. Every row in both tables has five labelers and 1, 2, 3, or 4 remove votes. The predictors are the 30 binary columns in `post_feature_labels.parquet`.",
            "",
            f"The train table has {train_rows:,} rows, {train_keep:,} keep and {train_remove:,} remove. The test table has {test_rows:,} rows, {test_keep:,} keep and {test_remove:,} remove. The upsampled table already contains every regular post, so all {shared_posts:,} test posts also appear in training.",
            "",
            "## Logistic regression",
            "",
            "The positive class is remove. A row is predicted remove when the remove probability is at least 0.5.",
            "",
            logistic_table,
            "",
            (
                f"A prediction that always says keep is correct on {test_keep:,} of the {test_rows:,} test posts, "
                f"so its accuracy is {_four(logistic_test['constant_keep_accuracy'])}. "
                f"Its remove F1 is 0. The fitted test accuracy is {_four(logistic_test['accuracy'])}, "
                f"and the fitted test F1 is {_four(logistic_test['f1'])}."
            ),
            "",
            "## Linear regression",
            "",
            "The target is `n_remove / n_raters`. MAE, RMSE, and R^2 use predictions limited to the range 0 to 1. `outside` counts raw predictions below 0 or above 1.",
            "",
            linear_table,
            "",
            "## Largest logistic coefficients",
            "",
            _coefficient_table(logistic_coefficients),
            "",
            "## Largest linear coefficients",
            "",
            _coefficient_table(linear_coefficients),
            "",
        ]
    )


def _logistic_table(train: dict[str, float], test: dict[str, float]) -> str:
    header = "| Split | Rows | Accuracy | Precision | Recall | F1 |"
    rule = "| --- | ---: | ---: | ---: | ---: | ---: |"
    return "\n".join([header, rule, _logistic_row("Train", train), _logistic_row("Test", test)])


def _logistic_row(name: str, metrics: dict[str, float]) -> str:
    return (
        f"| {name} | {_count(metrics['sample_count'])} | {_four(metrics['accuracy'])} "
        f"| {_four(metrics['precision'])} | {_four(metrics['recall'])} | {_four(metrics['f1'])} |"
    )


def _linear_table(train: dict[str, float], test: dict[str, float]) -> str:
    header = "| Split | Rows | MAE | RMSE | R^2 | Outside 0 to 1 |"
    rule = "| --- | ---: | ---: | ---: | ---: | ---: |"
    return "\n".join([header, rule, _linear_row("Train", train), _linear_row("Test", test)])


def _linear_row(name: str, metrics: dict[str, float]) -> str:
    outside = f"{int(metrics['outside_count']):,} of {_count(metrics['sample_count'])}"
    return (
        f"| {name} | {_count(metrics['sample_count'])} | {_four(metrics['mae'])} "
        f"| {_four(metrics['rmse'])} | {_four(metrics['r2'])} | {outside} |"
    )


def _coefficient_table(rows: list[tuple[str, float]]) -> str:
    lines = ["| Feature | Name | Coefficient |", "| --- | --- | ---: |"]
    for feature, coefficient in rows:
        name = "Intercept" if feature == "intercept" else LABEL_TO_DETAIL[feature]["name"]
        lines.append(f"| `{feature}` | {name} | {coefficient:.4f} |")
    return "\n".join(lines)
