"""Tests for clone_mixed_feeds() and concat_source_rows()."""

from __future__ import annotations

import json

from experiments.load_study_assignments_2026_09_09.split import (
    FeedKind,
    feed_kind,
    parse_post_ids,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.tests.conftest import (
    CREATED_AT,
    mixed_post_ids,
    source_row,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.upsample import (
    clone_mixed_feeds,
    concat_source_rows,
)


class TestCloneMixedFeeds:
    """Tests for clone_mixed_feeds()."""

    def test_clones_keep_post_sets_and_concat_keeps_prefix(
        self, stance_by_post: dict[str, str]
    ) -> None:
        """Verifies clones reuse post ids and concat keeps the original rows first."""
        sampled_rows = [
            source_row(1, mixed_post_ids(1)),
            source_row(2, mixed_post_ids(2)),
        ]
        expected_ids = ["user-0003", "user-0004"]

        result = clone_mixed_feeds(sampled_rows, 3, CREATED_AT)

        assert [row.id for row in result] == expected_ids
        for source, clone in zip(sampled_rows, result):
            source_ids = set(json.loads(source.assigned_post_ids))
            clone_ids = set(parse_post_ids(clone.assigned_post_ids))
            assert clone_ids == source_ids
            kind = feed_kind(parse_post_ids(clone.assigned_post_ids), stance_by_post)
            assert kind is FeedKind.TEN_TEN
        combined = concat_source_rows(sampled_rows, result)
        assert combined[:2] == sampled_rows
        assert combined[2:] == result
