"""Tests for evaluate metrics with invalid-as-wrong scoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.finetune_qwen_model_2026_08_08.evaluate import (
    effective_pred_labels,
    render_results_markdown,
    score_prediction_csv,
)


class TestEffectivePredLabels:
    """Tests for effective_pred_labels()."""

    def test_invalid_never_counts_as_correct(self):
        """Verifies invalid rows are flipped vs gold for scoring."""
        # Arrange
        frame = pd.DataFrame(
            {
                "keep_remove_label": [1, 0, 1],
                "predicted_decision": ["remove", "__invalid__", "keep"],
                "predicted_label": [1, "", 0],
            }
        )

        # Act
        result = effective_pred_labels(
            frame["keep_remove_label"],
            frame["predicted_decision"],
            frame["predicted_label"],
        )

        # Assert
        # gold 1, pred 1 -> 1
        # gold 0, invalid -> flipped to 1
        # gold 1, pred 0 -> 0
        assert result == [1, 1, 0]


class TestScorePredictionCsv:
    """Tests for score_prediction_csv()."""

    def test_invalid_reduces_accuracy(self, tmp_path: Path):
        """Verifies an invalid row lowers accuracy vs an all-correct CSV."""
        good = tmp_path / "good.csv"
        bad = tmp_path / "bad.csv"
        pd.DataFrame(
            {
                "message_id": ["a", "b"],
                "decision": ["remove", "keep"],
                "keep_remove_label": [1, 0],
                "raw_generation": ["remove", "keep"],
                "predicted_decision": ["remove", "keep"],
                "predicted_label": [1, 0],
            }
        ).to_csv(good, index=False)
        pd.DataFrame(
            {
                "message_id": ["a", "b"],
                "decision": ["remove", "keep"],
                "keep_remove_label": [1, 0],
                "raw_generation": ["remove", "???"],
                "predicted_decision": ["remove", "__invalid__"],
                "predicted_label": [1, ""],
            }
        ).to_csv(bad, index=False)

        good_metrics = score_prediction_csv(good)
        bad_metrics = score_prediction_csv(bad)
        assert good_metrics["accuracy"] == 1.0
        assert bad_metrics["accuracy"] < good_metrics["accuracy"]


class TestRenderResultsMarkdown:
    """Tests for render_results_markdown()."""

    def test_contains_train_and_test_tables(self):
        """Verifies markdown has both sections and both arms."""
        zeros = {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }
        markdown = render_results_markdown(
            {"baseline": zeros, "fine-tuned": zeros},
            {"baseline": zeros, "fine-tuned": zeros},
        )
        assert "## Train" in markdown
        assert "## Test" in markdown
        assert "baseline" in markdown
        assert "fine-tuned" in markdown
