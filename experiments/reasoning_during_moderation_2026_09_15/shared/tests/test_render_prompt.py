"""Tests for render_prompt()."""

from __future__ import annotations

from experiments.llm_prompt_engineering_2026_08_05.prompt import (
    KEEP_REMOVE_FEATURES_ADDENDUM,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    CLOSING_LINE,
    ROLE_MIRROR,
    ROLE_ORIGINAL,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.prompt import (
    render_prompt,
)

ABORTION_ORIGINAL = (
    "I'm a bleeding-heart liberal, and I think the issue of abortion is "
    "obviously about protecting women's rights!"
)
WRONG_CLOSING = "Allow Or Remove?"
CLICK_NEXT = "Click Next"


class TestRenderPrompt:
    """Tests for render_prompt function."""

    def test_original_first_without_criteria(self) -> None:
        """Verifies Post 1 is original and the website closing line is used."""
        result = render_prompt("o", "m", ROLE_ORIGINAL, False)
        expected_end = CLOSING_LINE

        assert "Post 1: o" in result
        assert "Post 2: m" in result
        assert result.rstrip().endswith(expected_end)
        assert "There are no right or wrong answers" in result
        assert "political mirrors" in result
        assert WRONG_CLOSING not in result
        assert CLICK_NEXT not in result
        assert KEEP_REMOVE_FEATURES_ADDENDUM.strip() not in result

    def test_mirror_first_keeps_instruction_example(self) -> None:
        """Verifies Post 1 is the mirror while the abortion example stays fixed."""
        result = render_prompt("o", "m", ROLE_MIRROR, False)

        assert "Post 1: m" in result
        assert "Post 2: o" in result
        assert ABORTION_ORIGINAL in result

    def test_criteria_addendum_before_posts(self) -> None:
        """Verifies the addendum sits after the judgment paragraph and before Post 1."""
        result = render_prompt("o", "m", ROLE_ORIGINAL, True)
        addendum_at = result.find(KEEP_REMOVE_FEATURES_ADDENDUM.strip())
        post_at = result.find("Post 1:")
        judgment_at = result.find("using your own judgment")

        assert addendum_at != -1
        assert judgment_at < addendum_at < post_at
