"""Tests for within-topic log-odds contrasts."""

from __future__ import annotations

from experiments.bertopic_original_mirror_part3_2026_09_24.src.analyze_cross_role import (
    log_odds_with_dirichlet,
    top_contrast_terms,
)


class TestLogOdds:
    """Tests for log_odds_with_dirichlet."""

    def test_log_odds_positive_favors_original(self) -> None:
        """A term seen only on the original side has positive log-odds."""
        delta = log_odds_with_dirichlet(count_o=10, count_m=0, n_o=20, n_m=20, alpha=0.01)

        assert delta > 0


class TestTopContrastTerms:
    """Tests for top_contrast_terms."""

    def test_top_15_per_role_per_topic(self) -> None:
        """Each role keeps at most 15 terms."""
        original_counts = {f"o{index}": 5 for index in range(20)}
        mirror_counts = {f"m{index}": 5 for index in range(20)}

        result = top_contrast_terms(0, original_counts, mirror_counts)

        assert result.groupby("role").size().max() <= 15
        assert set(result["role"]) == {"original", "mirror"}
