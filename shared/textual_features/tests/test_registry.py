"""Tests for the textual features registry catalog."""

from __future__ import annotations

import pytest

from shared.textual_features.registry import (
    AVG_SENTENCE_LENGTH,
    CHAR_COUNT,
    FEATURES,
    FLESCH_KINCAID_GRADE,
    FeatureKind,
    INTERGROUP,
    PRIME,
    PUNCTUATION_COUNT,
    PUNCTUATION_DENSITY,
    READING_EASE,
    SENTENCE_COUNT,
    VALENCE,
    WORD_COUNT,
    get_feature,
)

REQUIRED_NAMES = [
    CHAR_COUNT,
    WORD_COUNT,
    SENTENCE_COUNT,
    AVG_SENTENCE_LENGTH,
    PUNCTUATION_COUNT,
    PUNCTUATION_DENSITY,
    FLESCH_KINCAID_GRADE,
    READING_EASE,
    VALENCE,
    INTERGROUP,
    PRIME,
]

DETERMINISTIC_NAMES = [
    CHAR_COUNT,
    WORD_COUNT,
    SENTENCE_COUNT,
    AVG_SENTENCE_LENGTH,
    PUNCTUATION_COUNT,
    PUNCTUATION_DENSITY,
    FLESCH_KINCAID_GRADE,
    READING_EASE,
]

CLASSIFIER_NAMES = [VALENCE, INTERGROUP, PRIME]


class TestGetFeature:
    """Tests for get_feature()."""

    def test_all_required_names_are_registered(self) -> None:
        """Verifies all eleven plan registry names exist in FEATURES."""
        missing = [name for name in REQUIRED_NAMES if name not in FEATURES]
        assert missing == []

    def test_unknown_name_raises_key_error_with_valid_names(self) -> None:
        """Verifies unknown names raise KeyError listing valid keys."""
        with pytest.raises(KeyError, match="CHAR_COUNT") as exc_info:
            get_feature("NOT_A_FEATURE")
        assert "Unknown textual feature" in str(exc_info.value)

    @pytest.mark.parametrize("name", DETERMINISTIC_NAMES)
    def test_metric_entries_build_with_expected_name(self, name: str) -> None:
        """Verifies metric entries build and expose the frozen metric_name."""
        entry = get_feature(name)
        assert entry.kind is FeatureKind.METRIC
        metric = entry.build()
        assert metric.name == entry.metric_name
        assert metric.calculate("Hello world!") >= 0.0

    @pytest.mark.parametrize("name", CLASSIFIER_NAMES)
    def test_classifier_entries_expose_classify_post(self, name: str) -> None:
        """Verifies classifier entries expose a callable classify_post."""
        entry = get_feature(name)
        assert entry.kind is FeatureKind.CLASSIFIER
        assert callable(entry.classify_post)
        assert entry.build is None
        assert entry.metric_name is None
