"""Tests for pair topic agreement."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.analyze_cross_role import (
    agreement_rate_all,
    agreement_rate_excl_noise,
    bootstrap_rate_ci,
)


def _pairs(rows: list[tuple[int, int]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["original_topic", "mirror_topic"])


class TestAgreementRateAll:
    """Tests for agreement_rate_all."""

    def test_agreement_rate_all_includes_noise_matches(self) -> None:
        """Noise matches count toward the all-pairs rate."""
        pairs = _pairs([(-1, -1), (-1, -1), (1, 2), (3, 3)])

        result = agreement_rate_all(pairs)

        assert result == 0.75


class TestAgreementRateExclNoise:
    """Tests for agreement_rate_excl_noise."""

    def test_agreement_rate_excl_noise_drops_noise_rows(self) -> None:
        """Noise pairs are dropped before the rate is computed."""
        pairs = _pairs([(-1, -1), (1, 1), (2, 3)])

        result = agreement_rate_excl_noise(pairs)

        assert result == 0.5


class TestBootstrapRateCi:
    """Tests for bootstrap_rate_ci."""

    def test_bootstrap_ci_bounds_contain_point_estimate(self) -> None:
        """The percentile interval contains the point estimate."""
        flags = np.array([True, True, False, True])

        point, low, high = bootstrap_rate_ci(flags, bootstrap_n=200, seed=42)

        assert low <= point <= high
