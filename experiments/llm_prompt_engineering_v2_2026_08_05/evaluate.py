"""Score v2 keep/remove classifier predictions and emit the RESULTS table.

Imports scoring helpers from
``experiments.llm_prompt_engineering_2026_08_05.evaluate`` and reassembles the
RESULTS markdown header for n=1000 + Qwen 3.6 (v1 hardcodes n=500).

Positive class for precision / recall / F1 is remove (``keep_remove_label=1``).

RESULTS.md table shape (filled by production / ``--write-results``)::

    # Prompt engineering keep/remove classifier results

    - Model: `qwen/qwen3.6-plus`
    - Subset: `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` (n=1000, seed=42, balanced 500 keep / 500 remove)
    - Response schema: `shared.schemas.IsRemoveResult`
    - Positive class for precision / recall / F1: remove (`keep_remove_label=1`)
    - Control run dir: `<path>`
    - Tuned run dir: `<path>`

    | Arm | Accuracy | Precision | Recall | F1 |
    | --- | --- | --- | --- | --- |
    | control | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
    | prompt-tuned | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Run from repo root::

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \\
      --run-dir experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control/outputs/<TS>

    PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/evaluate.py \\
      --control-run-dir <CONTROL_TS> --tuned-run-dir <TUNED_TS> \\
      --model qwen/qwen3.6-plus \\
      --write-results experiments/llm_prompt_engineering_v2_2026_08_05/RESULTS.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.llm_prompt_engineering_2026_08_05.evaluate import (
    METRIC_KEYS,
    compute_metrics,
    format_metrics_row,
    load_predictions,
    score_run_dir,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_SUBSET_PATH = (
    "experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv"
)
DEFAULT_MODEL = "qwen/qwen3.6-plus"
SUBSET_N = 1000
SUBSET_SEED = 42


def evaluate_two_arms(
    control_run_dir: Path,
    tuned_run_dir: Path,
    model: str = DEFAULT_MODEL,
    subset_path: str = DEFAULT_SUBSET_PATH,
) -> str:
    """Score both arms and return the v2 RESULTS.md markdown body.

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
        (
            f"- Subset: `{subset_path}` "
            f"(n={SUBSET_N}, seed={SUBSET_SEED}, balanced 500 keep / 500 remove)"
        ),
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
    """Parse CLI arguments for scoring v2 runner outputs."""
    parser = argparse.ArgumentParser(
        description=(
            "Score v2 keep/remove classifier predictions against gold labels."
        )
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
        raise ValueError(
            "Provide --run-dir or both --control-run-dir and --tuned-run-dir"
        )
    _print_single_arm(args.run_dir)


if __name__ == "__main__":
    main()
