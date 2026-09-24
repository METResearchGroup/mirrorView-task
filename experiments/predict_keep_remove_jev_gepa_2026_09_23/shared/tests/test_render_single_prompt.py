"""Tests for original-only and mirror-only prompt rendering."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    CLOSING_LINE,
    render_mirror_prompt,
    render_original_prompt,
    render_pair_prompt,
)

GOLDEN_SINGLE_OPENING = (
    "Your task will be to review a series of real political social media posts, "
    "and decide whether each post should be allowed or removed from the platform."
)
GOLDEN_SINGLE_NO_RIGHT_WRONG = (
    "There are no right or wrong answers - we are interested in what you personally think."
)
GOLDEN_SINGLE_JOB_SENTENCE = (
    "Your job is to decide whether the post should be allowed or removed from the platform."
)


class TestRenderOriginalPrompt:
    def test_renders_original_only_view(self) -> None:
        output = render_original_prompt("o")

        assert "Post 1: o" in output
        assert GOLDEN_SINGLE_OPENING in output
        assert GOLDEN_SINGLE_JOB_SENTENCE in output
        assert GOLDEN_SINGLE_NO_RIGHT_WRONG in output
        assert "both posts in the pair" not in output
        assert "Post 2:" not in output
        assert "political mirrors" not in output
        assert output.endswith(CLOSING_LINE)


class TestRenderMirrorPrompt:
    def test_renders_mirror_only_view(self) -> None:
        output = render_mirror_prompt("m")

        assert "Post 1: m" in output
        assert GOLDEN_SINGLE_OPENING in output
        assert GOLDEN_SINGLE_JOB_SENTENCE in output
        assert GOLDEN_SINGLE_NO_RIGHT_WRONG in output
        assert "both posts in the pair" not in output
        assert "Post 2:" not in output
        assert "political mirrors" not in output
        assert output.endswith(CLOSING_LINE)


class TestSinglePostInstructionDiff:
    def test_pair_and_single_opening_sentences_differ(self) -> None:
        pair_output = render_pair_prompt("o", "m", "original", add_criteria=False)
        single_output = render_original_prompt("o")

        assert "pairs of real political" in pair_output
        assert "both posts in the pair" in pair_output
        assert "each post should be allowed" in single_output
        assert "pairs of real political" not in single_output
