"""Tests for Study 2 five-labeler unanimous and split keep/remove subsets.

given modal labels with five-labeler posts at 0, 1, 2, 3, 4, and 5 removes,
and posts with 1, 4, and 6 labelers
when build_unanimous_keep_remove_labels runs
then only five-labeler posts with 0 or 5 removes remain

when build_split_keep_remove_labels runs
then only five-labeler posts with 1, 2, 3, or 4 removes remain

when both builders run
then their post ids are disjoint and their union is every five-labeler post

when write_keep_remove_label_splits runs on that frame
then both CSVs match the two subsets

when labels are omitted
then the writer loads STUDY_2_KEEP_REMOVE_LABELS

when get_dataset looks up the unanimous and split names
then each entry points at the matching CSV under shared/data/transformed/study_2
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd

from shared.data.registry import (
    STUDY_2_KEEP_REMOVE_LABELS,
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
    get_dataset,
)
from shared.data.transformed.study_2.split_keep_remove_labels import (
    build_split_keep_remove_labels,
    build_unanimous_keep_remove_labels,
    write_keep_remove_label_splits,
)
from shared.data.transformed.study_2.transform import OUTPUT_COLUMNS


def _row(post_id: str, n_raters: int | float, n_remove: int | float | None) -> dict[str, object]:
    """One modal label row. Decision is not recomputed."""
    return {
        "post_id": post_id,
        "original_text": f"original {post_id}",
        "mirror_text": f"mirror {post_id}",
        "decision": "keep",
        "keep_remove_label": 0,
        "n_raters": n_raters,
        "keep_rate": 1.0,
        "n_keep": n_raters if n_remove is None else n_raters - n_remove,
        "n_remove": n_remove,
        "is_unanimous": True,
        "sampled_stance": "left",
        "sample_toxicity_type": "insult",
        "platform": post_id.split("_", 1)[0],
    }


def _mixed_labels() -> pd.DataFrame:
    """Five-labeler posts at every remove count, plus other labeler counts."""
    rows = [
        _row("reddit_zero", 5, 0),
        _row("reddit_one", 5, 1),
        _row("bluesky_two", 5, 2),
        _row("twitter_three", 5, 3),
        _row("reddit_four", 5, 4),
        _row("bluesky_five", 5, 5),
        _row("reddit_few", 4, 0),
        _row("twitter_one_rater", 1, 0),
        _row("bluesky_six", 6, 0),
    ]
    return pd.DataFrame(rows)[OUTPUT_COLUMNS]


class TestBuildUnanimousKeepRemoveLabels:
    """Tests for build_unanimous_keep_remove_labels."""

    def test_keeps_zero_and_five_removes_among_five_labelers(self) -> None:
        """Unanimous rows are five-labeler posts with 0 or 5 remove votes."""
        labels = _mixed_labels()
        expected = labels.loc[labels["post_id"].isin(["reddit_zero", "bluesky_five"])].reset_index(drop=True)

        result = build_unanimous_keep_remove_labels(labels)

        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


class TestBuildSplitKeepRemoveLabels:
    """Tests for build_split_keep_remove_labels."""

    def test_keeps_partial_removes_among_five_labelers(self) -> None:
        """Split rows are five-labeler posts with 1, 2, 3, or 4 remove votes."""
        labels = _mixed_labels()
        expected_ids = ["reddit_one", "bluesky_two", "twitter_three", "reddit_four"]
        expected = labels.loc[labels["post_id"].isin(expected_ids)].reset_index(drop=True)

        result = build_split_keep_remove_labels(labels)

        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)

    def test_unanimous_and_split_partition_five_labeler_posts(self) -> None:
        """Every five-labeler post is in exactly one subset."""
        labels = _mixed_labels()
        five_ids = set(labels.loc[labels["n_raters"] == 5, "post_id"])

        unanimous_ids = set(build_unanimous_keep_remove_labels(labels)["post_id"])
        split_ids = set(build_split_keep_remove_labels(labels)["post_id"])

        assert unanimous_ids.isdisjoint(split_ids)
        assert unanimous_ids | split_ids == five_ids


class TestWriteKeepRemoveLabelSplits:
    """Tests for write_keep_remove_label_splits."""

    def test_writes_both_subset_csvs(self, tmp_path: Path) -> None:
        """The caller writes the unanimous CSV and the split CSV."""
        labels = _mixed_labels()
        unanimous_path = tmp_path / "keep_remove_unanimous_labels.csv"
        split_path = tmp_path / "keep_remove_split_labels.csv"

        unanimous, split = write_keep_remove_label_splits(
            labels,
            unanimous_path=unanimous_path,
            split_path=split_path,
        )

        assert list(unanimous["post_id"]) == ["reddit_zero", "bluesky_five"]
        assert list(split["post_id"]) == ["reddit_one", "bluesky_two", "twitter_three", "reddit_four"]
        written_unanimous = pd.read_csv(unanimous_path)
        written_split = pd.read_csv(split_path)
        assert list(written_unanimous["post_id"]) == list(unanimous["post_id"])
        assert list(written_split["post_id"]) == list(split["post_id"])

    def test_loads_registered_modal_labels_when_omitted(self, tmp_path: Path) -> None:
        """Omitting labels loads STUDY_2_KEEP_REMOVE_LABELS once."""
        labels = _mixed_labels()
        load_path = "shared.data.dataloader.load_dataset"

        with patch(load_path, return_value=labels) as load_dataset:
            write_keep_remove_label_splits(
                unanimous_path=tmp_path / "unanimous.csv",
                split_path=tmp_path / "split.csv",
            )

        load_dataset.assert_called_once_with(STUDY_2_KEEP_REMOVE_LABELS, low_memory=False)


class TestGetDataset:
    """Tests for get_dataset on the Study 2 split names."""

    def test_unanimous_labels_are_registered(self) -> None:
        """STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS points at the unanimous CSV."""
        entry = get_dataset(STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS)

        assert entry.name == STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS
        assert entry.relative_path.as_posix() == (
            "shared/data/transformed/study_2/keep_remove_unanimous_labels.csv"
        )
        assert entry.kind == "transformed"
        assert entry.study_phase == "study_2"

    def test_split_labels_are_registered(self) -> None:
        """STUDY_2_KEEP_REMOVE_SPLIT_LABELS points at the split CSV."""
        entry = get_dataset(STUDY_2_KEEP_REMOVE_SPLIT_LABELS)

        assert entry.name == STUDY_2_KEEP_REMOVE_SPLIT_LABELS
        assert entry.relative_path.as_posix() == (
            "shared/data/transformed/study_2/keep_remove_split_labels.csv"
        )
        assert entry.kind == "transformed"
        assert entry.study_phase == "study_2"
