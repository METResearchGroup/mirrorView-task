"""Tests for hydrate join helpers."""

from pathlib import Path

import pandas as pd
import pytest

from experiments.create_feature_generation_training_sets_2026_09_04.src.hydrate import (
    hydrate_classifier,
    load_preprocessed_records,
    read_table,
    write_training_parquet,
)


class TestReadTable:
    """Tests for read_table."""

    def test_csv_file_is_read_as_csv(self, tmp_path: Path):
        """Verify a normal csv file is parsed with keep_default_na=False."""
        csv_path = tmp_path / "labels.csv"
        csv_path.write_text("uri,label_timestamp,is_political\nu1,2026_09_04-10:00:00,true\n")

        result = read_table(csv_path)
        expected = pd.DataFrame(
            {
                "uri": ["u1"],
                "label_timestamp": ["2026_09_04-10:00:00"],
                "is_political": ["true"],
            }
        )

        pd.testing.assert_frame_equal(result, expected)

    def test_parquet_bytes_with_csv_suffix_reads_parquet(self, tmp_path: Path):
        """Verify PAR1-prefixed posts.csv is read as parquet without decode errors."""
        parquet_path = tmp_path / "posts.csv"
        source = pd.DataFrame({"uri": ["at://example/post/1"], "text": ["parquet text"]})
        source.to_parquet(parquet_path, index=False)

        result = read_table(parquet_path)
        expected = pd.DataFrame({"uri": ["at://example/post/1"], "text": ["parquet text"]})

        pd.testing.assert_frame_equal(result, expected)


class TestLoadPreprocessedRecords:
    """Tests for load_preprocessed_records."""

    def test_bluesky_csv_records_load_join_id_and_text(self, bluesky_dataset_dir: Path):
        """Verify Bluesky preprocessed csv exposes uri and text."""
        result = load_preprocessed_records(bluesky_dataset_dir, "bluesky")

        assert len(result) == 1
        assert result.iloc[0]["uri"] == "at://did:plc:abc/app.bsky.feed.post/1"
        assert result.iloc[0]["text"] == "hello bluesky"

    def test_two_runs_with_shared_uri_keep_first(self, tmp_path: Path):
        """Verify duplicate join ids across runs keep the first row only."""
        dataset_dir = tmp_path / "bluesky_dup"
        run_a = dataset_dir / "preprocessed" / "2026_09_04-09:00:00"
        run_b = dataset_dir / "preprocessed" / "2026_09_04-10:00:00"
        run_a.mkdir(parents=True)
        run_b.mkdir(parents=True)
        shared_uri = "at://did:plc:abc/app.bsky.feed.post/1"
        pd.DataFrame({"uri": [shared_uri], "text": ["first run text"]}).to_csv(
            run_a / "posts.csv", index=False
        )
        pd.DataFrame({"uri": [shared_uri], "text": ["second run text"]}).to_csv(
            run_b / "posts.csv", index=False
        )

        result = load_preprocessed_records(dataset_dir, "bluesky")

        assert len(result) == 1
        assert result.iloc[0]["text"] == "first run text"

    def test_reddit_body_copied_to_text(self, reddit_dataset_dir: Path):
        """Verify Reddit records expose text from body."""
        result = load_preprocessed_records(reddit_dataset_dir, "reddit")

        assert len(result) == 1
        assert result.iloc[0]["comment_fullname"] == "t1_abc123"
        assert result.iloc[0]["text"] == "hello reddit"


