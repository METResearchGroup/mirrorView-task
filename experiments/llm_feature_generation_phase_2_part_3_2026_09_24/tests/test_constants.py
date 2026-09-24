"""Tests for experiment constants."""

from __future__ import annotations

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants


class TestSplitSeed:
    """Tests for SPLIT_SEED."""

    def test_split_seed_is_42(self) -> None:
        """SPLIT_SEED matches the plan contract."""
        assert constants.SPLIT_SEED == 42


class TestTextArms:
    """Tests for TEXT_ARMS."""

    def test_text_arms_match_contract(self) -> None:
        """TEXT_ARMS lists the three text arms."""
        expected = ("original_only", "mirror_only", "paired")
        assert constants.TEXT_ARMS == expected


class TestS3Prefix:
    """Tests for S3_PREFIX."""

    def test_s3_prefix_matches_experiment_folder(self) -> None:
        """S3_PREFIX mirrors the experiment folder path."""
        expected = "experiments/llm_feature_generation_phase_2_part_3_2026_09_24/"
        assert constants.S3_PREFIX == expected


class TestMinRaters:
    """Tests for MIN_RATERS."""

    def test_min_raters_is_4(self) -> None:
        """MIN_RATERS matches the reasoning reference."""
        assert constants.MIN_RATERS == 4
