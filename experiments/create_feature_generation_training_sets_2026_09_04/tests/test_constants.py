"""Tests for locked classifier and output column constants."""

import pytest

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    CLASSIFIER_NAMES,
    LABEL_COLUMNS,
    PLATFORM_RECORD_COLUMNS,
)


class TestClassifierNames:
    """Tests for CLASSIFIER_NAMES."""

    def test_classifier_names_match_locked_order(self):
        """Verify classifier names follow the locked FEATURE_REGISTRY order."""
        expected = (
            "is_likely_spam",
            "is_news_or_opinion",
            "is_political",
            "is_self_contained",
            "is_structurally_complete",
            "is_toxic_tiered",
            "political_stance",
        )

        result = CLASSIFIER_NAMES

        assert result == expected


class TestLabelColumns:
    """Tests for LABEL_COLUMNS."""

    @pytest.mark.parametrize(
        "classifier_name,expected",
        [
            ("is_news_or_opinion", ("category",)),
            ("is_toxic_tiered", ("toxicity_prob", "toxicity_tier")),
        ],
    )
    def test_label_columns_for_classifier(self, classifier_name, expected):
        """Verify label column tuples for news/opinion and tiered toxicity."""
        result = LABEL_COLUMNS[classifier_name]

        assert result == expected


class TestPlatformRecordColumns:
    """Tests for PLATFORM_RECORD_COLUMNS."""

    def test_platform_record_columns(self):
        """Verify join id and text columns per platform."""
        expected = {
            "bluesky": ("uri", "text"),
            "twitter": ("tweet_id", "text"),
            "reddit": ("comment_fullname", "body"),
        }

        result = PLATFORM_RECORD_COLUMNS

        assert result == expected
