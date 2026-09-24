"""Tests for the outcome corpus filter and party rates."""

from __future__ import annotations

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.outcomes import (
    compute_party_outcomes,
    load_outcome_corpus,
)


class TestLoadOutcomeCorpus:
    """Tests for load_outcome_corpus."""

    def test_analyze_outcomes_filters_min_raters(self) -> None:
        """Posts below the rater minimum are dropped."""
        labels = pd.DataFrame(
            {
                "post_id": ["A", "B"],
                "n_raters": [2, 3],
                "decision": ["keep", "remove"],
            }
        )

        result = load_outcome_corpus(labels, min_raters=3)

        assert list(result["post_id"]) == ["B"]


class TestComputePartyOutcomes:
    """Tests for compute_party_outcomes."""

    def test_party_keep_rate_uses_rating_level(self) -> None:
        """Democrat and republican keep rates are computed from ratings."""
        ratings = pd.DataFrame(
            {
                "topic": [1, 1, 1, 1],
                "party_group": ["democrat", "democrat", "democrat", "republican"],
                "decision": ["keep", "keep", "keep", "remove"],
            }
        )

        result = compute_party_outcomes(ratings)

        democrat = result.loc[result.party_group == "democrat"].iloc[0]
        republican = result.loc[result.party_group == "republican"].iloc[0]
        assert democrat["keep_rate"] == 1.0
        assert republican["keep_rate"] == 0.0
