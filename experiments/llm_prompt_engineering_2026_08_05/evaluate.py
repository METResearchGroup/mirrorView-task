"""Score keep/remove classifier predictions and emit the RESULTS table.

Positive class for precision / recall / F1 is remove (``keep_remove_label=1``).

RESULTS.md table shape (filled by production / ``--write-results``)::

    # Prompt engineering keep/remove classifier results

    - Model: `gpt-5.4-nano`
    - Subset: `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` (n=500, seed=42)
    - Response schema: `shared.schemas.IsRemoveResult`
    - Positive class for precision / recall / F1: remove (`keep_remove_label=1`)
    - Control run dir: `<path>`
    - Tuned run dir: `<path>`

    | Arm | Accuracy | Precision | Recall | F1 |
    | --- | --- | --- | --- | --- |
    | control | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
    | prompt-tuned | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Run from repo root::

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/evaluate.py \\
      --run-dir experiments/llm_prompt_engineering_2026_08_05/outputs/control/outputs/<TS>

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/evaluate.py \\
      --control-run-dir <CONTROL_TS> --tuned-run-dir <TUNED_TS> \\
      --write-results experiments/llm_prompt_engineering_2026_08_05/RESULTS.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_SUBSET_PATH = (
    "experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv"
)
DEFAULT_MODEL = "gpt-5.4-nano"
REQUIRED_PRED_KEYS = (
    "message_id",
    "keep_remove_label",
    "predicted_label",
    "arm",
)
METRIC_KEYS = ("accuracy", "precision", "recall", "f1")


def compute_metrics(
    y_true: list[int] | pd.Series,
    y_pred: list[int] | pd.Series,
) -> dict[str, float]:
    """Compute accuracy / precision / recall / F1 (positive class = remove).

    Parameters
    ----------
    y_true
        Gold labels (0 = keep, 1 = remove).
    y_pred
        Predicted labels (0 = keep, 1 = remove).

    Returns
    -------
    dict[str, float]
        Keys: ``accuracy``, ``precision``, ``recall``, ``f1``.
    """
    y_true_arr = [int(v) for v in y_true]
    y_pred_arr = [int(v) for v in y_pred]
    return {
        "accuracy": float(accuracy_score(y_true_arr, y_pred_arr)),
        "precision": float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        "recall": float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        "f1": float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
    }


def load_predictions(run_dir: Path) -> pd.DataFrame:
    """Load per-item prediction JSON files from a runner output directory.

    Parameters
    ----------
    run_dir
        Timestamped runner folder containing ``metadata.json`` and prediction
        ``*.json`` files.

    Returns
    -------
    pd.DataFrame
        One row per prediction with required writer fields.

    Raises
    ------
    FileNotFoundError
        When ``metadata.json`` is missing.
    ValueError
        When no predictions are found, required keys are missing, or
        ``message_id`` values are duplicated.
    """
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Missing metadata.json under {run_dir}")

    rows: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name == "metadata.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        missing = [key for key in REQUIRED_PRED_KEYS if key not in payload]
        if missing:
            raise ValueError(f"{path} missing keys: {missing}")
        rows.append(payload)

    if not rows:
        raise ValueError(f"No prediction JSON files found under {run_dir}")

    frame = pd.DataFrame(rows)
    if frame["message_id"].duplicated().any():
        dupes = frame.loc[frame["message_id"].duplicated(), "message_id"].tolist()
        raise ValueError(f"Duplicate message_id values in {run_dir}: {dupes}")
    return frame


def score_run_dir(run_dir: Path) -> tuple[pd.DataFrame, dict[str, float]]:
    """Load predictions from ``run_dir`` and compute metrics.

    Parameters
    ----------
    run_dir
        Timestamped runner output directory.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, float]]
        Prediction frame and metrics dict.
    """
    frame = load_predictions(run_dir)
    metrics = compute_metrics(
        frame["keep_remove_label"].tolist(),
        frame["predicted_label"].tolist(),
    )
    return frame, metrics


def format_metrics_row(arm_label: str, metrics: dict[str, float]) -> str:
    """Format one markdown table row with metrics to 4 decimal places."""
    return (
        f"| {arm_label} | {metrics['accuracy']:.4f} | "
        f"{metrics['precision']:.4f} | {metrics['recall']:.4f} | "
        f"{metrics['f1']:.4f} |"
    )


def evaluate_two_arms(
    control_run_dir: Path,
    tuned_run_dir: Path,
    model: str = DEFAULT_MODEL,
    subset_path: str = DEFAULT_SUBSET_PATH,
) -> str:
    """Score both arms and return the RESULTS.md markdown body.

    Parameters
    ----------
    control_run_dir
        Control arm timestamped runner directory.
    tuned_run_dir
        Tuned arm timestamped runner directory.
    model
        Model id recorded in the header.
    subset_path
        Repo-relative subset path recorded in the header.

    Returns
    -------
    str
        Full RESULTS.md markdown including the two-row metrics table.
    """
    _, control_metrics = score_run_dir(control_run_dir)
    _, tuned_metrics = score_run_dir(tuned_run_dir)
    lines = [
        "# Prompt engineering keep/remove classifier results",
        "",
        f"- Model: `{model}`",
        f"- Subset: `{subset_path}` (n=500, seed=42)",
        "- Response schema: `shared.schemas.IsRemoveResult`",
        "- Positive class for precision / recall / F1: remove (`keep_remove_label=1`)",
        f"- Control run dir: `{control_run_dir}`",
        f"- Tuned run dir: `{tuned_run_dir}`",
        "",
        "| Arm | Accuracy | Precision | Recall | F1 |",
        "| --- | --- | --- | --- | --- |",
        format_metrics_row("control", control_metrics),
        format_metrics_row("prompt-tuned", tuned_metrics),
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for scoring runner outputs."""
    parser = argparse.ArgumentParser(
        description="Score keep/remove classifier predictions against gold labels."
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Single arm timestamped runner directory.",
    )
    parser.add_argument(
        "--control-run-dir",
        type=Path,
        default=None,
        help="Control arm run dir (use with --tuned-run-dir).",
    )
    parser.add_argument(
        "--tuned-run-dir",
        type=Path,
        default=None,
        help="Tuned arm run dir (use with --control-run-dir).",
    )
    parser.add_argument(
        "--write-results",
        type=Path,
        default=None,
        help="When set with both arm dirs, write RESULTS.md to this path.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model id for RESULTS header (default: {DEFAULT_MODEL}).",
    )
    return parser.parse_args(argv)


