"""Tests for stratified cohort split."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort import (
    build_cohort_frame,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.split import (
    build_stratify_key,
    stratified_split,
    write_split_outputs,
)


@pytest.fixture
def cohort_frame() -> pd.DataFrame:
    """Full cohort built with the all-participant filter."""
    return build_cohort_frame("all")


class TestStratifiedSplitSizes:
    """Tests for stratified_split sizes."""

    def test_stratified_split_sizes(self, cohort_frame: pd.DataFrame) -> None:
        """18,899 posts split into 9,449 discovery and 9,450 test."""
        discovery_ids, test_ids = stratified_split(cohort_frame, constants.SPLIT_SEED)
        assert len(discovery_ids) == constants.EXPECTED_DISCOVERY_COUNT
        assert len(test_ids) == constants.EXPECTED_TEST_COUNT


class TestSplitDisjointComplete:
    """Tests for split completeness."""

    def test_split_is_disjoint_and_complete(
        self, cohort_frame: pd.DataFrame
    ) -> None:
        """Discovery and test IDs partition the cohort."""
        discovery_ids, test_ids = stratified_split(cohort_frame, constants.SPLIT_SEED)
        full_ids = set(cohort_frame["post_id"])
        assert set(discovery_ids) | set(test_ids) == full_ids
        assert set(discovery_ids) & set(test_ids) == set()


class TestSplitReproducible:
    """Tests for split reproducibility."""

    def test_split_reproducible_with_seed_42(
        self, cohort_frame: pd.DataFrame
    ) -> None:
        """Two runs with seed 42 produce identical ID lists."""
        first_discovery, first_test = stratified_split(
            cohort_frame, constants.SPLIT_SEED
        )
        second_discovery, second_test = stratified_split(
            cohort_frame, constants.SPLIT_SEED
        )
        assert first_discovery == second_discovery
        assert first_test == second_test


class TestStratifyPreservesMargin:
    """Tests for stratification quality."""

    def test_stratify_preserves_modal_decision_margin(
        self, cohort_frame: pd.DataFrame
    ) -> None:
        """Each modal_decision stratum stays near 50/50 discovery versus test."""
        discovery_ids, test_ids = stratified_split(cohort_frame, constants.SPLIT_SEED)
        discovery_set = set(discovery_ids)
        for decision, group in cohort_frame.groupby("modal_decision", dropna=False):
            stratum_ids = set(group["post_id"])
            n_discovery = len(stratum_ids & discovery_set)
            ratio = n_discovery / len(stratum_ids)
            assert abs(ratio - constants.TEST_SIZE) <= constants.STRATIFY_MARGIN


class TestSplitMetadataSchema:
    """Tests for split metadata output."""

    def test_split_metadata_schema(
        self, cohort_frame: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Written JSON contains required keys and split_seed 42."""
        discovery_ids, test_ids = stratified_split(cohort_frame, constants.SPLIT_SEED)
        result = write_split_outputs(
            cohort_frame,
            discovery_ids,
            test_ids,
            constants.SPLIT_SEED,
            constants.PARTICIPANT_FILTER_ALL,
        )
        metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
        assert metadata["split_seed"] == constants.SPLIT_SEED
        assert metadata["n_discovery"] == constants.EXPECTED_DISCOVERY_COUNT
        assert metadata["n_test"] == constants.EXPECTED_TEST_COUNT
        assert metadata["stratify_columns"] == list(constants.STRATIFY_COLUMNS)


class TestUnlabeledPostsAssigned:
    """Tests for unlabeled post assignment."""

    def test_unlabeled_posts_assigned_to_split(
        self, cohort_frame: pd.DataFrame
    ) -> None:
        """Posts with null modal_decision still receive discovery or test."""
        discovery_ids, test_ids = stratified_split(cohort_frame, constants.SPLIT_SEED)
        unlabeled = set(
            cohort_frame.loc[cohort_frame["modal_decision"].isna(), "post_id"]
        )
        assigned = set(discovery_ids) | set(test_ids)
        assert unlabeled <= assigned


class TestBuildStratifyKey:
    """Tests for build_stratify_key."""

    def test_build_stratify_key_uses_unlabeled_for_null(self) -> None:
        """Null modal_decision values become the unlabeled stratum token."""
        frame = pd.DataFrame(
            {
                "modal_decision": [None, "keep"],
                "sampled_stance": ["left", "right"],
                "sample_toxicity_type": ["low", "high"],
                "in_part2_catalog": [True, False],
            }
        )
        result = build_stratify_key(frame)
        assert constants.UNLABELED_STRATUM in result.iloc[0]
