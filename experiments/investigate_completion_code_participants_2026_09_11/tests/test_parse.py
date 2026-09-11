"""Tests for parse_assignment_payload() and posts_match_assignment()."""

from experiments.investigate_completion_code_participants_2026_09_11.parse import (
    parse_assignment_payload,
    parse_post_ids,
    posts_match_assignment,
)


class TestParseAssignmentPayload:
    """Tests for parse_assignment_payload()."""

    def test_reads_nested_metadata_string(self) -> None:
        """Verifies assignment_id, s3_key, party, and condition come out of a live-shaped payload."""
        payload = (
            '{"s3_bucket": "jspsych-mirror-view-2026-09-09", '
            '"s3_key": "precomputed_assignments/batch/democrat/training_assisted/assignments.csv", '
            '"assignment_id": "democrat-training_assisted-0613", '
            '"metadata": "{\\"political_party\\": \\"democrat\\", '
            '\\"condition\\": \\"training_assisted\\"}"}'
        )
        expected = {
            "assignment_id": "democrat-training_assisted-0613",
            "s3_key": "precomputed_assignments/batch/democrat/training_assisted/assignments.csv",
            "political_party": "democrat",
            "condition": "training_assisted",
        }

        result = parse_assignment_payload(payload)

        assert result == expected


class TestParsePostIds:
    """Tests for parse_post_ids()."""

    def test_parses_json_list(self) -> None:
        """Verifies a JSON list of ids is returned as strings."""
        result = parse_post_ids('["a", "b"]')

        assert result == ["a", "b"]


class TestPostsMatchAssignment:
    """Tests for posts_match_assignment()."""

    def test_order_sensitive(self) -> None:
        """Verifies a swapped order is not a match."""
        result = posts_match_assignment(("a", "b"), ("b", "a"))

        assert result is False

    def test_equal_lists_match(self) -> None:
        """Verifies identical order matches."""
        result = posts_match_assignment(("a", "b"), ["a", "b"])

        assert result is True
