"""Score all-posts predictions against the modal label table.

Run from repo root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/score_all_posts.py \\
      --write \\
      --write-results \\
      experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/RESULTS.md
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from experiments.finetune_qwen_model_2026_08_08.evaluate import (
    compute_metrics,
    effective_pred_labels,
)
from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import (
    INVALID_DECISION,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_ALL_POSTS_PATH = EXPERIMENT_ROOT / "data" / "all_posts.csv"
DEFAULT_PRED_PATHS: dict[str, Path] = {
    "unanimous_model": EXPERIMENT_ROOT / "preds" / "unanimous_model" / "all_posts.csv",
    "modal_model": EXPERIMENT_ROOT / "preds" / "modal_model" / "all_posts.csv",
}
DEFAULT_SCORES_DIR = EXPERIMENT_ROOT / "scores"

OVERALL_COLUMNS = (
    "model",
    "slice",
    "n",
    "n_remove",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "invalid_rate",
)
BY_REMOVE_VOTES_COLUMNS = (
    "model",
    "n_remove",
    "n",
    "n_label_remove",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "invalid_rate",
)
SLICE_ORDER = ("all_posts", "train", "test", "unanimous_posts")
MODEL_ORDER = ("unanimous_model", "modal_model")
N_REMOVE_VALUES = tuple(range(6))
FIVE_RATERS = 5

ZERO_METRICS = {
    "accuracy": 0.0,
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0,
}


def format_metric(value: float) -> str:
    """Format a metric to four decimal places."""
    return f"{value:.4f}"


def invalid_rate(frame: pd.DataFrame) -> float:
    """Return the fraction of invalid prediction rows."""
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


def _as_bool(series: pd.Series) -> pd.Series:
    """Coerce manifest booleans that may be read as strings."""
    if series.dtype == bool:
        return series
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes"})


def merge_all_posts_with_predictions(
    all_posts: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Join gold metadata with prediction columns on ``message_id``."""
    pred_cols = ["message_id", "predicted_decision", "predicted_label"]
    missing = set(pred_cols) - set(predictions.columns)
    if missing:
        raise ValueError(f"Predictions missing columns: {sorted(missing)}")
    merged = all_posts.merge(
        predictions[pred_cols],
        on="message_id",
        how="inner",
        validate="one_to_one",
    )
    if len(merged) != len(all_posts):
        raise ValueError(
            "Prediction rows do not match all_posts message_ids one-to-one."
        )
    return merged


def score_frame(frame: pd.DataFrame) -> dict[str, float]:
    """Score one slice with invalid-as-wrong handling (gold = modal label)."""
    if frame.empty:
        return {**ZERO_METRICS, "invalid_rate": 0.0}
    y_true = [int(value) for value in frame["keep_remove_label"].tolist()]
    y_pred = effective_pred_labels(
        frame["keep_remove_label"],
        frame["predicted_decision"],
        frame["predicted_label"],
    )
    metrics = compute_metrics(y_true, y_pred)
    metrics["invalid_rate"] = invalid_rate(frame)
    return metrics


def _slice_filters() -> dict[str, Callable[[pd.DataFrame], pd.DataFrame]]:
    """Return named slice filters over a merged all-posts frame."""
    return {
        "all_posts": lambda frame: frame,
        "train": lambda frame: frame[frame["split"] == "train"],
        "test": lambda frame: frame[frame["split"] == "test"],
        "unanimous_posts": lambda frame: frame[_as_bool(frame["in_unanimous"])],
    }


def build_overall_rows(
    merged: pd.DataFrame,
    model: str,
) -> list[dict[str, float | int | str]]:
    """Build overall.csv rows for one model across all slices."""
    rows: list[dict[str, float | int | str]] = []
    for slice_name in SLICE_ORDER:
        slice_frame = _slice_filters()[slice_name](merged)
        metrics = score_frame(slice_frame)
        n_remove = int((slice_frame["keep_remove_label"] == 1).sum())
        rows.append(
            {
                "model": model,
                "slice": slice_name,
                "n": len(slice_frame),
                "n_remove": n_remove,
                **metrics,
            }
        )
    return rows


def build_by_remove_votes_rows(
    merged: pd.DataFrame,
    model: str,
) -> list[dict[str, float | int | str]]:
    """Build by_remove_votes.csv rows for one model (5 raters only)."""
    five_rater = merged[merged["n_raters"] == FIVE_RATERS]
    rows: list[dict[str, float | int | str]] = []
    for n_remove in N_REMOVE_VALUES:
        bucket = five_rater[five_rater["n_remove"] == n_remove]
        metrics = score_frame(bucket)
        n_label_remove = int((bucket["keep_remove_label"] == 1).sum())
        rows.append(
            {
                "model": model,
                "n_remove": n_remove,
                "n": len(bucket),
                "n_label_remove": n_label_remove,
                **metrics,
            }
        )
    return rows