class TestHydrateClassifier:
    """Tests for hydrate_classifier."""

    def test_bluesky_is_political_joins_text(self, bluesky_dataset_dir: Path):
        """Verify Bluesky labels join to preprocessed text with expected columns."""
        labels = pd.DataFrame(
            {
                "uri": ["at://did:plc:abc/app.bsky.feed.post/1"],
                "label_timestamp": ["2026_09_04-11:00:00"],
                "is_political": [True],
            }
        )
        records = load_preprocessed_records(bluesky_dataset_dir, "bluesky")

        result = hydrate_classifier(
            labels,
            records,
            platform="bluesky",
            classifier_name="is_political",
        )

        assert list(result.columns) == ["uri", "label_timestamp", "text", "is_political"]
        assert len(result) == 1
        assert result.iloc[0]["text"] == "hello bluesky"
        assert result.iloc[0]["is_political"] is True

    def test_duplicate_uri_keeps_later_label_timestamp(self, bluesky_dataset_dir: Path):
        """Verify duplicate uri rows keep the latest label_timestamp."""
        labels = pd.DataFrame(
            {
                "uri": [
                    "at://did:plc:abc/app.bsky.feed.post/1",
                    "at://did:plc:abc/app.bsky.feed.post/1",
                ],
                "label_timestamp": ["2026_09_04-09:00:00", "2026_09_04-12:00:00"],
                "is_political": [False, True],
            }
        )
        records = load_preprocessed_records(bluesky_dataset_dir, "bluesky")

        result = hydrate_classifier(
            labels,
            records,
            platform="bluesky",
            classifier_name="is_political",
        )

        assert len(result) == 1
        assert result.iloc[0]["label_timestamp"] == "2026_09_04-12:00:00"
        assert result.iloc[0]["is_political"] is True

    def test_unmatched_label_uri_is_dropped(self, bluesky_dataset_dir: Path):
        """Verify label rows without preprocessed text are removed."""
        labels = pd.DataFrame(
            {
                "uri": ["at://did:plc:missing/post/99"],
                "label_timestamp": ["2026_09_04-11:00:00"],
                "is_political": [True],
            }
        )
        records = load_preprocessed_records(bluesky_dataset_dir, "bluesky")

        result = hydrate_classifier(
            labels,
            records,
            platform="bluesky",
            classifier_name="is_political",
        )

        assert len(result) == 0

    def test_twitter_joins_int_tweet_id_to_string_uri(self, twitter_dataset_dir: Path):
        """Verify Twitter joins string uri labels to integer tweet_id records."""
        labels = pd.DataFrame(
            {
                "uri": ["123456789"],
                "label_timestamp": ["2026_09_04-11:00:00"],
                "is_political": [False],
            }
        )
        records = load_preprocessed_records(twitter_dataset_dir, "twitter")

        result = hydrate_classifier(
            labels,
            records,
            platform="twitter",
            classifier_name="is_political",
        )

        assert len(result) == 1
        assert result.iloc[0]["uri"] == "123456789"
        assert result.iloc[0]["text"] == "hello twitter"

    def test_reddit_output_uri_and_text_from_records(self, reddit_dataset_dir: Path):
        """Verify Reddit output uri matches classifier and text equals body."""
        labels = pd.DataFrame(
            {
                "uri": ["t1_abc123"],
                "label_timestamp": ["2026_09_04-11:00:00"],
                "is_political": [True],
            }
        )
        records = load_preprocessed_records(reddit_dataset_dir, "reddit")

        result = hydrate_classifier(
            labels,
            records,
            platform="reddit",
            classifier_name="is_political",
        )

        assert len(result) == 1
        assert result.iloc[0]["uri"] == "t1_abc123"
        assert result.iloc[0]["text"] == "hello reddit"

    def test_is_news_or_opinion_keeps_category_column(self, bluesky_dataset_dir: Path):
        """Verify is_news_or_opinion retains category without renaming."""
        labels = pd.DataFrame(
            {
                "uri": ["at://did:plc:abc/app.bsky.feed.post/1"],
                "label_timestamp": ["2026_09_04-11:00:00"],
                "category": ["news"],
            }
        )
        records = load_preprocessed_records(bluesky_dataset_dir, "bluesky")

        result = hydrate_classifier(
            labels,
            records,
            platform="bluesky",
            classifier_name="is_news_or_opinion",
        )

        assert "category" in result.columns
        assert "news_or_opinion_category" not in result.columns
        assert result.iloc[0]["category"] == "news"

    def test_is_toxic_tiered_keeps_both_label_columns(self, bluesky_dataset_dir: Path):
        """Verify is_toxic_tiered retains toxicity_prob and toxicity_tier."""
        labels = pd.DataFrame(
            {
                "uri": ["at://did:plc:abc/app.bsky.feed.post/1"],
                "label_timestamp": ["2026_09_04-11:00:00"],
                "toxicity_prob": [0.42],
                "toxicity_tier": ["medium"],
            }
        )
        records = load_preprocessed_records(bluesky_dataset_dir, "bluesky")

        result = hydrate_classifier(
            labels,
            records,
            platform="bluesky",
            classifier_name="is_toxic_tiered",
        )

        assert list(result.columns) == [
            "uri",
            "label_timestamp",
            "text",
            "toxicity_prob",
            "toxicity_tier",
        ]
        assert result.iloc[0]["toxicity_prob"] == 0.42
        assert result.iloc[0]["toxicity_tier"] == "medium"

    def test_missing_label_column_raises_value_error(self, bluesky_dataset_dir: Path):
        """Verify missing required label columns raise ValueError naming the column."""
        labels = pd.DataFrame(
            {
                "uri": ["at://did:plc:abc/app.bsky.feed.post/1"],
                "label_timestamp": ["2026_09_04-11:00:00"],
            }
        )
        records = load_preprocessed_records(bluesky_dataset_dir, "bluesky")

        with pytest.raises(ValueError, match="is_political"):
            hydrate_classifier(
                labels,
                records,
                platform="bluesky",
                classifier_name="is_political",
            )

    def test_empty_labels_returns_zero_rows_with_output_columns(self):
        """Verify empty labels return an empty frame with the output schema."""
        labels = pd.DataFrame()
        records = pd.DataFrame({"uri": ["u1"], "text": ["text"]})

        result = hydrate_classifier(
            labels,
            records,
            platform="bluesky",
            classifier_name="is_political",
        )

        expected_columns = ["uri", "label_timestamp", "text", "is_political"]
        assert list(result.columns) == expected_columns
        assert len(result) == 0


class TestWriteTrainingParquet:
    """Tests for write_training_parquet."""

    def test_writes_readable_parquet_with_unique_uri(self, tmp_path: Path):
        """Verify parquet is written, readable, and uri values are unique."""
        frame = pd.DataFrame(
            {
                "uri": ["at://example/post/1"],
                "label_timestamp": ["2026_09_04-11:00:00"],
                "text": ["sample text"],
                "is_political": [True],
            }
        )
        output_path = tmp_path / "nested" / "training.parquet"

        written_path = write_training_parquet(frame, output_path)
        result = pd.read_parquet(written_path)

        assert written_path == output_path
        assert output_path.exists()
        assert len(result) == 1
        assert result["uri"].is_unique
