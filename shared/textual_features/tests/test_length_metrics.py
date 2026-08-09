"""Parity tests for length / punctuation textual features."""

from __future__ import annotations

import pytest

from shared.textual_features.avg_sentence_length import AvgSentenceLengthMetric
from shared.textual_features.char_count import CharCountMetric
from shared.textual_features.punctuation_count import PunctuationCountMetric
from shared.textual_features.punctuation_density import PunctuationDensityMetric
from shared.textual_features.sentence_count import SentenceCountMetric
from shared.textual_features.word_count import WordCountMetric

FIXTURE_TEXT = "Hello world!"
EMPTY_TEXT = ""


class TestCharCountMetric:
    """Tests for CharCountMetric.calculate()."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            (FIXTURE_TEXT, 12.0),
            (EMPTY_TEXT, 0.0),
        ],
    )
    def test_calculate(self, text: str, expected: float) -> None:
        """Verifies character count on fixture and empty strings."""
        result = CharCountMetric().calculate(text)
        assert result == expected


class TestWordCountMetric:
    """Tests for WordCountMetric.calculate()."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            (FIXTURE_TEXT, 2.0),
            (EMPTY_TEXT, 0.0),
        ],
    )
    def test_calculate(self, text: str, expected: float) -> None:
        """Verifies word count on fixture and empty strings."""
        result = WordCountMetric().calculate(text)
        assert result == expected


class TestSentenceCountMetric:
    """Tests for SentenceCountMetric.calculate()."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            (FIXTURE_TEXT, 1.0),
            (EMPTY_TEXT, 0.0),
        ],
    )
    def test_calculate(self, text: str, expected: float) -> None:
        """Verifies sentence count on fixture and empty strings."""
        result = SentenceCountMetric().calculate(text)
        assert result == expected


class TestAvgSentenceLengthMetric:
    """Tests for AvgSentenceLengthMetric.calculate()."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            (FIXTURE_TEXT, 2.0),
            (EMPTY_TEXT, 0.0),
        ],
    )
    def test_calculate(self, text: str, expected: float) -> None:
        """Verifies average sentence length on fixture and empty strings."""
        result = AvgSentenceLengthMetric().calculate(text)
        assert result == expected


class TestPunctuationCountMetric:
    """Tests for PunctuationCountMetric.calculate()."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            (FIXTURE_TEXT, 1.0),
            (EMPTY_TEXT, 0.0),
        ],
    )
    def test_calculate(self, text: str, expected: float) -> None:
        """Verifies punctuation count on fixture and empty strings."""
        result = PunctuationCountMetric().calculate(text)
        assert result == expected


class TestPunctuationDensityMetric:
    """Tests for PunctuationDensityMetric.calculate()."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            (FIXTURE_TEXT, 1.0 / 12.0),
            (EMPTY_TEXT, 0.0),
        ],
    )
    def test_calculate(self, text: str, expected: float) -> None:
        """Verifies punctuation density on fixture and empty strings."""
        result = PunctuationDensityMetric().calculate(text)
        assert result == expected
