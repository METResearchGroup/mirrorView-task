"""Tests for build_training_sets walk behavior."""

from pathlib import Path

import pandas as pd
import pytest

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    CLASSIFIER_NAMES,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.walk import (
    build_training_sets,
)

RUN_TIMESTAMP = "2026_09_04-12:00:00"
SHARED_URI = "at://did:plc:abc/app.bsky.feed.post/1"


def _write_bluesky_preprocessed(dataset_dir: Path) -> None:
    run_dir = dataset_dir / "preprocessed" / "run1"
    run_dir.mkdir(parents=True)
    posts = pd.DataFrame(
        {
            "uri": [SHARED_URI],
            "text": ["hello bluesky"],
        }
    )
    posts.to_csv(run_dir / "posts.csv", index=False)


def _write_is_political_labels(features_dir: Path) -> None:
    features_dir.mkdir(parents=True)
    labels = pd.DataFrame(
        {
            "uri": [SHARED_URI],
            "label_timestamp": ["2026_09_04-11:00:00"],
            "is_political": [True],
        }
    )
    labels.to_csv(features_dir / "is_political.csv", index=False)


def _write_is_toxic_tiered_labels(features_dir: Path) -> None:
    features_dir.mkdir(parents=True)
    labels = pd.DataFrame(
        {
            "uri": ["t1_abc123"],
            "label_timestamp": ["2026_09_04-11:00:00"],
            "toxicity_prob": [0.42],
            "toxicity_tier": ["medium"],
        }
    )
    labels.to_csv(features_dir / "is_toxic_tiered.csv", index=False)


class TestBuildTrainingSets:
    """Tests for build_training_sets."""

    def test_writes_parquet_for_existing_classifier_only(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Verify one existing classifier writes parquet and skips missing classifiers."""
        data_root = tmp_path / "data"
        output_root = tmp_path / "training_data"
        dataset_dir = data_root / "bluesky" / "ds1"
        _write_bluesky_preprocessed(dataset_dir)
        features_dir = dataset_dir / "features"
        _write_is_political_labels(features_dir)
        (features_dir / "metadata.json").write_text("{}")

        result = build_training_sets(
            data_root,
            timestamp=RUN_TIMESTAMP,
            output_root=output_root,
        )

        expected_path = output_root / "is_political" / f"ds1_{RUN_TIMESTAMP}.parquet"
        assert result == [expected_path]
        assert expected_path.exists()
        assert not (output_root / "is_likely_spam").exists()

        captured = capsys.readouterr().out
        assert str(expected_path) in captured
        assert "wrote 1 parquets" in captured

    def test_reddit_classifier_only_prints_skip_for_missing_classifiers(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        """Verify missing classifiers print skip lines and one parquet is written."""
        data_root = tmp_path / "data"
        output_root = tmp_path / "training_data"
        dataset_dir = data_root / "reddit" / "ds2"
        _write_is_toxic_tiered_labels(dataset_dir / "features")

        result = build_training_sets(
            data_root,
            timestamp=RUN_TIMESTAMP,
            output_root=output_root,
        )

        expected_path = (
            output_root / "is_toxic_tiered" / f"ds2_{RUN_TIMESTAMP}.parquet"
        )
        assert result == [expected_path]
        assert expected_path.exists()

        captured = capsys.readouterr().out
        other_classifiers = [
            name for name in CLASSIFIER_NAMES if name != "is_toxic_tiered"
        ]
        for classifier_name in other_classifiers:
            assert "ds2" in captured
            assert classifier_name in captured
        assert "wrote 1 parquets" in captured

    def test_two_platforms_share_timestamp_suffix(self, tmp_path: Path):
        """Verify two platform datasets write parquets with the same timestamp."""
        data_root = tmp_path / "data"
        output_root = tmp_path / "training_data"

        bluesky_dir = data_root / "bluesky" / "ds_bluesky"
        _write_bluesky_preprocessed(bluesky_dir)
        _write_is_political_labels(bluesky_dir / "features")

        twitter_dir = data_root / "twitter" / "ds_twitter"
        twitter_run = twitter_dir / "preprocessed" / "run1"
        twitter_run.mkdir(parents=True)
        pd.DataFrame(
            {
                "tweet_id": [123456789],
                "text": ["hello twitter"],
            }
        ).to_csv(twitter_run / "posts.csv", index=False)
        twitter_features = twitter_dir / "features"
        twitter_features.mkdir(parents=True)
        pd.DataFrame(
            {
                "uri": ["123456789"],
                "label_timestamp": ["2026_09_04-11:00:00"],
                "is_political": [False],
            }
        ).to_csv(twitter_features / "is_political.csv", index=False)

        result = build_training_sets(
            data_root,
            timestamp=RUN_TIMESTAMP,
            output_root=output_root,
        )

        expected = [
            output_root / "is_political" / f"ds_bluesky_{RUN_TIMESTAMP}.parquet",
            output_root / "is_political" / f"ds_twitter_{RUN_TIMESTAMP}.parquet",
        ]
        assert result == expected
        for path in expected:
            assert path.name.endswith(f"_{RUN_TIMESTAMP}.parquet")
