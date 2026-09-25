"""Tests for post-only Jev state rendering (study instruction excluded from state)."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    CLOSING_LINE,
    STUDY_INSTRUCTION,
    render_posts_only_state,
)


class TestRenderPostsOnlyState:
    """Tests for render_posts_only_state."""

    def test_pair_view_has_posts_and_closing_without_study_opening(self) -> None:
        output = render_posts_only_state("pair", "o", "m", "original")

        assert "Post 1:" in output
        assert "Post 2:" in output
        assert CLOSING_LINE in output
        assert "pairs of real political" not in output
        assert STUDY_INSTRUCTION[:40] not in output

    def test_original_view_single_post_without_mirror_example(self) -> None:
        output = render_posts_only_state("original", "only-post", "mirror-unused", "original")

        assert "Post 1: only-post" in output
        assert "Post 2:" not in output
        assert "political mirrors" not in output.lower()
