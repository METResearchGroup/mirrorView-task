"""Tests for held-out analysis Q1 through Q7."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.analyze import (
    enrich_test_labels,
    load_test_labels,
    run_q1,
    run_q1_replication,
    run_q2,
    run_q3,
    run_q4,
    run_q5,
    run_q6,
    run_q7,
)


class TestLoadTestLabels:
    """Tests for load_test_labels."""

    def test_analyze_filters_test_split_only(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        assert (frame["split"] == constants.TEST_SPLIT).all()
        assert set(frame["post_id"]) == synthetic_test_post_ids


class TestRunQ1Replication:
    """Tests for run_q1_replication."""

    def test_q1_replication_uses_part3_only_on_part2_catalog(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_cohort_frame: pd.DataFrame,
        synthetic_part3_cohort: pd.DataFrame,
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        enriched = enrich_test_labels(frame, synthetic_cohort_frame)
        result = run_q1_replication(enriched, synthetic_part3_cohort, None)
        assert result["uses_participant_filter"] == constants.PARTICIPANT_FILTER_PART3_ONLY
        assert result["post_ids"] == ["post_catalog"]


class TestRunQ1:
    """Tests for run_q1."""

    def test_q1_prevalence_bh_correction(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_feature_ids: list[str],
        synthetic_cohort_frame: pd.DataFrame,
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        enriched = enrich_test_labels(frame, synthetic_cohort_frame)
        result = run_q1(enriched, synthetic_feature_ids)
        assert result["n_posts"] == len(synthetic_test_post_ids)
        assert "q_value" in result["features"][0]
        assert "p_value" in result["features"][0]


class TestRunQ2:
    """Tests for run_q2."""

    def test_q2_stance_concordance(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_feature_ids: list[str],
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        result = run_q2(frame, synthetic_feature_ids)
        assert result["features"][0]["concordance_rate"] >= 0.0


class TestRunQ3:
    """Tests for run_q3."""

    def test_q3_flip_mismatch_rate(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_feature_ids: list[str],
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        result = run_q3(frame, synthetic_feature_ids)
        row = result["features"][0]
        assert "orig_present_mirror_absent_rate" in row
        assert "mirror_present_orig_absent_rate" in row


class TestRunQ4:
    """Tests for run_q4."""

    def test_q4_logistic_auc_log_loss(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_feature_ids: list[str],
        synthetic_cohort_frame: pd.DataFrame,
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        enriched = enrich_test_labels(frame, synthetic_cohort_frame)
        result = run_q4(enriched, synthetic_feature_ids)
        assert "auc" in result["models"]["original_only"]
        assert "log_loss" in result["models"]["paired"]


class TestRunQ5:
    """Tests for run_q5."""

    def test_q5_three_group_prevalence(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_feature_ids: list[str],
        synthetic_cohort_frame: pd.DataFrame,
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        enriched = enrich_test_labels(frame, synthetic_cohort_frame)
        result = run_q5(enriched, synthetic_feature_ids)
        assert constants.GROUP_SPLIT in result["group_counts"]


class TestRunQ6:
    """Tests for run_q6."""

    def test_q6_party_stance_feature_table(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_feature_ids: list[str],
        synthetic_cohort_frame: pd.DataFrame,
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        enriched = enrich_test_labels(frame, synthetic_cohort_frame)
        trials = pd.DataFrame(
            {
                "post_id": ["post_test_a", "post_test_b"],
                "decision": [constants.DECISION_REMOVE, constants.DECISION_REMOVE],
                "moderator_party": ["democrat", "republican"],
                "prolific_id": ["w1", "w2"],
            }
        )
        result = run_q6(enriched, synthetic_feature_ids, trial_frame=trials)
        columns = set(result["rows"][0].keys())
        assert {"moderator_party", "post_stance", "feature_id", "remove_rate"}.issubset(columns)


class TestRunQ7:
    """Tests for run_q7."""

    def test_q7_nested_models_delta_auc(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_feature_ids: list[str],
        synthetic_cohort_frame: pd.DataFrame,
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        enriched = enrich_test_labels(frame, synthetic_cohort_frame)
        result = run_q7(enriched, synthetic_feature_ids)
        assert "delta_auc" in result


class TestDiscoveryGuard:
    """Tests that discovery rows never enter Q metrics."""

    def test_no_discovery_rows_in_q1_q7_metrics(
        self,
        synthetic_label_matrix: Path,
        synthetic_test_post_ids: set[str],
        synthetic_feature_ids: list[str],
        synthetic_cohort_frame: pd.DataFrame,
    ) -> None:
        frame = load_test_labels(synthetic_label_matrix, synthetic_test_post_ids)
        enriched = enrich_test_labels(frame, synthetic_cohort_frame)
        discovery_frame = enriched.copy()
        discovery_frame.loc[0, "split"] = constants.DISCOVERY_SPLIT
        with pytest.raises(ValueError):
            run_q1(discovery_frame, synthetic_feature_ids)
