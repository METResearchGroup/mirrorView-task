"""Tests for four-cell agreement assignment and results formatting."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.agreement import (
    assign_agreement_cell,
    build_four_cell_counts,
    build_four_cell_shares,
    build_vote_funnel,
)
from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.platform_rates import (
    DECISION_ROWS,
    PLATFORM_COLUMNS,
    PLATFORM_TOXICITY_COLUMNS,
    PROPORTION_DECIMALS,
    modal_decision,
)
from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.write_results import (
    format_results_markdown,
)


def _per_post_row(
    *,
    post_id: str,
    n_raters: int,
    keep_count: int,
    remove_count: int,
    is_unanimous: bool,
) -> dict[str, object]:
    return {
        "post_id": post_id,
        "n_raters": n_raters,
        "keep_count": keep_count,
        "remove_count": remove_count,
        "n_unique_decisions": 1 if is_unanimous else 2,
        "is_unanimous": is_unanimous,
        "original_text": "orig",
        "mirror_text": "mirror",
    }


class TestAssignAgreementCell:
    """Tests for assign_agreement_cell."""

    def test_unanimous_keep_cell(self):
        """Unanimous keep rows map to unanimous_keep."""
        row = pd.Series(
            _per_post_row(
                post_id="twitter_1",
                n_raters=3,
                keep_count=3,
                remove_count=0,
                is_unanimous=True,
            )
        )
        result = assign_agreement_cell(row)
        assert result == "unanimous_keep"

    def test_majority_keep_cell(self):
        """Majority keep rows map to majority_keep."""
        row = pd.Series(
            _per_post_row(
                post_id="reddit_1",
                n_raters=3,
                keep_count=2,
                remove_count=1,
                is_unanimous=False,
            )
        )
        result = assign_agreement_cell(row)
        assert result == "majority_keep"

    def test_unanimous_remove_cell(self):
        """Unanimous remove rows map to unanimous_remove."""
        row = pd.Series(
            _per_post_row(
                post_id="twitter_2",
                n_raters=3,
                keep_count=0,
                remove_count=3,
                is_unanimous=True,
            )
        )
        result = assign_agreement_cell(row)
        assert result == "unanimous_remove"

    def test_majority_remove_cell(self):
        """Majority remove rows map to majority_remove."""
        row = pd.Series(
            _per_post_row(
                post_id="reddit_2",
                n_raters=3,
                keep_count=1,
                remove_count=2,
                is_unanimous=False,
            )
        )
        result = assign_agreement_cell(row)
        assert result == "majority_remove"

    def test_exact_tie_raises(self):
        """Exact ties raise ValueError."""
        row = pd.Series(
            _per_post_row(
                post_id="bluesky_1",
                n_raters=4,
                keep_count=2,
                remove_count=2,
                is_unanimous=False,
            )
        )
        with pytest.raises(ValueError):
            assign_agreement_cell(row)


class TestBuildFourCellCounts:
    """Tests for build_four_cell_counts."""

    def test_tie_excluded_from_four_cell_universe(self):
        """Tie posts are absent from four-cell counts."""
        per_post = pd.DataFrame(
            [
                _per_post_row(
                    post_id="twitter_1",
                    n_raters=3,
                    keep_count=3,
                    remove_count=0,
                    is_unanimous=True,
                ),
                _per_post_row(
                    post_id="reddit_1",
                    n_raters=4,
                    keep_count=2,
                    remove_count=2,
                    is_unanimous=False,
                ),
            ]
        )
        result = build_four_cell_counts(per_post)
        assert int(result["count"].sum()) == 1
        assert "unanimous_keep" in set(result["cell"])

    def test_modal_tie_is_remove_but_excluded_from_four_cell(self):
        """Modal tie-break is remove while four-cell excludes the tie post."""
        per_post = pd.DataFrame(
            [
                _per_post_row(
                    post_id="reddit_1",
                    n_raters=4,
                    keep_count=2,
                    remove_count=2,
                    is_unanimous=False,
                )
            ]
        )
        assert modal_decision(2, 2) == "remove"
        result = build_four_cell_counts(per_post)
        assert int(result["count"].sum()) == 0


class TestBuildVoteFunnel:
    """Tests for build_vote_funnel and share denominators."""

    def test_funnel_counts_match_remaining_posts(self):
        """Dropped posts and the four-cell total use the same per-post frame."""
        per_post = pd.DataFrame(
            [
                _per_post_row(
                    post_id="keep_all",
                    n_raters=3,
                    keep_count=3,
                    remove_count=0,
                    is_unanimous=True,
                ),
                _per_post_row(
                    post_id="too_few",
                    n_raters=2,
                    keep_count=2,
                    remove_count=0,
                    is_unanimous=True,
                ),
                _per_post_row(
                    post_id="tie",
                    n_raters=4,
                    keep_count=2,
                    remove_count=2,
                    is_unanimous=False,
                ),
            ]
        )
        funnel = build_vote_funnel(per_post)
        counts = dict(zip(funnel["metric"], funnel["count"], strict=True))
        shares = build_four_cell_shares(build_four_cell_counts(per_post))
        assert counts["posts_after_vote_clean"] == 3
        assert counts["posts_dropped_lt_3_raters"] == 1
        assert counts["posts_dropped_ties"] == 1
        assert counts["posts_remaining"] == 1
        assert int(shares["count"].sum()) == counts["posts_remaining"]
        assert float(shares["share"].sum()) == 1.0


class TestFormatResultsMarkdown:
    """Tests for format_results_markdown."""

    def test_contains_required_table_headers(self):
        """Rendered markdown includes all five required table headers."""
        platform_counts = pd.DataFrame(
            [[1, 2, 3], [4, 5, 6]],
            index=list(DECISION_ROWS),
            columns=list(PLATFORM_COLUMNS),
        )
        platform_proportions = platform_counts.div(platform_counts.sum(axis=0), axis=1)
        platform_toxicity_proportions = pd.DataFrame(
            [[0.5] * len(PLATFORM_TOXICITY_COLUMNS)] * 2,
            index=list(DECISION_ROWS),
            columns=list(PLATFORM_TOXICITY_COLUMNS),
        )
        four_cell_counts = pd.DataFrame(
            {
                "cell": ["unanimous_keep", "majority_keep"],
                "count": [1, 1],
            }
        )
        four_cell_shares = four_cell_counts.assign(share=[0.5, 0.5])
        funnel = pd.DataFrame(
            {
                "metric": [
                    "posts_after_vote_clean",
                    "posts_dropped_lt_3_raters",
                    "posts_dropped_ties",
                    "posts_remaining",
                ],
                "count": [2, 0, 0, 2],
            }
        )
        result = format_results_markdown(
            platform_counts,
            platform_proportions,
            platform_toxicity_proportions,
            four_cell_counts,
            four_cell_shares,
            funnel,
        )
        assert "| decision | Bluesky | Reddit | Twitter |" in result
        assert "| cell | count | share |" in result
        assert "| metric | count |" in result
        toxicity_header = (
            "| decision | "
            + " | ".join(PLATFORM_TOXICITY_COLUMNS)
            + " |"
        )
        assert toxicity_header in result
