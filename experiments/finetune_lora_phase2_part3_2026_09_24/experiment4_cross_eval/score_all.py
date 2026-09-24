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
    """Score one arm on one test set with bootstrap CIs."""
    raise NotImplementedError


def write_cross_eval_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    """Write the eight-row cross-eval metrics table."""
    raise NotImplementedError


def load_split_counts(part3_root: Path) -> dict[str, int]:
    """Load split and balanced row counts from manifest and CSVs."""
    raise NotImplementedError


def render_results_markdown(
    rows: list[dict[str, float | int | str]],
    split_counts: dict[str, int],
) -> str:
    """Render RESULTS.md from cross-eval rows and split counts."""
    raise NotImplementedError


def score_all_arms() -> list[dict[str, float | int | str]]:
    """Score every arm and test-set combination."""
    raise NotImplementedError


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
