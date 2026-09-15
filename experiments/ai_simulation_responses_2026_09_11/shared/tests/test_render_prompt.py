"""Tests for prompt rendering."""

from __future__ import annotations

from experiments.ai_simulation_responses_2026_09_11.shared.constants import CohortUser
from experiments.ai_simulation_responses_2026_09_11.shared.prompts import (
    STUDY_SYSTEM_PROMPT,
    STUDY_SYSTEM_PROMPT_SINGLE_PAIR,
    render_pairs,
    render_single_pair,
    render_user_prompt,
)


class TestRenderUserPrompt:
    """Tests for render_pairs and render_user_prompt functions."""

    def test_render_pairs_respects_pair_order(self, sample_trials):
        """Post 1 and Post 2 follow pair_order with a Post pair heading."""
        # Arrange
        expected_post_one = "mirror-0"
        expected_post_two = "original-0"

        # Act
        result = render_pairs(sample_trials)

        # Assert
        assert "## Post pair 1" in result
        assert f"Post 1:\n{expected_post_one}" in result
        assert f"Post 2:\n{expected_post_two}" in result

    def test_experiment_one_has_no_demographics_or_reflection(
        self, sample_user, sample_trials
    ):
        """Experiment 1 prompt contains pairs only."""
        # Act
        result = render_user_prompt(1, sample_user, sample_trials)

        # Assert
        assert "## Participant information" not in result
        assert "## Participant reflection" not in result

    def test_experiment_two_omits_empty_education(self, sample_user, sample_trials):
        """Experiment 2 omits education when missing and keeps age when set."""
        # Arrange
        user = CohortUser(
            **{
                **sample_user.__dict__,
                "education": "",
            }
        )

        # Act
        result = render_user_prompt(2, user, sample_trials)

        # Assert
        assert "- Education:" not in result
        assert "- Age: 30" in result

    def test_experiment_three_includes_reflection_block(
        self, sample_user, sample_trials, reflection_question
    ):
        """Experiment 3 includes the reflection question, answer, and rating."""
        # Act
        result = render_user_prompt(3, sample_user, sample_trials)

        # Assert
        assert reflection_question in result
        assert sample_user.phase1_pair_reflection_text in result
        assert "1 = Not at all, 7 = Very much" in result
        assert str(sample_user.phase1_pair_influence_rating) in result


class TestRenderSinglePair:
    """Tests for render_single_pair function."""

    def test_follows_pair_order_without_pair_number(self, sample_trials):
        """Post 1 and Post 2 follow pair_order and omit pair numbers."""
        # Arrange
        expected = "Post 1:\nmirror-0\n\nPost 2:\noriginal-0"

        # Act
        result = render_single_pair(sample_trials[0])

        # Assert
        assert result == expected
        assert "Post pair" not in result
        assert "of 20" not in result
        assert "pair_index" not in result


class TestStudySystemPromptSinglePair:
    """Tests for STUDY_SYSTEM_PROMPT_SINGLE_PAIR."""

    def test_asks_for_yes_no_on_one_pair(self):
        """The one-pair prompt keeps the website copy and drops the 20-pair schema."""
        # Arrange / Act
        result = STUDY_SYSTEM_PROMPT_SINGLE_PAIR

        # Assert
        assert result.startswith("We are developing a new social media platform")
        assert "20 post pairs" not in result
        assert "remove_pair_indexes" not in result
        assert '"yes"' in result or "yes" in result


class TestStudySystemPrompt:
    """Tests that the 20-pair system prompt stays frozen."""

    def test_still_mentions_twenty_pairs(self):
        """The experiment 1 through 4 system prompt still describes 20 pairs."""
        # Arrange / Act
        result = STUDY_SYSTEM_PROMPT

        # Assert
        assert "You will see all 20 post pairs" in result

