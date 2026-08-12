"""Tests for three-arm evaluate helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.compare_qwen_lora_modal_eval_2026_08_12.evaluate import (
    ARM_BASELINE,
    ARM_MODAL,
    ARM_ORDER,
    ARM_UNANIMOUS,
    evaluate_preds_dir,
    render_results_markdown,
)

PRED_COLUMNS = (
    "message_id",
    "decision",
    "keep_remove_label",
    "raw_generation",
    "predicted_decision",
    "predicted_label",
)


def _write_pred_csv(path: Path, *, predicted_label: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [
            {
                "message_id": "m1",
                "decision": "remove" if predicted_label == 1 else "keep",
                "keep_remove_label": 1,
                "raw_generation": "remove" if predicted_label == 1 else "keep",
                "predicted_decision": (
                    "remove" if predicted_label == 1 else "keep"
                ),
                "predicted_label": predicted_label,
            },
            {
                "message_id": "m2",
                "decision": "keep",
                "keep_remove_label": 0,
                "raw_generation": "keep",
                "predicted_decision": "keep",
                "predicted_label": 0,
            },
        ],
        columns=list(PRED_COLUMNS),
    )
    frame.to_csv(path, index=False)


def test_evaluate_preds_dir_scores_three_arms(tmp_path: Path) -> None:
    """All three arms are scored on train and test."""
    preds_dir = tmp_path / "preds"
    for arm, pred in (
        (ARM_BASELINE, 1),
        (ARM_UNANIMOUS, 1),
        (ARM_MODAL, 0),
    ):
        for split in ("train", "test"):
            _write_pred_csv(
                preds_dir / arm / f"{split}_labels.csv",
                predicted_label=pred,
            )

    train_metrics, test_metrics = evaluate_preds_dir(preds_dir)
    assert set(train_metrics) == set(ARM_ORDER)
    assert set(test_metrics) == set(ARM_ORDER)
    assert train_metrics[ARM_BASELINE]["accuracy"] == 1.0
    assert test_metrics[ARM_MODAL]["accuracy"] == 0.5


def test_render_results_markdown_lists_arms_in_order(tmp_path: Path) -> None:
    """Markdown tables list baseline, unanimous_lora, then modal_lora."""
    preds_dir = tmp_path / "preds"
    for arm in ARM_ORDER:
        for split in ("train", "test"):
            _write_pred_csv(
                preds_dir / arm / f"{split}_labels.csv",
                predicted_label=1,
            )
    train_metrics, test_metrics = evaluate_preds_dir(preds_dir)
    markdown = render_results_markdown(train_metrics, test_metrics)
    baseline_idx = markdown.index(f"| {ARM_BASELINE} |")
    unanimous_idx = markdown.index(f"| {ARM_UNANIMOUS} |")
    modal_idx = markdown.index(f"| {ARM_MODAL} |")
    assert baseline_idx < unanimous_idx < modal_idx
    assert "STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS" in markdown
