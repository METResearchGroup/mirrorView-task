"""Tests for pair-view prompt rendering."""

from __future__ import annotations

from experiments.llm_prompt_engineering_2026_08_05.prompt import (
    KEEP_REMOVE_FEATURES_ADDENDUM,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    CLOSING_LINE,
    render_pair_prompt,
)

GOLDEN_PAIR_BODY_LINES = (
    "Your task will be to review a series of pairs of real political social media posts, "
    "and decide whether both posts in the pair should be allowed or removed from the platform.",
    "The pairs are political mirrors of each other.",
    "There are no right or wrong answers - we are interested in what you personally think.",
)


class TestRenderPairPrompt:
    def test_original_first_role_renders_ordered_posts(self) -> None:
        output = render_pair_prompt("o", "m", "original", add_criteria=False)

        assert "Post 1: o" in output
        assert "Post 2: m" in output
        assert output.endswith(CLOSING_LINE)
        for line in GOLDEN_PAIR_BODY_LINES:
            assert line in output
        assert "Imperative policy or punishment demands" not in output

    def test_mirror_first_role_renders_swapped_posts(self) -> None:
        output = render_pair_prompt("o", "m", "mirror", add_criteria=False)

        assert "Post 1: m" in output
        assert "Post 2: o" in output
        assert "Original Text:" in output
        assert "Mirror Text:" in output

    def test_add_criteria_inserts_addendum_before_post_1(self) -> None:
        output = render_pair_prompt("o", "m", "original", add_criteria=True)

        job_idx = output.index(
            "Your job is to decide whether both posts in the pair should be allowed or removed from the platform."
        )
        post_1_idx = output.index("Post 1:")
        addendum_idx = output.index("Imperative policy or punishment demands")
        assert job_idx < addendum_idx < post_1_idx
        assert KEEP_REMOVE_FEATURES_ADDENDUM.strip() in output
