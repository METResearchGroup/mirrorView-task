"""Parity tests for readability textual features."""

from __future__ import annotations

from shared.textual_features.flesch_kincaid_grade import FleschKincaidGradeMetric
from shared.textual_features.reading_ease import FleschReadingEaseMetric

READABILITY_FIXTURE = "Hello world."
# Captured from pre-migration experiment metrics on READABILITY_FIXTURE.
EXPECTED_FLESCH_KINCAID_GRADE = 2.890000000000004
EXPECTED_FLESCH_READING_EASE = 77.90500000000002


class TestFleschKincaidGradeMetric:
    """Tests for FleschKincaidGradeMetric.calculate()."""

    def test_calculate_matches_legacy_fixture(self) -> None:
        """Verifies grade matches the pre-migration experiment literal."""
        result = FleschKincaidGradeMetric().calculate(READABILITY_FIXTURE)
        expected = EXPECTED_FLESCH_KINCAID_GRADE
        assert result == expected

    def test_empty_string_returns_zero(self) -> None:
        """Verifies empty input yields 0.0."""
        result = FleschKincaidGradeMetric().calculate("")
        expected = 0.0
        assert result == expected


class TestFleschReadingEaseMetric:
    """Tests for FleschReadingEaseMetric.calculate()."""

    def test_calculate_matches_legacy_fixture(self) -> None:
        """Verifies reading ease matches the pre-migration experiment literal."""
        result = FleschReadingEaseMetric().calculate(READABILITY_FIXTURE)
        expected = EXPECTED_FLESCH_READING_EASE
        assert result == expected

    def test_empty_string_returns_zero(self) -> None:
        """Verifies empty input yields 0.0."""
        result = FleschReadingEaseMetric().calculate("")
        expected = 0.0
        assert result == expected
