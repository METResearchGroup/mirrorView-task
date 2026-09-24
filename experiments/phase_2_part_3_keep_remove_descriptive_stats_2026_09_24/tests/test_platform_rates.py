"""Tests for platform keep/remove crosstabs and toxicity joins."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.platform_rates import (
    PLATFORM_COLUMNS,
    PLATFORM_TOXICITY_COLUMNS,
    PROPORTION_DECIMALS,
    build_labeled_posts,
    build_platform_crosstab,
    build_platform_toxicity_crosstab,
    column_proportions,
    derive_platform,
    modal_decision,
)


@pytest.fixture
def tiny_per_post() -> pd.DataFrame:
    """Two posts across Bluesky and Reddit with distinct vote counts."""
    return pd.DataFrame(
        [
            {
                "post_id": "bluesky_a",
                "keep_count": 2,
                "remove_count": 0,
            },
            {
                "post_id": "reddit_b",
                "keep_count": 1,
                "remove_count": 1,
            },
        ]
    )


@pytest.fixture
def tiny_stimuli() -> pd.DataFrame:
    """Stimuli rows matching the tiny per-post fixture."""
    return pd.DataFrame(
        [
            {
                "post_primary_key": "bluesky_a",
                "sample_toxicity_type": "sample_low_toxicity",
            },
            {
                "post_primary_key": "reddit_b",
                "sample_toxicity_type": "sample_high_toxicity",
            },
        ]
    )


@pytest.fixture
def labeled_posts(
    tiny_per_post: pd.DataFrame, tiny_stimuli: pd.DataFrame
) -> pd.DataFrame:
    """Labeled posts built from the tiny fixture."""
    return build_labeled_posts(tiny_per_post, tiny_stimuli)


class TestModalDecision:
    """Tests for modal_decision()."""

    def test_tie_becomes_remove(self):
        """Return remove when keep and remove counts are equal."""
        result = modal_decision(keep_count=1, remove_count=1)

        assert result == "remove"


class TestBuildPlatformCrosstab:
    """Tests for build_platform_crosstab()."""

    def test_counts_keep_and_remove_rows(self, labeled_posts: pd.DataFrame):
        """Keep row sums to one Bluesky post; remove row sums to one Reddit tie."""
        result = build_platform_crosstab(labeled_posts)

        assert int(result.loc["keep"].sum()) == 1
        assert int(result.loc["remove"].sum()) == 1


class TestColumnProportions:
    """Tests for column_proportions()."""

    def test_positive_columns_sum_to_one_at_four_decimals(
        self, labeled_posts: pd.DataFrame
    ):
        """Each platform column with counts sums to 1.0000 at four decimal places."""
        counts = build_platform_crosstab(labeled_posts)

        result = column_proportions(counts)

        for platform in PLATFORM_COLUMNS:
            column_total = int(counts[platform].sum())
            if column_total == 0:
                assert result[platform].isna().all()
                continue
            rounded = result[platform].round(PROPORTION_DECIMALS)
            assert float(rounded.sum()) == pytest.approx(1.0000)


class TestBuildPlatformToxicityCrosstab:
    """Tests for build_platform_toxicity_crosstab()."""

    def test_column_order_matches_contract(self, labeled_posts: pd.DataFrame):
        """Return columns in PLATFORM_TOXICITY_COLUMNS order."""
        result = build_platform_toxicity_crosstab(labeled_posts)

        assert list(result.columns) == list(PLATFORM_TOXICITY_COLUMNS)


class TestDerivePlatform:
    """Tests for derive_platform()."""

    def test_unknown_prefix_raises_value_error(self):
        """Raise ValueError when the post id prefix is not recognized."""
        with pytest.raises(ValueError):
            derive_platform("unknown_123")


class TestBuildLabeledPosts:
    """Tests for build_labeled_posts()."""

    def test_missing_stimuli_row_raises_value_error(
        self, tiny_per_post: pd.DataFrame, tiny_stimuli: pd.DataFrame
    ):
        """Raise ValueError when a per-post id lacks a stimuli match."""
        per_post = pd.concat(
            [
                tiny_per_post,
                pd.DataFrame(
                    [{"post_id": "twitter_missing", "keep_count": 1, "remove_count": 0}]
                ),
            ],
            ignore_index=True,
        )

        with pytest.raises(ValueError):
            build_labeled_posts(per_post, tiny_stimuli)