def score_model(
    all_posts: pd.DataFrame,
    pred_path: Path,
    model: str,
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float | int | str]]]:
    """Score one model's predictions against ``all_posts``."""
    if not pred_path.is_file():
        raise FileNotFoundError(f"Prediction CSV not found: {pred_path}")
    predictions = pd.read_csv(pred_path)
    merged = merge_all_posts_with_predictions(all_posts, predictions)
    overall = build_overall_rows(merged, model)
    by_remove = build_by_remove_votes_rows(merged, model)
    return overall, by_remove


def write_score_csvs(
    scores_dir: Path,
    overall_rows: list[dict[str, float | int | str]],
    by_remove_rows: list[dict[str, float | int | str]],
) -> tuple[Path, Path]:
    """Write ``overall.csv`` and ``by_remove_votes.csv`` under ``scores_dir``."""
    scores_dir.mkdir(parents=True, exist_ok=True)
    overall_path = scores_dir / "overall.csv"
    by_remove_path = scores_dir / "by_remove_votes.csv"
    pd.DataFrame(overall_rows, columns=list(OVERALL_COLUMNS)).to_csv(
        overall_path,
        index=False,
    )
    pd.DataFrame(by_remove_rows, columns=list(BY_REMOVE_VOTES_COLUMNS)).to_csv(
        by_remove_path,
        index=False,
    )
    return overall_path, by_remove_path


def _markdown_table(
    rows: list[dict[str, float | int | str]],
    columns: tuple[str, ...],
    metric_columns: tuple[str, ...],
) -> str:
    """Render a markdown table with four-decimal metrics."""
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        cells: list[str] = []
        for column in columns:
            value = row[column]
            if column in metric_columns:
                cells.append(format_metric(float(value)))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_results_markdown(
    overall_rows: list[dict[str, float | int | str]],
    by_remove_rows: list[dict[str, float | int | str]],
) -> str:
    """Render RESULTS.md with a short lead and both score tables."""
    metric_columns = (
        "accuracy",
        "precision",
        "recall",
        "f1",
        "invalid_rate",
    )
    lead = (
        "All-posts scores use the modal keep/remove label as gold. "
        "The all_posts and train slices include posts each model trained on, "
        "so they are not held-out evaluations."
    )
    return "\n".join(
        [
            "# Experiment 5: all-posts inference scores",
            "",
            lead,
            "",
            "## Overall slices",
            "",
            _markdown_table(overall_rows, OVERALL_COLUMNS, metric_columns),
            "",
            "## Five-rater posts by remove-vote count",
            "",
            _markdown_table(by_remove_rows, BY_REMOVE_VOTES_COLUMNS, metric_columns),
            "",
        ]
    )


def score_all_models(
    all_posts_path: Path,
    pred_paths: dict[str, Path],
) -> tuple[
    list[dict[str, float | int | str]],
    list[dict[str, float | int | str]],
]:
    """Score every configured model."""
    if not all_posts_path.is_file():
        raise FileNotFoundError(f"all_posts table not found: {all_posts_path}")
    all_posts = pd.read_csv(all_posts_path)
    overall_rows: list[dict[str, float | int | str]] = []
    by_remove_rows: list[dict[str, float | int | str]] = []
    for model in MODEL_ORDER:
        pred_path = pred_paths[model]
        overall, by_remove = score_model(all_posts, pred_path, model)
        overall_rows.extend(overall)
        by_remove_rows.extend(by_remove)
    return overall_rows, by_remove_rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Score all-posts keep/remove predictions."
    )
    parser.add_argument(
        "--all-posts",
        default=str(DEFAULT_ALL_POSTS_PATH),
        help="Path to all_posts.csv with gold labels and splits.",
    )
    parser.add_argument(
        "--unanimous-preds",
        default=str(DEFAULT_PRED_PATHS["unanimous_model"]),
        help="Prediction CSV for the unanimous adapter model.",
    )
    parser.add_argument(
        "--modal-preds",
        default=str(DEFAULT_PRED_PATHS["modal_model"]),
        help="Prediction CSV for the modal adapter model.",
    )
    parser.add_argument(
        "--scores-dir",
        default=str(DEFAULT_SCORES_DIR),
        help="Directory for overall.csv and by_remove_votes.csv.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write scores/overall.csv and scores/by_remove_votes.csv.",
    )
    parser.add_argument(
        "--write-results",
        metavar="PATH",
        help="Write RESULTS.md to PATH.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    pred_paths = {
        "unanimous_model": Path(args.unanimous_preds),
        "modal_model": Path(args.modal_preds),
    }
    overall_rows, by_remove_rows = score_all_models(
        Path(args.all_posts),
        pred_paths,
    )
    if args.write:
        overall_path, by_remove_path = write_score_csvs(
            Path(args.scores_dir),
            overall_rows,
            by_remove_rows,
        )
        print(f"Wrote {overall_path}")
        print(f"Wrote {by_remove_path}")
    if args.write_results:
        results_path = Path(args.write_results)
        markdown = render_results_markdown(overall_rows, by_remove_rows)
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(markdown, encoding="utf-8")
        print(f"Wrote {results_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
