"""Score baseline, unanimous LoRA, and modal LoRA preds into RESULTS.md.

Reuses metric helpers from ``experiments.finetune_qwen_model_2026_08_08.evaluate``.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/compare_qwen_lora_modal_eval_2026_08_12/evaluate.py \\
      --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \\
      --write-results experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from experiments.finetune_qwen_model_2026_08_08.evaluate import (
    format_metric,
    score_prediction_csv,
)
from experiments.finetune_qwen_model_2026_08_08.src.train_config import MODEL_ID

ARM_BASELINE = "baseline"
ARM_UNANIMOUS = "unanimous_lora"
ARM_MODAL = "modal_lora"
ARM_ORDER = (ARM_BASELINE, ARM_UNANIMOUS, ARM_MODAL)

PRED_RELATIVE_PATHS = {
    ("train", ARM_BASELINE): Path("baseline") / "train_labels.csv",
    ("train", ARM_UNANIMOUS): Path("unanimous_lora") / "train_labels.csv",
    ("train", ARM_MODAL): Path("modal_lora") / "train_labels.csv",
    ("test", ARM_BASELINE): Path("baseline") / "test_labels.csv",
    ("test", ARM_UNANIMOUS): Path("unanimous_lora") / "test_labels.csv",
    ("test", ARM_MODAL): Path("modal_lora") / "test_labels.csv",
}

DATA_DESCRIPTION = (
    "STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS via frozen splits in "
    "experiments/larger_finetune_qwen_model_2026_08_08/data/; "
    "balanced 1:1; seed=1; 80/20 (train 4500 / test 1126)"
)


def evaluate_preds_dir(preds_dir: Path) -> tuple[
    dict[str, dict[str, float]],
    dict[str, dict[str, float]],
]:
    """Score the six expected prediction CSVs under ``preds_dir``."""
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


def render_results_markdown(
    train_metrics: dict[str, dict[str, float]],
    test_metrics: dict[str, dict[str, float]],
    data_description: str = DATA_DESCRIPTION,
) -> str:
    """Render RESULTS.md with train and test three-arm tables."""

    def table_block(metrics_by_arm: dict[str, dict[str, float]]) -> str:
        lines = [
            "| Arm | Accuracy | Precision | Recall | F1 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for arm in ARM_ORDER:
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
            "# Qwen3-4B keep/remove ablation on one modal eval set",
            "",
            f"- Model: `{MODEL_ID}`",
            f"- Data: {data_description}",
            "- Positive class: remove",
            "- Arms: baseline (no LoRA); unanimous_lora (PR 54 adapter "
            "`passrole_probe3`); modal_lora (PR 57 adapter "
            "`modal_larger_1ep_2026_08_09`)",
            "- No retraining in this experiment",
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Score three keep/remove prediction arms into RESULTS.md."
    )
    parser.add_argument(
        "--preds-dir",
        required=True,
        help="Directory with baseline/, unanimous_lora/, and modal_lora/.",
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
