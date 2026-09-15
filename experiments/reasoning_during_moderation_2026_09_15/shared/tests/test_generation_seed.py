"""Tests for generation_seed()."""

from __future__ import annotations

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    UINT32_MODULUS,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.runner import (
    generation_seed,
)


class TestGenerationSeed:
    """Tests for generation_seed function."""

    def test_same_post_is_stable_uint32(self) -> None:
        """Verifies two calls match and the seed fits in 32 bits."""
        first = generation_seed("A")
        second = generation_seed("A")

        assert first == second
        assert 0 <= first < UINT32_MODULUS
