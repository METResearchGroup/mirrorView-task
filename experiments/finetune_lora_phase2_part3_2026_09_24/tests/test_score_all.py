"""Tests for experiment4 cross-eval scoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from experiments.finetune_qwen_model_2026_08_08.evaluate import (
    compute_metrics,
    effective_pred_labels,
)
from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import (
    INVALID_DECISION,
)
from experiments.finetune_lora_phase2_part3_2026_09_24.experiment4_cross_eval.score_all import (
    bootstrap_f1_ci,
    invalid_rate,
    score_arm_test_set,
)

PRED_COLUMNS = (
    "message_id",
    "decision",
    "keep_remove_label",
    "raw_generation",
    "predicted_decision",
    "predicted_label",
)


def _pred_row(
    message_id: str,
    gold: int,
    predicted_decision: str,
    predicted_label: object,
) -> dict[str, object]:
    decision = "remove" if gold == 1 else "keep"
    return {
        "message_id": message_id,
        "decision": decision,
        "keep_remove_label": gold,
        "raw_generation": f"raw-{message_id}",
        "predicted_decision": predicted_decision,
        "predicted_label": predicted_label,
    }


def _write_pred_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=list(PRED_COLUMNS)).to_csv(path, index=False)


class TestBootstrapF1Ci:
    """Tests for bootstrap_f1_ci."""

    def test_point_f1_lies_within_bootstrap_interval(self):
        """Point F1 should fall inside the 95% bootstrap interval."""
        y_true = [1, 0, 1, 0]
        y_pred = [1, 0, 0, 1]

        point_f1, f1_ci_low, f1_ci_high = bootstrap_f1_ci(
            y_true,
            y_pred,
            n_resamples=1000,
            seed=1,
        )

        assert f1_ci_low <= point_f1 <= f1_ci_high

    def test_bootstrap_is_deterministic_for_fixed_seed(self):
        """Repeated calls with the same seed return identical CIs."""
        y_true = [1, 0, 1, 0]
        y_pred = [1, 0, 0, 1]

        first = bootstrap_f1_ci(y_true, y_pred, n_resamples=1000, seed=1)
        second = bootstrap_f1_ci(y_true, y_pred, n_resamples=1000, seed=1)

        assert first == second


class TestInvalidRate:
    """Tests for invalid_rate."""

    def test_invalid_rows_counted_as_wrong_not_correct_remove(self):
        """Invalid generations count as wrong, not as correct remove."""
        frame = pd.DataFrame(
            [
                _pred_row("m1", 1, "remove", 1),
                _pred_row("m2", 1, INVALID_DECISION, pd.NA),
            ]
        )
        y_true = [int(v) for v in frame["keep_remove_label"].tolist()]
        y_pred = effective_pred_labels(
            frame["keep_remove_label"],
            frame["predicted_decision"],
            frame["predicted_label"],
        )
        metrics = compute_metrics(y_true, y_pred)

        assert metrics["f1"] == 1.0

    def test_invalid_rate_counts_invalid_and_missing_labels(self):
        """Invalid rate is the fraction of invalid or missing-label rows."""
        rows = [
            _pred_row("m1", 0, "keep", 0),
            _pred_row("m2", 0, INVALID_DECISION, pd.NA),
            _pred_row("m3", 1, "remove", 1),
            _pred_row("m4", 0, "keep", pd.NA),
            _pred_row("m5", 1, "remove", 1),
            _pred_row("m6", 0, "keep", 0),
            _pred_row("m7", 1, "remove", 1),
            _pred_row("m8", 0, "keep", 0),
            _pred_row("m9", 1, "remove", 1),
            _pred_row("m10", 0, "keep", 0),
        ]
        frame = pd.DataFrame(rows, columns=list(PRED_COLUMNS))

        result = invalid_rate(frame)

        assert result == 0.2


class TestScoreArmTestSet:
    """Tests for score_arm_test_set."""

    def test_scores_prediction_csv_with_bootstrap_fields(self, tmp_path: Path):
        """Scoring returns metrics, counts, and bootstrap CI fields."""
        pred_path = tmp_path / "preds.csv"
        rows = [
            _pred_row("m1", 1, "remove", 1),
            _pred_row("m2", 0, "keep", 0),
            _pred_row("m3", 1, "remove", 0),
            _pred_row("m4", 0, "keep", 0),
        ]
        _write_pred_csv(pred_path, rows)

        result = score_arm_test_set(
            pred_path,
            arm="zero-shot",
            test_set="test_unanimous",
        )

        assert result["arm"] == "zero-shot"
        assert result["test_set"] == "test_unanimous"
        assert result["n"] == 4
        assert result["n_remove"] == 2
        assert result["f1_ci_low"] <= result["f1"] <= result["f1_ci_high"]
        assert 0.0 <= result["invalid_rate"] <= 1.0


class TestMissingPreds:
    """Tests for missing prediction files."""

    def test_missing_pred_path_raises_file_not_found(self, tmp_path: Path):
        """Missing prediction CSV raises FileNotFoundError with the path."""
        missing_path = tmp_path / "missing.csv"

        with pytest.raises(FileNotFoundError, match=str(missing_path)):
            score_arm_test_set(
                missing_path,
                arm="zero-shot",
                test_set="test_unanimous",
            )
