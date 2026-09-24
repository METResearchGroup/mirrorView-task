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

N_SYNTHETIC_EXISTING = 40
N_SYNTHETIC_NEW = 10
N_SYNTHETIC_DISCOVERY_EXISTING = 20
N_SYNTHETIC_TEST_EXISTING = 20


def _write_post_id_csv(path: Path, post_ids: list[str]) -> None:
    pd.DataFrame({"post_id": post_ids}).to_csv(path, index=False)


def _synthetic_cohort_frame(
    n_existing: int = N_SYNTHETIC_EXISTING,
    n_new: int = N_SYNTHETIC_NEW,
) -> pd.DataFrame:
    """Build a small cohort with mixed labels for split behavior tests."""
    rows: list[dict[str, object]] = []
    decisions = ("keep", "remove", None)
    stances = ("left", "right")
    toxicity = ("low", "high")
    for index in range(n_existing):
        rows.append(
            {
                "post_id": f"synth_existing_{index:03d}",
                "modal_decision": decisions[index % 3],
                "sampled_stance": stances[index % 2],
                "sample_toxicity_type": toxicity[(index // 2) % 2],
                "in_part2_catalog": index % 2 == 0,
                "participant_filter": constants.PARTICIPANT_FILTER_ALL,
            }
        )
    new_profiles = (
        ("keep", "left", "low", True),
        ("keep", "left", "low", True),
        ("keep", "right", "high", False),
        ("keep", "right", "high", False),
        ("remove", "left", "high", True),
        ("remove", "left", "high", True),
        ("remove", "right", "low", False),
        ("remove", "right", "low", False),
        (None, "left", "low", False),
        (None, "left", "low", False),
    )
    for index, profile in enumerate(new_profiles[:n_new]):
        decision, stance, tox_type, in_catalog = profile
        rows.append(
            {
                "post_id": f"synth_new_{index:03d}",
                "modal_decision": decision,
                "sampled_stance": stance,
                "sample_toxicity_type": tox_type,
                "in_part2_catalog": in_catalog,
                "participant_filter": constants.PARTICIPANT_FILTER_ALL,
            }
        )
    return pd.DataFrame(rows)


def _seed_synthetic_existing_split(split_dir: Path, cohort: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Write discovery and test CSVs for the first existing posts only."""
    existing_ids = cohort["post_id"].iloc[:N_SYNTHETIC_EXISTING].astype(str).tolist()
    prior_discovery = existing_ids[:N_SYNTHETIC_DISCOVERY_EXISTING]
    prior_test = existing_ids[N_SYNTHETIC_DISCOVERY_EXISTING:N_SYNTHETIC_EXISTING]
    split_dir.mkdir(parents=True, exist_ok=True)
    _write_post_id_csv(split_dir / "discovery_post_ids.csv", prior_discovery)
    _write_post_id_csv(split_dir / "test_post_ids.csv", prior_test)
    return prior_discovery, prior_test


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


@pytest.fixture
def synthetic_split_setup(tmp_path: Path) -> tuple[pd.DataFrame, Path, list[str], list[str]]:
    """Small cohort, tmp split dir, and prior discovery or test ID lists."""
    cohort = _synthetic_cohort_frame()
    split_dir = tmp_path / "synthetic_post_split"
    prior_discovery, prior_test = _seed_synthetic_existing_split(split_dir, cohort)
    return cohort, split_dir, prior_discovery, prior_test


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
        self, synthetic_split_setup: tuple[pd.DataFrame, Path, list[str], list[str]]
    ) -> None:
        """Prior discovery and test lists stay prefixes after new posts are assigned."""
        cohort, split_dir, prior_discovery, prior_test = synthetic_split_setup
        discovery_ids, test_ids, stats = split_with_preservation(
            cohort, constants.SPLIT_SEED, split_dir
        )
        assert stats.n_existing_preserved == N_SYNTHETIC_EXISTING
        assert stats.n_new_posts_assigned == N_SYNTHETIC_NEW
        assert discovery_ids[: len(prior_discovery)] == prior_discovery
        assert test_ids[: len(prior_test)] == prior_test
        assert len(discovery_ids) + len(test_ids) == len(cohort)


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
        self, synthetic_split_setup: tuple[pd.DataFrame, Path, list[str], list[str]]
    ) -> None:
        """New posts keep each modal_decision stratum near 50/50."""
        cohort, _split_dir, prior_discovery, prior_test = synthetic_split_setup
        assigned = set(prior_discovery) | set(prior_test)
        new_frame = cohort.loc[~cohort["post_id"].isin(assigned)]
        assert len(new_frame) == N_SYNTHETIC_NEW
        discovery_ids, test_ids = stratified_split(new_frame, constants.SPLIT_SEED)
        assert set(discovery_ids) | set(test_ids) == set(new_frame["post_id"])
        assert set(discovery_ids) & set(test_ids) == set()
        test_ratio = len(test_ids) / len(new_frame)
        assert abs(test_ratio - constants.TEST_SIZE) <= constants.STRATIFY_MARGIN
        discovery_set = set(discovery_ids)
        stratify_labels = build_stratify_key(new_frame)
        for _label, group in new_frame.groupby(stratify_labels, sort=False):
            if len(group) < 2:
                continue
            stratum_ids = set(group["post_id"])
            n_discovery = len(stratum_ids & discovery_set)
            ratio = n_discovery / len(stratum_ids)
            assert abs(ratio - constants.TEST_SIZE) <= constants.STRATIFY_MARGIN


class TestSplitMetadataSchema:
    """Tests for split metadata output."""

    def test_split_metadata_schema(
        self, synthetic_split_setup: tuple[pd.DataFrame, Path, list[str], list[str]]
    ) -> None:
        """Written JSON contains required keys and counts from the synthetic cohort."""
        cohort, split_dir, _prior_discovery, _prior_test = synthetic_split_setup
        discovery_ids, test_ids, preservation = split_with_preservation(
            cohort, constants.SPLIT_SEED, split_dir
        )
        result = write_split_outputs(
            cohort,
            discovery_ids,
            test_ids,
            constants.SPLIT_SEED,
            preservation,
            split_dir=split_dir,
        )
        metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
        assert metadata["dataset"] == constants.DATASET_PHASE_2_PART_2_AND_3
        assert metadata["seed"] == constants.SPLIT_SEED
        assert metadata["n_discovery"] == len(discovery_ids)
        assert metadata["n_test"] == len(test_ids)
        assert metadata["n_new_posts_assigned"] == N_SYNTHETIC_NEW
        assert metadata["n_existing_preserved"] == N_SYNTHETIC_EXISTING
        assert metadata["stratify_columns"] == list(constants.STRATIFY_COLUMNS)


class TestCommittedSplitInvariants:
    """Read-only checks on committed post_split artifacts."""

    def test_committed_split_invariants(self) -> None:
        """Committed lists partition 20k posts with expected preservation counts."""
        split_dir = paths.post_split_dir()
        discovery, test = read_committed_post_ids(split_dir)
        discovery_set = set(discovery)
        test_set = set(test)
        assert len(discovery_set | test_set) == constants.EXPECTED_POST_COUNT
        assert discovery_set & test_set == set()
        assert len(discovery) == constants.EXPECTED_DISCOVERY_COUNT
        assert len(test) == constants.EXPECTED_TEST_COUNT
        metadata_path = split_dir / "split_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["dataset"] == constants.DATASET_PHASE_2_PART_2_AND_3
        assert metadata["n_existing_preserved"] == constants.LEGACY_PART3_POST_COUNT
        assert metadata["n_new_posts_assigned"] == constants.EXPECTED_NEW_POST_COUNT


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
