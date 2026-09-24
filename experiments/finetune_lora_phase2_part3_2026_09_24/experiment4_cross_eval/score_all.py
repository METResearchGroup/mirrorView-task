"""Score cross-eval predictions and write cross_eval.csv / RESULTS.md.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/finetune_lora_phase2_part3_2026_09_24/experiment4_cross_eval/score_all.py \\
      --write-results experiments/finetune_lora_phase2_part3_2026_09_24/RESULTS.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.finetune_qwen_model_2026_08_08.evaluate import (
    compute_metrics,
    effective_pred_labels,
    score_prediction_csv,
)
from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import (
    INVALID_DECISION,
)
from experiments.finetune_lora_phase2_part3_2026_09_24.shared.run_config import (
    MODEL_ID,
    RANDOM_SEED,
)

PART3_ROOT = Path(__file__).resolve().parents[1]
CROSS_EVAL_COLUMNS = (
    "arm",
    "test_set",
    "n",
    "n_remove",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "f1_ci_low",
    "f1_ci_high",
    "invalid_rate",
)
BOOTSTRAP_N_RESAMPLES = 1000
BOOTSTRAP_SEED = 1
CI_LOW_PERCENTILE = 2.5
CI_HIGH_PERCENTILE = 97.5

ARM_PRED_PATHS: dict[str, dict[str, Path]] = {
    "zero-shot": {
        "test_unanimous": PART3_ROOT
        / "experiment4_cross_eval/preds/test_unanimous.csv",
        "test_modal": PART3_ROOT / "experiment4_cross_eval/preds/test_modal.csv",
    },
    "experiment1_unanimous": {
        "test_unanimous": PART3_ROOT
        / "experiment1_unanimous/preds/test_unanimous.csv",
        "test_modal": PART3_ROOT / "experiment1_unanimous/preds/test_modal.csv",
    },
    "experiment2_modal": {
        "test_unanimous": PART3_ROOT / "experiment2_modal/preds/test_unanimous.csv",
        "test_modal": PART3_ROOT / "experiment2_modal/preds/test_modal.csv",
    },
    "experiment3_modal_size_matched": {
        "test_unanimous": PART3_ROOT
        / "experiment3_modal_size_matched/preds/test_unanimous.csv",
        "test_modal": PART3_ROOT
        / "experiment3_modal_size_matched/preds/test_modal.csv",
    },
}
MATRIX_ARM_ORDER = (
    "zero-shot",
    "experiment1_unanimous",
    "experiment2_modal",
    "experiment3_modal_size_matched",
)
MATRIX_ARM_LABELS = {
    "zero-shot": "zero-shot",
    "experiment1_unanimous": "Experiment 1",
    "experiment2_modal": "Experiment 2",
    "experiment3_modal_size_matched": "Experiment 3",
}
TEST_SET_ORDER = ("test_unanimous", "test_modal")
TEST_SET_LABELS = {
    "test_unanimous": "unanimous test",
    "test_modal": "modal test",
}
PART2_REFERENCE_MODEL = "Qwen/Qwen3-4B-Instruct-2507"


def format_metric(value: float) -> str:
    """Format a metric to four decimal places."""
    return f"{value:.4f}"


def bootstrap_f1_ci(
    y_true: list[int],
    y_pred: list[int],
    n_resamples: int = BOOTSTRAP_N_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float, float]:
    """Bootstrap remove-F1 confidence interval over test posts.

    Parameters
    ----------
    y_true
        Gold labels (0 keep / 1 remove).
    y_pred
        Effective predicted labels for scoring.
    n_resamples
        Number of bootstrap resamples.
    seed
        Random seed for resampling.

    Returns
    -------
    tuple[float, float, float]
        Point remove-F1, 2.5th percentile, and 97.5th percentile.
    """
    point_f1 = compute_metrics(y_true, y_pred)["f1"]
    if not y_true:
        return point_f1, point_f1, point_f1
    rng = np.random.default_rng(seed)
    sample_count = len(y_true)
    f1_samples: list[float] = []
    for _ in range(n_resamples):
        indices = rng.integers(0, sample_count, size=sample_count)
        resampled_true = [y_true[index] for index in indices]
        resampled_pred = [y_pred[index] for index in indices]
        f1_samples.append(compute_metrics(resampled_true, resampled_pred)["f1"])
    f1_ci_low = float(np.percentile(f1_samples, CI_LOW_PERCENTILE))
    f1_ci_high = float(np.percentile(f1_samples, CI_HIGH_PERCENTILE))
    return point_f1, f1_ci_low, f1_ci_high


def invalid_rate(frame: pd.DataFrame) -> float:
    """Return the fraction of invalid prediction rows.

    Parameters
    ----------
    frame
        Prediction CSV loaded as a DataFrame.

    Returns
    -------
    float
        Fraction of rows with ``__invalid__`` decision or missing label.
    """
    if frame.empty:
        return 0.0
    invalid_decision = (
        frame["predicted_decision"].astype(str).str.strip().str.lower()
        == INVALID_DECISION
    )
    predicted_label = frame["predicted_label"]
    missing_label = predicted_label.isna() | (
        predicted_label.astype(str).str.strip() == ""
    )
    invalid_rows = invalid_decision | missing_label
    return float(invalid_rows.sum()) / len(frame)


def score_arm_test_set(pred_path: Path, arm: str, test_set: str) -> dict[str, float | int | str]:
    """Score one arm on one test set with bootstrap CIs.

    Parameters
    ----------
    pred_path
        Prediction CSV path.
    arm
        Model arm identifier.
    test_set
        Test set name (``test_unanimous`` or ``test_modal``).

    Returns
    -------
    dict[str, float | int | str]
        Metrics, counts, bootstrap CI, and invalid rate for one arm/test set.

    Raises
    ------
    FileNotFoundError
        When ``pred_path`` does not exist.
    """
    if not pred_path.is_file():
        raise FileNotFoundError(f"Prediction CSV not found: {pred_path}")
    frame = pd.read_csv(pred_path)
    metrics = score_prediction_csv(pred_path)
    y_true = [int(value) for value in frame["keep_remove_label"].tolist()]
    y_pred = effective_pred_labels(
        frame["keep_remove_label"],
        frame["predicted_decision"],
        frame["predicted_label"],
    )
    point_f1, f1_ci_low, f1_ci_high = bootstrap_f1_ci(y_true, y_pred)
    n_remove = int((frame["keep_remove_label"] == 1).sum())
    return {
        "arm": arm,
        "test_set": test_set,
        "n": len(frame),
        "n_remove": n_remove,
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": point_f1,
        "f1_ci_low": f1_ci_low,
        "f1_ci_high": f1_ci_high,
        "invalid_rate": invalid_rate(frame),
    }


def write_cross_eval_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    """Write the eight-row cross-eval metrics table.

    Parameters
    ----------
    path
        Destination CSV path.
    rows
        One metrics dict per arm and test-set combination.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=list(CROSS_EVAL_COLUMNS)).to_csv(path, index=False)


