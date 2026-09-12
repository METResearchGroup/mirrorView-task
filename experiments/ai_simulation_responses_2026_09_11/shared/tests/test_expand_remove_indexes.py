"""Tests for expand_remove_indexes."""

from __future__ import annotations

import pytest

from experiments.ai_simulation_responses_2026_09_11.shared.schema import (
    expand_remove_indexes,
)


class TestExpandRemoveIndexes:
    """Tests for expand_remove_indexes function."""

    def test_expands_first_and_last_indexes(self):
        """Indexes 1 and 20 map to positions 0 and 19."""
        # Arrange
        remove_pair_indexes = [1, 20]
        expected = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]

        # Act
        result = expand_remove_indexes(remove_pair_indexes)

        # Assert
        assert result == expected

    def test_empty_list_keeps_all_pairs(self):
        """An empty remove list keeps all 20 pairs."""
        # Arrange
        expected = [0] * 20

        # Act
        result = expand_remove_indexes([])

        # Assert
        assert result == expected

    def test_zero_index_raises_value_error(self):
        """Index 0 is invalid."""
        with pytest.raises(ValueError):
            expand_remove_indexes([0])

    def test_duplicate_index_raises_value_error(self):
        """Duplicate indexes are invalid."""
        with pytest.raises(ValueError):
            expand_remove_indexes([1, 1])

    def test_twenty_one_index_raises_value_error(self):
        """Index 21 is invalid."""
        with pytest.raises(ValueError):
            expand_remove_indexes([21])
