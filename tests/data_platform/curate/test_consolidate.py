from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.curate.consolidate import ConsolidateConfig, build_wide_table
from tests.data_platform.conftest import (
    make_political_feature_rows,
    write_feature_csv,
    write_posts_file,
)
from tests.data_platform.constants import LABEL_TIMESTAMP, URI_POST_A, URI_POST_B


def _feature_run_dir(features_root: Path) -> Path:
    return features_root / LABEL_TIMESTAMP


def test_build_wide_table_joins_features(tmp_path: Path) -> None:
    posts_file = tmp_path / "posts.csv"
    write_posts_file(posts_file)

    features_root = tmp_path / "features"
    write_feature_csv(_feature_run_dir(features_root), "is_political", make_political_feature_rows())
    write_feature_csv(
        _feature_run_dir(features_root),
        "is_likely_spam",
        [
            {"source_record_id": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_likely_spam": False},
            {"source_record_id": URI_POST_B, "label_timestamp": LABEL_TIMESTAMP, "is_likely_spam": True},
        ],
    )
    write_feature_csv(
        _feature_run_dir(features_root),
        "is_news_or_opinion",
        [
            {"source_record_id": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "category": "news"},
            {"source_record_id": URI_POST_B, "label_timestamp": LABEL_TIMESTAMP, "category": "opinion"},
        ],
    )

    wide = build_wide_table(
        ConsolidateConfig(
            posts_file=posts_file,
            features_root=features_root,
            feature_names=("is_political", "is_likely_spam", "is_news_or_opinion"),
        )
    )

    assert len(wide) == 2
    assert "news_or_opinion_category" in wide.columns
    assert "is_likely_spam" in wide.columns
    assert wide.loc[wide["uri"] == URI_POST_A, "news_or_opinion_category"].iloc[0] == "news"
    assert wide.loc[wide["uri"] == URI_POST_A, "is_political"].iloc[0] in {
        True,
        "True",
    }
    assert wide.loc[wide["uri"] == URI_POST_A, "is_likely_spam"].iloc[0] in {
        False,
        "False",
    }


def test_build_wide_table_supports_reddit_id_column_mapping(tmp_path: Path) -> None:
    comments_csv = tmp_path / "comments.csv"
    pd.DataFrame([{"comment_fullname": "t1_a", "body": "comment one"}]).to_csv(
        comments_csv,
        index=False,
    )

    features_root = tmp_path / "features"
    write_feature_csv(
        _feature_run_dir(features_root),
        "is_political",
        [{"source_record_id": "t1_a", "label_timestamp": LABEL_TIMESTAMP, "is_political": True}],
    )

    wide = build_wide_table(
        ConsolidateConfig(
            posts_file=comments_csv,
            features_root=features_root,
            feature_names=("is_political",),
            id_column="comment_fullname",
            feature_file_id_column="source_record_id",
        )
    )

    assert len(wide) == 1
    assert wide.iloc[0]["comment_fullname"] == "t1_a"
    assert wide.iloc[0]["body"] == "comment one"
    assert wide.iloc[0]["is_political"] in {True, "True"}


def test_build_wide_table_picks_latest_label_timestamp_for_duplicate_ids(tmp_path: Path) -> None:
    posts_file = tmp_path / "posts.csv"
    write_posts_file(posts_file)

    features_root = tmp_path / "features"
    write_feature_csv(
        _feature_run_dir(features_root),
        "is_political",
        [
            {
                "source_record_id": URI_POST_A,
                "label_timestamp": "2026_01_01-00:00:00",
                "is_political": False,
            },
            {
                "source_record_id": URI_POST_A,
                "label_timestamp": "2026_02_01-00:00:00",
                "is_political": True,
            },
        ],
    )

    wide = build_wide_table(
        ConsolidateConfig(
            posts_file=posts_file,
            features_root=features_root,
            feature_names=("is_political",),
        )
    )

    assert len(wide) == 2
    assert wide.loc[wide["uri"] == URI_POST_A, "is_political"].iloc[0] in {True, "True"}


def test_build_wide_table_picks_latest_label_across_timestamped_runs(tmp_path: Path) -> None:
    """Given two feature runs, when consolidating, then the latest label_timestamp wins."""
    posts_file = tmp_path / "posts.csv"
    write_posts_file(posts_file)

    features_root = tmp_path / "features"
    write_feature_csv(
        features_root / "2026_01_01-00:00:00",
        "is_political",
        [
            {
                "source_record_id": URI_POST_A,
                "label_timestamp": "2026_01_01-00:00:00",
                "is_political": False,
            }
        ],
    )
    write_feature_csv(
        features_root / "2026_02_01-00:00:00",
        "is_political",
        [
            {
                "source_record_id": URI_POST_A,
                "label_timestamp": "2026_02_01-00:00:00",
                "is_political": True,
            }
        ],
    )

    wide = build_wide_table(
        ConsolidateConfig(
            posts_file=posts_file,
            features_root=features_root,
            feature_names=("is_political",),
        )
    )

    matching = wide.loc[wide["uri"] == URI_POST_A]
    assert len(matching) == 1
    assert matching["is_political"].iloc[0] in {True, "True"}