def _label_counts(frame: pd.DataFrame) -> tuple[int, int, int]:
    row_count = len(frame)
    remove_count = int((frame["keep_remove_label"] == 1).sum())
    keep_count = row_count - remove_count
    return row_count, remove_count, keep_count


def load_split_counts(part3_root: Path) -> dict[str, int]:
    """Load split and balanced row counts from manifest and CSVs.

    Parameters
    ----------
    part3_root
        Part 3 experiment root directory.

    Returns
    -------
    dict[str, int]
        Post-level and balanced row counts for RESULTS.md tables.
    """
    manifest = pd.read_csv(part3_root / "data/split_manifest.csv")
    test_unanimous = pd.read_csv(part3_root / "data/test_unanimous.csv")
    test_modal = pd.read_csv(part3_root / "data/test_modal.csv")
    exp1_train = pd.read_csv(part3_root / "experiment1_unanimous/data/train.csv")
    exp2_train = pd.read_csv(part3_root / "experiment2_modal/data/train.csv")
    exp3_train = pd.read_csv(
        part3_root / "experiment3_modal_size_matched/data/train.csv"
    )
    unanimous_rows, unanimous_remove, unanimous_keep = _label_counts(test_unanimous)
    modal_rows, modal_remove, modal_keep = _label_counts(test_modal)
    return {
        "modal_posts": len(manifest),
        "unanimous_posts": int(manifest["in_unanimous"].sum()),
        "exp1_train_rows": len(exp1_train),
        "exp2_train_rows": len(exp2_train),
        "exp3_train_rows": len(exp3_train),
        "test_unanimous_rows": unanimous_rows,
        "test_unanimous_remove": unanimous_remove,
        "test_unanimous_keep": unanimous_keep,
        "test_modal_rows": modal_rows,
        "test_modal_remove": modal_remove,
        "test_modal_keep": modal_keep,
    }


def _row_lookup(
    rows: list[dict[str, float | int | str]],
) -> dict[tuple[str, str], dict[str, float | int | str]]:
    return {(str(row["arm"]), str(row["test_set"])): row for row in rows}


def _format_f1_with_ci(row: dict[str, float | int | str]) -> str:
    return (
        f"{format_metric(float(row['f1']))} "
        f"[{format_metric(float(row['f1_ci_low']))}, "
        f"{format_metric(float(row['f1_ci_high']))}]"
    )


def _summary_paragraph(rows: list[dict[str, float | int | str]]) -> str:
    best_row = max(rows, key=lambda row: float(row["f1"]))
    best_arm = MATRIX_ARM_LABELS[str(best_row["arm"])]
    best_test = TEST_SET_LABELS[str(best_row["test_set"])]
    best_f1 = _format_f1_with_ci(best_row)
    nonzero_invalid = [
        f"{MATRIX_ARM_LABELS[str(row['arm'])]} on "
        f"{TEST_SET_LABELS[str(row['test_set'])]} "
        f"({format_metric(float(row['invalid_rate']))})"
        for row in rows
        if float(row["invalid_rate"]) > 0.0
    ]
    if nonzero_invalid:
        invalid_text = (
            " Nonzero invalid generation rates: "
            + "; ".join(nonzero_invalid)
            + "."
        )
    else:
        invalid_text = " All arms had zero invalid generations."
    return (
        f"The highest remove-F1 on the Part 3 balanced test sets is "
        f"{best_arm} on the {best_test} at {best_f1}."
        f"{invalid_text}"
    )


