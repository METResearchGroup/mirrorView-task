"""Tests for scoring helpers."""

from __future__ import annotations

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from experiments.ai_simulation_responses_2026_09_11.shared.constants import POSTS_PER_USER
from experiments.ai_simulation_responses_2026_09_11.shared.score import (
    UserScoreRow,
    pooled_metrics,
    slice_tables,
    user_metrics,
)


class TestUserMetrics:
    """Tests for user_metrics function."""

    def test_matches_sklearn_with_remove_as_positive(self):
        """Metrics match sklearn with zero_division=0 and positive class 1."""
        # Arrange
        gold = [1, 0, 1, 0]
        pred = [1, 1, 1, 0]

        # Act
        result = user_metrics(gold, pred)

        # Assert
        expected = {
            "accuracy": accuracy_score(gold, pred),
            "precision": precision_score(gold, pred, zero_division=0),
            "recall": recall_score(gold, pred, zero_division=0),
            "f1": f1_score(gold, pred, zero_division=0),
        }
        assert result.accuracy == expected["accuracy"]
        assert result.precision == expected["precision"]
        assert result.recall == expected["recall"]
        assert result.f1 == expected["f1"]


class TestPooledMetrics:
    """Tests for pooled_metrics and slice_tables functions."""

    def test_mean_user_accuracy_matches_pooled_accuracy(self):
        """Mean user accuracy equals pooled accuracy when pair counts match."""
        # Arrange
        gold_a = [1] * POSTS_PER_USER
        pred_a = [1] * POSTS_PER_USER
        gold_b = [0] * POSTS_PER_USER
        pred_b = [1] * POSTS_PER_USER
        user_rows = [
            UserScoreRow("user-a", "democrat", tuple(gold_a), tuple(pred_a)),
            UserScoreRow("user-b", "republican", tuple(gold_b), tuple(pred_b)),
        ]

        # Act
        mean_user_accuracy = sum(
            user_metrics(list(row.gold), list(row.pred)).accuracy for row in user_rows
        ) / len(user_rows)
        pooled_gold = list(gold_a) + list(gold_b)
        pooled_pred = list(pred_a) + list(pred_b)
        result = pooled_metrics(pooled_gold, pooled_pred)

        # Assert
        expected = 0.5
        assert mean_user_accuracy == expected
        assert result.accuracy == expected

    def test_slice_tables_filters_party_group(self):
        """Democrat user-level means use only democrat users."""
        # Arrange
        user_rows = [
            UserScoreRow("dem-1", "democrat", (1, 0), (1, 0)),
            UserScoreRow("rep-1", "republican", (1, 1), (0, 0)),
        ]
        trial_rows = []

        # Act
        result = slice_tables(user_rows, trial_rows)
        democrat_accuracy = result["party"]["democrat"].accuracy
        republican_accuracy = result["party"]["republican"].accuracy

        # Assert
        expected_democrat = user_metrics([1, 0], [1, 0]).accuracy
        expected_republican = user_metrics([1, 1], [0, 0]).accuracy
        assert democrat_accuracy == expected_democrat
        assert republican_accuracy == expected_republican
