"""Tests for scoring helpers."""

from __future__ import annotations

import inspect

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    MODEL_FOLDER_BEDROCK_CLAUDE,
    POSTS_PER_USER,
)
from experiments.ai_simulation_responses_2026_09_11.shared.score import (
    TrialScoreRow,
    UserScoreRow,
    _prediction_by_user,
    agreement_rate,
    mean_user_metrics,
    models_for_experiment,
    pair_predictions_by_user,
    pooled_metrics,
    score_experiment,
    slice_tables,
    user_metrics,
)
from experiments.ai_simulation_responses_2026_09_11.shared.schema import (
    expand_remove_indexes,
    stitch_pair_predictions,
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

    def test_party_slice_uses_mean_user_metrics_not_pooled(self):
        """Party slices average per-user metrics instead of pooling pairs."""
        # Arrange
        user_rows = [
            UserScoreRow("dem-1", "democrat", (1, 0), (1, 0)),
            UserScoreRow("dem-2", "democrat", (1, 1), (0, 0)),
        ]

        # Act
        result = slice_tables(user_rows, [])
        democrat = result["party"]["democrat"]

        # Assert
        expected = mean_user_metrics(user_rows)
        assert democrat.accuracy == expected.accuracy
        assert democrat.f1 == expected.f1

    def test_slice_tables_filters_toxicity_tier(self):
        """Toxicity slices pool only rows in that tier."""
        # Arrange
        trial_rows = [
            TrialScoreRow("user-a", "left", "sample_low_toxicity", 1, 1),
            TrialScoreRow("user-a", "left", "sample_high_toxicity", 0, 1),
        ]

        # Act
        result = slice_tables([], trial_rows)
        low = result["toxicity"]["sample_low_toxicity"]
        high = result["toxicity"]["sample_high_toxicity"]

        # Assert
        assert low.accuracy == pooled_metrics([1], [1]).accuracy
        assert high.accuracy == pooled_metrics([0], [1]).accuracy

    def test_slice_tables_filters_sampled_stance(self):
        """Stance slices pool only rows with that sampled stance."""
        # Arrange
        trial_rows = [
            TrialScoreRow("user-a", "left", "sample_low_toxicity", 1, 0),
            TrialScoreRow("user-a", "right", "sample_low_toxicity", 0, 1),
        ]

        # Act
        result = slice_tables([], trial_rows)
        left = result["stance"]["left"]
        right = result["stance"]["right"]

        # Assert
        assert left.accuracy == pooled_metrics([1], [0]).accuracy
        assert right.accuracy == pooled_metrics([0], [1]).accuracy


class TestPairPredictionsByUser:
    """Tests for experiment 6 yes/no stitch scoring."""

    def test_twenty_yes_no_rows_match_stitch_and_expand(self):
        """20 pair rows become the same pred as stitch plus expand_remove_indexes."""
        # Arrange
        records = []
        stitch_rows = []
        for pair_index in range(1, 21):
            remove = "yes" if pair_index in (1, 20) else "no"
            records.append(
                {"source_record_id": f"user-a:{pair_index}", "remove": remove}
            )
            stitch_rows.append(("user-a", pair_index, remove))
        labels = pd.DataFrame(records)

        # Act
        result = pair_predictions_by_user(labels)

        # Assert
        expected = stitch_pair_predictions(stitch_rows)
        assert result == expected
        assert expand_remove_indexes(result["user-a"])[0] == 1
        assert expand_remove_indexes(result["user-a"])[19] == 1

    def test_nineteen_rows_drop_the_user(self):
        """A user with 19 pair rows is absent from stitched predictions."""
        # Arrange
        records = [
            {"source_record_id": f"user-a:{pair_index}", "remove": "no"}
            for pair_index in range(1, 20)
        ]
        labels = pd.DataFrame(records)

        # Act
        result = pair_predictions_by_user(labels)

        # Assert
        assert "user-a" not in result


class TestAgreementRate:
    """Tests for experiment 1 vs experiment 6 pair agreement."""

    def test_one_pair_difference_is_nineteen_of_twenty(self):
        """Agreement is 19/20 when only the first pair differs."""
        # Arrange
        exp1 = (1,) + (0,) * 19
        exp6 = (0,) + (0,) * 19

        # Act
        result = agreement_rate(exp1, exp6)

        # Assert
        assert result == 19 / 20


class TestPredictedRemoveRate:
    """Tests for predicted remove rate on pooled pairs."""

    def test_equals_mean_of_predictions(self):
        """Predicted remove rate is sum(pred) / len(pred)."""
        # Arrange
        gold = [1, 0, 1, 0]
        pred = [1, 1, 0, 0]

        # Act
        result = pooled_metrics(gold, pred)

        # Assert
        assert result.predicted_remove_rate == sum(pred) / len(pred)


class TestModelsForExperiment:
    """Tests for models_for_experiment function."""

    def test_experiment_one_still_includes_claude(self):
        """Experiments 1 through 4 still iterate MODEL_ORDER including Claude."""
        # Arrange / Act
        result = models_for_experiment(1)
        source = inspect.getsource(score_experiment)

        # Assert
        assert MODEL_FOLDER_BEDROCK_CLAUDE in result
        assert "MODEL_ORDER" in source
        assert "remove_pair_indexes" in inspect.getsource(_prediction_by_user)

    def test_experiment_six_excludes_claude(self):
        """Experiment 6 scores the three non-Claude models."""
        # Act
        result = models_for_experiment(6)

        # Assert
        assert MODEL_FOLDER_BEDROCK_CLAUDE not in result
        assert len(result) == 3