def render_results_markdown(
    rows: list[dict[str, float | int | str]],
    split_counts: dict[str, int],
) -> str:
    """Render RESULTS.md from cross-eval rows and split counts."""
    lookup = _row_lookup(rows)
    matrix_lines = [
        "| Arm | unanimous test | modal test |",
        "| --- | --- | --- |",
    ]
    for arm in MATRIX_ARM_ORDER:
        unanimous_cell = _format_f1_with_ci(lookup[(arm, "test_unanimous")])
        modal_cell = _format_f1_with_ci(lookup[(arm, "test_modal")])
        matrix_lines.append(
            f"| {MATRIX_ARM_LABELS[arm]} | {unanimous_cell} | {modal_cell} |"
        )

    metrics_lines = [
        "| arm | test_set | n | n_remove | accuracy | precision | recall | f1 | "
        "f1_ci_low | f1_ci_high | invalid_rate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        metrics_lines.append(
            "| {arm} | {test_set} | {n} | {n_remove} | {accuracy} | "
            "{precision} | {recall} | {f1} | {f1_ci_low} | {f1_ci_high} | "
            "{invalid_rate} |".format(
                arm=row["arm"],
                test_set=row["test_set"],
                n=row["n"],
                n_remove=row["n_remove"],
                accuracy=format_metric(float(row["accuracy"])),
                precision=format_metric(float(row["precision"])),
                recall=format_metric(float(row["recall"])),
                f1=format_metric(float(row["f1"])),
                f1_ci_low=format_metric(float(row["f1_ci_low"])),
                f1_ci_high=format_metric(float(row["f1_ci_high"])),
                invalid_rate=format_metric(float(row["invalid_rate"])),
            )
        )

    split_lines = [
        "| Split | n | n_remove | n_keep |",
        "| --- | --- | --- | --- |",
        f"| modal pool posts | {split_counts['modal_posts']} | — | — |",
        f"| unanimous-min3 posts | {split_counts['unanimous_posts']} | — | — |",
        f"| Experiment 1 train | {split_counts['exp1_train_rows']} | — | — |",
        f"| Experiment 2 train | {split_counts['exp2_train_rows']} | — | — |",
        f"| Experiment 3 train | {split_counts['exp3_train_rows']} | — | — |",
        "| test_unanimous | "
        f"{split_counts['test_unanimous_rows']} | "
        f"{split_counts['test_unanimous_remove']} | "
        f"{split_counts['test_unanimous_keep']} |",
        "| test_modal | "
        f"{split_counts['test_modal_rows']} | "
        f"{split_counts['test_modal_remove']} | "
        f"{split_counts['test_modal_keep']} |",
    ]

    part2_block = "\n".join(
        [
            f"## Part 2 reference (different base model: `{PART2_REFERENCE_MODEL}`)",
            "",
            "These Part 2 test remove-F1 values use a different base model and are "
            "not comparable to Part 3.",
            "",
            "| Test set | Arm | remove-F1 |",
            "| --- | --- | --- |",
            "| unanimous | baseline | 0.7407 |",
            "| unanimous | fine-tuned | 0.9688 |",
            "| modal | baseline | 0.7210 |",
            "| modal | fine-tuned | 0.6962 |",
        ]
    )

    return "\n".join(
        [
            "# Part 3 LoRA cross-eval keep/remove results",
            "",
            f"- Model: `{MODEL_ID}`",
            f"- Seed: {RANDOM_SEED}",
            "- Positive class: remove",
            "",
            "## Remove-F1 matrix (95% bootstrap CI)",
            "",
            "\n".join(matrix_lines),
            "",
            "## Full metrics",
            "",
            "\n".join(metrics_lines),
            "",
            "## Split counts",
            "",
            "\n".join(split_lines),
            "",
            "## Summary",
            "",
            _summary_paragraph(rows),
            "",
            part2_block,
            "",
        ]
    )


def score_all_arms() -> list[dict[str, float | int | str]]:
    """Score every arm and test-set combination."""
    rows: list[dict[str, float | int | str]] = []
    for arm, test_paths in ARM_PRED_PATHS.items():
        for test_set, pred_path in test_paths.items():
            rows.append(score_arm_test_set(pred_path, arm, test_set))
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Score Part 3 cross-eval predictions."
    )
    parser.add_argument(
        "--write-results",
        required=True,
        help="Path to write RESULTS.md.",
    )
    parser.add_argument(
        "--cross-eval-csv",
        default=str(PART3_ROOT / "experiment4_cross_eval/scores/cross_eval.csv"),
        help="Path to write cross_eval.csv.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    rows = score_all_arms()
    write_cross_eval_csv(Path(args.cross_eval_csv), rows)
    results_path = Path(args.write_results)
    split_counts = load_split_counts(PART3_ROOT)
    markdown = render_results_markdown(rows, split_counts)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.cross_eval_csv}")
    print(f"Wrote {results_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
