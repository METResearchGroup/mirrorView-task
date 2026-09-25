"""Tests for render_state_text view dispatch."""

from __future__ import annotations

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    render_mirror_prompt,
    render_original_prompt,
    render_pair_prompt,
    render_state_text,
)


class TestRenderStateText:
    def test_pair_view_dispatches(self) -> None:
        output = render_state_text("pair", "o", "m", "original", add_criteria=False)
        expected = render_pair_prompt("o", "m", "original", add_criteria=False)

        assert output == expected

    def test_original_view_dispatches(self) -> None:
        output = render_state_text("original", "o", "m", "original", add_criteria=False)
        expected = render_original_prompt("o")

        assert output == expected

    def test_mirror_view_dispatches(self) -> None:
        output = render_state_text("mirror", "o", "m", "original", add_criteria=False)
        expected = render_mirror_prompt("m")

        assert output == expected

    def test_unknown_view_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="unknown view: invalid"):
            render_state_text("invalid", "o", "m", "original")
