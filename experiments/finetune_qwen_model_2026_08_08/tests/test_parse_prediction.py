"""Tests for keep/remove generation parsing."""

from __future__ import annotations

import pytest

from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import (
    INVALID_DECISION,
    parse_generation,
)


class TestParseGeneration:
    """Tests for parse_generation()."""

    @pytest.mark.parametrize(
        ("raw", "decision", "label"),
        [
            ("keep", "keep", 0),
            ("Keep", "keep", 0),
            ("keep\nextra", "keep", 0),
            ("remove", "remove", 1),
            ("Remove", "remove", 1),
            ("remove please", "remove", 1),
        ],
    )
    def test_valid_first_token(self, raw, decision, label):
        """Verifies keep/remove first-token mapping."""
        # Arrange / Act
        result = parse_generation(raw)

        # Assert
        assert result.predicted_decision == decision
        assert result.predicted_label == label

    @pytest.mark.parametrize(
        "raw",
        ["", "allow", "yes", "maybe keep", "  "],
    )
    def test_invalid_generations(self, raw):
        """Verifies invalid generations map to __invalid__ with NA label."""
        result = parse_generation(raw)
        assert result.predicted_decision == INVALID_DECISION
        assert result.predicted_label is None
