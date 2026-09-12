"""Tests for experiment 6 yes/no pair labeling helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from experiments.ai_simulation_responses_2026_09_11.shared.schema import (
    LlmPairYesNoModel,
    expand_remove_indexes,
    pair_record_id,
    pair_yes_no_spec,
    parse_pair_record_id,
    parse_remove_yes_no,
    stitch_pair_predictions,
)


class TestParseRemoveYesNo:
    """Tests for parse_remove_yes_no function."""

    def test_yes_is_one(self):
        """yes maps to remove=1."""
        # Arrange
        expected = 1

        # Act
        result = parse_remove_yes_no("yes")

        # Assert
        assert result == expected

    def test_no_is_zero(self):
        """no maps to keep=0."""
        # Arrange
        expected = 0

        # Act
        result = parse_remove_yes_no("no")

        # Assert
        assert result == expected

    def test_maybe_raises_value_error(self):
        """Values other than yes or no are invalid."""
        with pytest.raises(ValueError):
            parse_remove_yes_no("maybe")


class TestPairRecordId:
    """Tests for pair_record_id and parse_pair_record_id."""

    def test_round_trip_splits_on_last_colon(self):
        """Record ids encode prolific_id and pair_index."""
        # Arrange
        expected = ("abc", 7)

        # Act
        result = parse_pair_record_id(pair_record_id("abc", 7))

        # Assert
        assert result == expected

    def test_parses_existing_record_id(self):
        """parse_pair_record_id splits abc:7."""
        # Arrange
        expected = ("abc", 7)

        # Act
        result = parse_pair_record_id("abc:7")

        # Assert
        assert result == expected


class TestStitchPairPredictions:
    """Tests for stitch_pair_predictions function."""

    def test_yes_on_first_and_last_indexes(self):
        """yes on pairs 1 and 20 becomes remove indexes [1, 20]."""
        # Arrange
        rows = [("user-a", pair_index, "no") for pair_index in range(1, 21)]
        rows[0] = ("user-a", 1, "yes")
        rows[19] = ("user-a", 20, "yes")
        expected_indexes = [1, 20]
        expected_binary = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]

        # Act
        result = stitch_pair_predictions(rows)

        # Assert
        assert result["user-a"] == expected_indexes
        assert expand_remove_indexes(result["user-a"]) == expected_binary

    def test_all_no_returns_empty_list(self):
        """All no answers stitch to an empty remove list."""
        # Arrange
        rows = [("user-a", pair_index, "no") for pair_index in range(1, 21)]
        expected: list[int] = []

        # Act
        result = stitch_pair_predictions(rows)

        # Assert
        assert result["user-a"] == expected

    def test_nineteen_pairs_omits_user(self):
        """A user with 19 pairs is omitted from the stitch result."""
        # Arrange
        rows = [("user-a", pair_index, "no") for pair_index in range(1, 20)]

        # Act
        result = stitch_pair_predictions(rows)

        # Assert
        assert result == {}


class TestPairYesNoSpec:
    """Tests for pair_yes_no_spec function."""

    def test_schema_accepts_yes_and_rejects_extra_fields(self):
        """The LLM schema accepts yes/no and forbids extra fields."""
        # Arrange
        spec = pair_yes_no_spec("openai")

        # Act
        accepted = spec.llm_output_schema.model_validate({"remove": "yes"})

        # Assert
        assert accepted.remove == "yes"
        with pytest.raises(ValidationError):
            spec.llm_output_schema.model_validate({"remove": "maybe"})
        with pytest.raises(ValidationError):
            spec.llm_output_schema.model_validate({"remove": "yes", "extra": 1})
        assert spec.llm_output_schema is LlmPairYesNoModel
