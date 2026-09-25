"""Tests for shared.metrics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score, precision_score, recall_score

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.metrics import (
    build_results_payload,
    hard_label_metrics,
    latency_summary,
    probability_metrics,
    spearman_remove_share,
    subgroup_metrics,
    trivial_baselines,
    tune_threshold_for_f1,
)


class TestHardLabelMetrics:
    """Tests for hard_label_metrics function."""

    def test_matches_sklearn_positive_remove(self):
        """F1, precision, recall use remove as positive class."""
        y_true = [1, 0, 1, 0]
        y_pred = [1, 0, 0, 0]

        result = hard_label_metrics(y_true, y_pred)

        assert result.f1 == f1_score(y_true, y_pred, zero_division=0)
        assert result.precision == precision_score(y_true, y_pred, zero_division=0)
        assert result.recall == recall_score(y_true, y_pred, zero_division=0)


class TestProbabilityMetrics:
    """Tests for probability_metrics function."""

    def test_thresholded_predictions_and_confusion(self):
        """Derives labels from p_remove at threshold 0.5."""
        y_true = [1, 0, 1, 0]
        p_remove = [0.9, 0.1, 0.4, 0.2]

        result = probability_metrics(y_true, p_remove, threshold=0.5)

        assert result.confusion.tp == 1
        assert result.confusion.fp == 0
        assert result.confusion.fn == 1
        assert result.confusion.tn == 2
        assert math.isfinite(result.roc_auc)
        assert math.isfinite(result.pr_auc)


class TestTuneThresholdForF1:
    """Tests for tune_threshold_for_f1 function."""

    def test_finds_perfect_f1_on_separable_scores(self):
        """Returns F1=1.0 when scores separate removes from keeps."""
        y_true = [1] * 2 + [0] * 8
        p_remove = [0.95, 0.85, 0.15, 0.05, 0.1, 0.2, 0.05, 0.15, 0.1, 0.05]

        threshold, best_f1 = tune_threshold_for_f1(y_true, p_remove)

        assert best_f1 == 1.0
        assert threshold in [round(value, 2) for value in np.arange(0.05, 1.0, 0.05)]


class TestTrivialBaselines:
    """Tests for trivial_baselines function."""

    def test_keep_all_remove_all_and_random_std(self):
        """keep-all F1 is zero; remove-all matches sklearn; random std is non-negative."""
        y_true = [1] * 20 + [0] * 80

        result = trivial_baselines(y_true)

        assert result.keep_all_f1 == 0.0
        assert result.remove_all_f1 == f1_score(y_true, [1] * len(y_true), zero_division=0)
        assert result.prevalence_random_f1_std >= 0.0


class TestSpearmanRemoveShare:
    """Tests for spearman_remove_share function."""

    def test_perfect_positive_correlation(self):
        """Monotonic inputs yield rho=1.0."""
        remove_share = [0.0, 0.5, 1.0]
        p_remove = [0.0, 0.5, 1.0]

        result = spearman_remove_share(remove_share, p_remove)

        assert result == 1.0


class TestLatencySummary:
    """Tests for latency_summary function."""

    def test_request_p50(self):
        """Request p50 uses latency.percentile_ms."""
        request_latencies = [100.0, 200.0, 300.0]
        post_latencies = [50.0, 150.0, 250.0]

        result = latency_summary(request_latencies, post_latencies)

        assert result["request"].p50_ms == 200.0


class TestSubgroupMetrics:
    """Tests for subgroup_metrics function."""

    def test_emits_stance_and_unanimous_subgroups(self):
        """Returns metrics rows for configured subgroup dimensions."""
        frame = pd.DataFrame(
            {
                "keep_remove_label": [1, 0, 1, 0],
                "p_remove": [0.9, 0.1, 0.8, 0.2],
                "sampled_stance": ["left", "left", "right", "right"],
                "sample_toxicity_type": ["low", "low", "high", "high"],
                "is_unanimous": [True, False, True, False],
                "remove_share": [1.0, 0.25, 0.75, 0.0],
            }
        )

        result = subgroup_metrics(frame)

        subgroup_names = {row.subgroup_name for row in result}
        assert "stance" in subgroup_names
        assert "toxicity" in subgroup_names
        assert "unanimous" in subgroup_names
        assert "remove_share_quartile" in subgroup_names


class TestBuildResultsPayload:
    """Tests for build_results_payload function."""

    def test_required_top_level_keys(self):
        """Payload includes headline_split and metrics_at_0_5."""
        metrics = probability_metrics([1, 0], [0.9, 0.1])
        trivial = trivial_baselines([1, 0])
        latency = latency_summary([100.0], [50.0])

        payload = build_results_payload(
            ablation_id="A1_pair_study_prompt",
            split_metrics={"test": metrics, "full": metrics},
            dev_tuned_test_metrics=metrics,
            dev_tuned_threshold=0.5,
            trivial=trivial,
            subgroups=[],
            spearman=1.0,
            latency=latency,
            cost=__import__(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.metrics",
                fromlist=["CostSummary"],
            ).CostSummary(input_tokens=1, output_tokens=1, cost_usd=0.01),
            wall_time_s=1.0,
        )

        assert payload["headline_split"] == "test"
        assert payload["secondary_split"] == "full"
        assert "metrics_at_0_5" in payload
        assert "test" in payload["metrics_at_0_5"]
