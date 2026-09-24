"""Tests for stratified cohort split."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort import (
    build_cohort_frame,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.split import (
    build_stratify_key,
    read_committed_post_ids,
    split_with_preservation,
    stratified_split,
    write_split_outputs,
)


@pytest.fixture
def cohort_frame() -> pd.DataFrame:
    """Full cohort built with the all-participant filter."""
    return build_cohort_frame("all")


@pytest.fixture
def split_dir(tmp_path: Path) -> Path:
    """Temporary post_split directory seeded from committed CSVs."""
    committed = paths.post_split_dir()
    target = tmp_path / "post_split"
    target.mkdir()
    for name in ("discovery_post_ids.csv", "test_post_ids.csv"):
        shutil.copy(committed / name, target / name)
    return target


class TestStratifiedSplitSizes:
    """Tests for split_with_preservation sizes."""

    def test_preservation_split_sizes(
        self, cohort_frame: pd.DataFrame, split_dir: Path
    ) -> None:
        """Union posts split into expected discovery and test counts."""
        discovery_ids, test_ids, _stats = split_with_preservation(
            cohort_frame, constants.SPLIT_SEED, split_dir
        )
        assert len(discovery_ids) == constants.EXPECTED_DISCOVERY_COUNT
        assert len(test_ids) == constants.EXPECTED_TEST_COUNT


class TestSplitDisjointComplete:
    """Tests for split completeness."""

    def test_split_is_disjoint_and_complete(
        self, cohort_frame: pd.DataFrame, split_dir: Path
    ) -> None:
        """Discovery and test IDs partition the cohort."""
        discovery_ids, test_ids, _stats = split_with_preservation(
            cohort_frame, constants.SPLIT_SEED, split_dir
        )
        full_ids = set(cohort_frame["post_id"])
        assert set(discovery_ids) | set(test_ids) == full_ids
        assert set(discovery_ids) & set(test_ids) == set()


class TestSplitPreservesExistingHalves:
    """Tests that prior discovery and test assignments are unchanged."""

    def test_existing_posts_keep_their_half(
        self, cohort_frame: pd.DataFrame, split_dir: Path
    ) -> None:
        """Committed discovery and test lists are prefixes of the union split."""
        prior_discovery, prior_test = read_committed_post_ids(split_dir)
        discovery_ids, test_ids, stats = split_with_preservation(
            cohort_frame, constants.SPLIT_SEED, split_dir
        )
        assert stats.n_existing_preserved == constants.LEGACY_PART3_POST_COUNT
        assert discovery_ids[: len(prior_discovery)] == prior_discovery
        assert test_ids[: len(prior_test)] == prior_test


class TestSplitReproducible:
    """Tests for split reproducibility."""

    def test_split_reproducible_with_seed_42(
        self, cohort_frame: pd.DataFrame, split_dir: Path
    ) -> None:
        """Two runs with seed 42 produce identical ID lists."""
        first_discovery, first_test, _ = split_with_preservation(
            cohort_frame, constants.SPLIT_SEED, split_dir
        )
        second_discovery, second_test, _ = split_with_preservation(
            cohort_frame, constants.SPLIT_SEED, split_dir
        )
        assert first_discovery == second_discovery
        assert first_test == second_test


class TestStratifyPreservesMargin:
    """Tests for stratification quality on new posts only."""

    def test_new_posts_stratify_modal_decision_margin(
        self, cohort_frame: pd.DataFrame, split_dir: Path
    ) -> None:
        """New posts keep each modal_decision stratum near 50/50."""
        prior_discovery, prior_test = read_committed_post_ids(split_dir)
        assigned = set(prior_discovery) | set(prior_test)
        new_frame = cohort_frame.loc[~cohort_frame["post_id"].isin(assigned)]
        discovery_ids, test_ids = stratified_split(new_frame, constants.SPLIT_SEED)
        discovery_set = set(discovery_ids)
        for decision, group in new_frame.groupby("modal_decision", dropna=False):
            stratum_ids = set(group["post_id"])
            n_discovery = len(stratum_ids & discovery_set)
            ratio = n_discovery / len(stratum_ids)
            assert abs(ratio - constants.TEST_SIZE) <= constants.STRATIFY_MARGIN


class TestSplitMetadataSchema:
    """Tests for split metadata output."""

    def test_split_metadata_schema(
        self, cohort_frame: pd.DataFrame, split_dir: Path
    ) -> None:
        """Written JSON contains required keys and seed 42."""
        discovery_ids, test_ids, preservation = split_with_preservation(
            cohort_frame, constants.SPLIT_SEED, split_dir
        )
        result = write_split_outputs(
            cohort_frame,
            discovery_ids,
            test_ids,
            constants.SPLIT_SEED,
            preservation,
            split_dir=split_dir,
        )
        metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
        assert metadata["dataset"] == constants.DATASET_PHASE_2_PART_2_AND_3
        assert metadata["seed"] == constants.SPLIT_SEED
        assert metadata["n_discovery"] == constants.EXPECTED_DISCOVERY_COUNT
        assert metadata["n_test"] == constants.EXPECTED_TEST_COUNT
        assert metadata["n_new_posts_assigned"] == constants.EXPECTED_NEW_POST_COUNT
        assert metadata["n_existing_preserved"] == constants.LEGACY_PART3_POST_COUNT
        assert metadata["stratify_columns"] == list(constants.STRATIFY_COLUMNS)


class TestUnlabeledPostsAssigned:
    """Tests for unlabeled post assignment."""

    def test_unlabeled_posts_assigned_to_split(
        self, cohort_frame: pd.DataFrame, split_dir: Path
    ) -> None:
        """Posts with null modal_decision still receive discovery or test."""
        discovery_ids, test_ids, _ = split_with_preservation(
            cohort_frame, constants.SPLIT_SEED, split_dir
        )
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