def _print_single_arm(run_dir: Path) -> None:
    """Print metrics for one arm to stdout."""
    frame, metrics = score_run_dir(run_dir)
    print(f"run_dir={run_dir}")
    print(f"n={len(frame)} arm={frame['arm'].iloc[0]}")
    for key in METRIC_KEYS:
        print(f"{key}={metrics[key]:.4f}")


def main(argv: list[str] | None = None) -> None:
    """CLI entry: score one arm or emit the two-row RESULTS table."""
    args = parse_args(argv)
    dual = args.control_run_dir is not None or args.tuned_run_dir is not None
    if args.run_dir is not None and dual:
        raise ValueError("Pass either --run-dir or both arm dirs, not mixed")
    if dual:
        if args.control_run_dir is None or args.tuned_run_dir is None:
            raise ValueError(
                "Both --control-run-dir and --tuned-run-dir are required together"
            )
        markdown = evaluate_two_arms(
            args.control_run_dir,
            args.tuned_run_dir,
            model=args.model,
        )
        print(markdown)
        if args.write_results is not None:
            args.write_results.parent.mkdir(parents=True, exist_ok=True)
            args.write_results.write_text(markdown, encoding="utf-8")
            print(f"Wrote {args.write_results}")
        return
    if args.run_dir is None:
        raise ValueError("Provide --run-dir or both --control-run-dir and --tuned-run-dir")
    _print_single_arm(args.run_dir)


if __name__ == "__main__":
    main()
