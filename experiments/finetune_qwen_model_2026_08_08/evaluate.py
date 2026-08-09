"""Score baseline vs fine-tuned prediction CSVs into RESULTS.md.

Invalid predictions (``__invalid__`` / NA label) never count as correct:
for scoring only, effective ``y_pred`` is flipped vs gold.

Positive class for precision / recall / F1 is remove (``keep_remove_label=1``).

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/finetune_qwen_model_2026_08_08/evaluate.py \\
      --preds-dir experiments/finetune_qwen_model_2026_08_08/preds \\
      --write-results experiments/finetune_qwen_model_2026_08_08/RESULTS.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import (
    INVALID_DECISION,
)
from experiments.finetune_qwen_model_2026_08_08.src.train_config import MODEL_ID

METRIC_KEYS = ("accuracy", "precision", "recall", "f1")
ARM_BASELINE = "baseline"
ARM_FINE_TUNED = "fine-tuned"
PRED_RELATIVE_PATHS = {
    ("train", ARM_BASELINE): Path("baseline") / "train_labels.csv",
    ("train", ARM_FINE_TUNED): Path("fine_tuned") / "train_labels.csv",
    ("test", ARM_BASELINE): Path("baseline") / "test_labels.csv",
    ("test", ARM_FINE_TUNED): Path("fine_tuned") / "test_labels.csv",
}


def effective_pred_labels(
    keep_remove_label: pd.Series,
    predicted_decision: pd.Series,
    predicted_label: pd.Series,
) -> list[int]:
    """Build scoring labels where invalid never equals gold.

    Parameters
    ----------
    keep_remove_label
        Gold labels (0 keep / 1 remove).
    predicted_decision
        Parsed decisions including ``__invalid__``.
    predicted_label
        Predicted 0/1 or NA/empty for invalid.

    Returns
    -------
    list[int]
        Effective ``y_pred`` for metric computation only.
    """
    y_pred: list[int] = []
    for gold, decision, pred in zip(
        keep_remove_label,
        predicted_decision,
        predicted_label,
        strict=True,
    ):
        gold_int = int(gold)
        decision_str = str(decision).strip().lower()
        pred_missing = pd.isna(pred) or str(pred).strip() == ""
        if decision_str == INVALID_DECISION or pred_missing:
            y_pred.append(1 - gold_int)
            continue
        y_pred.append(int(pred))
    return y_pred


def compute_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    """Compute accuracy / precision / recall / F1 (positive = remove)."""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def score_prediction_csv(path: Path) -> dict[str, float]:
    """Score one prediction CSV with invalid-as-wrong handling."""
    if not path.is_file():
        raise FileNotFoundError(f"Prediction CSV not found: {path}")
    frame = pd.read_csv(path)
    required = {
        "keep_remove_label",
        "predicted_decision",
        "predicted_label",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    y_true = [int(v) for v in frame["keep_remove_label"].tolist()]
    y_pred = effective_pred_labels(
        frame["keep_remove_label"],
        frame["predicted_decision"],
        frame["predicted_label"],
    )
    return compute_metrics(y_true, y_pred)


def format_metric(value: float) -> str:
    """Format a metric to four decimal places."""
    return f"{value:.4f}"


def render_results_markdown(
    train_metrics: dict[str, dict[str, float]],
    test_metrics: dict[str, dict[str, float]],
) -> str:
    """Render RESULTS.md with train and test comparison tables."""

    def table_block(metrics_by_arm: dict[str, dict[str, float]]) -> str:
        lines = [
            "| Arm | Accuracy | Precision | Recall | F1 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for arm in (ARM_BASELINE, ARM_FINE_TUNED):
            metrics = metrics_by_arm[arm]
            lines.append(
                "| {arm} | {acc} | {prec} | {rec} | {f1} |".format(
                    arm=arm,
                    acc=format_metric(metrics["accuracy"]),
                    prec=format_metric(metrics["precision"]),
                    rec=format_metric(metrics["recall"]),
                    f1=format_metric(metrics["f1"]),
                )
            )
        return "\n".join(lines)

    return "\n".join(
        [
            "# Qwen3-4B LoRA fine-tune keep/remove results",
            "",
            f"- Model: `{MODEL_ID}`",
            "- Data: unanimous min-3 balanced n=308; seed=1; 80/20",
            "- Positive class: remove",
            "- Exploratory teachability run (no numeric success bar)",
            "",
            "## Train",
            "",
            table_block(train_metrics),
            "",
            "## Test",
            "",
            table_block(test_metrics),
            "",
        ]
    )


def evaluate_preds_dir(preds_dir: Path) -> tuple[
    dict[str, dict[str, float]],
    dict[str, dict[str, float]],
]:
    """Score the four expected prediction CSVs under ``preds_dir``."""
    train_metrics: dict[str, dict[str, float]] = {}
    test_metrics: dict[str, dict[str, float]] = {}
    for (split, arm), relative in PRED_RELATIVE_PATHS.items():
        path = preds_dir / relative
        metrics = score_prediction_csv(path)
        if split == "train":
            train_metrics[arm] = metrics
        else:
            test_metrics[arm] = metrics
    return train_metrics, test_metrics


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Score baseline vs fine-tuned keep/remove predictions."
    )
    parser.add_argument(
        "--preds-dir",
        required=True,
        help="Directory containing baseline/ and fine_tuned/ pred CSVs.",
    )
    parser.add_argument(
        "--write-results",
        required=True,
        help="Path to write RESULTS.md.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    preds_dir = Path(args.preds_dir)
    write_path = Path(args.write_results)
    train_metrics, test_metrics = evaluate_preds_dir(preds_dir)
    markdown = render_results_markdown(train_metrics, test_metrics)
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote {write_path}")
    print(markdown)


if __name__ == "__main__":
    main(sys.argv[1:])
