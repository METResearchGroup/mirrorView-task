from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_platform.preprocessing.previously_used_stimuli import (
    STIMULI_DATASET_KIND,
    STIMULI_ID_COLUMN,
    extract_stimuli_ids,
    filter_previously_used_stimuli,
    load_previously_used_stimuli_ids,
)
from data_platform.preprocessing.preprocess_twitter import TWITTER_SPEC
from data_platform.preprocessing.runner import filter_duplicate_records
from shared.data.registry import DatasetEntry, DatasetKind
from tests.data_platform.constants import VALID_TWITTER_DATASET_ID
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


def _stimuli_frame(*keys: object) -> pd.DataFrame:
    return pd.DataFrame({STIMULI_ID_COLUMN: list(keys)})


def _records_frame(*record_ids: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "record_id": list(record_ids),
            "text": [f"text-{index}" for index in range(len(record_ids))],
        }
    )


def _dataset_entry(name: str, kind: DatasetKind) -> DatasetEntry:
    return DatasetEntry(
        name=name,
        relative_path=Path(f"{name}.csv"),
        kind=kind,
        study_phase="test",
    )


class TestExtractStimuliIds:
    """Tests for extract_stimuli_ids()."""

    def test_returns_post_primary_keys(self) -> None:
        """The function returns distinct stimuli keys from the catalog column."""
        frame = _stimuli_frame("twitter_1", "bluesky_2")
        expected = {"twitter_1", "bluesky_2"}

        result = extract_stimuli_ids(frame, "TEST_STIMULI")

        assert result == expected

    def test_omits_blank_and_duplicate_keys(self) -> None:
        """Blank, whitespace, and missing cells are dropped, and duplicate keys appear only once."""
        frame = _stimuli_frame("twitter_1", "twitter_1", "", "   ", None)
        expected = {"twitter_1"}

        result = extract_stimuli_ids(frame, "TEST_STIMULI")

        assert result == expected

    def test_raises_when_id_column_missing(self) -> None:
        """A stimuli table without post_primary_key is invalid."""
        frame = pd.DataFrame({"other": ["twitter_1"]})

        with pytest.raises(ValueError, match=STIMULI_ID_COLUMN):
            extract_stimuli_ids(frame, "TEST_STIMULI")

    def test_adds_reddit_comment_fullname_ingest_form(self) -> None:
        """Part 2 Reddit catalog keys also skip the ingest comment_fullname form."""
        frame = _stimuli_frame("reddit_1tnobm9_onxadx3")
        expected = {"reddit_1tnobm9_onxadx3", "reddit_t1_onxadx3"}

        result = extract_stimuli_ids(frame, "TEST_STIMULI")

        assert result == expected

    def test_does_not_alias_hashed_reddit_keys(self) -> None:
        """Older hashed Reddit catalog keys stay as written."""
        frame = _stimuli_frame("reddit_881fdcb47017d064")
        expected = {"reddit_881fdcb47017d064"}

        result = extract_stimuli_ids(frame, "TEST_STIMULI")

        assert result == expected


class TestLoadPreviouslyUsedStimuliIds:
    """Tests for load_previously_used_stimuli_ids()."""

    def test_unions_ids_from_stimuli_datasets_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Results tables are ignored, and stimuli tables are combined into one set."""
        datasets = {
            "KEEP_STIMULI": _dataset_entry("KEEP_STIMULI", STIMULI_DATASET_KIND),
            "OTHER_STIMULI": _dataset_entry("OTHER_STIMULI", STIMULI_DATASET_KIND),
            "RESULTS": _dataset_entry("RESULTS", "results"),
        }
        frames = {
            "KEEP_STIMULI": _stimuli_frame("twitter_1"),
            "OTHER_STIMULI": _stimuli_frame("twitter_2", "twitter_1"),
            "RESULTS": _stimuli_frame("twitter_3"),
        }

        def fake_load_dataset(name: str, *, low_memory: bool = False) -> pd.DataFrame:
            return frames[name]

        monkeypatch.setattr(
            "data_platform.preprocessing.previously_used_stimuli.load_dataset",
            fake_load_dataset,
        )
        expected = {"twitter_1", "twitter_2"}

        result = load_previously_used_stimuli_ids(datasets)

        assert result == expected

    def test_raises_when_stimuli_file_is_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A registered stimuli CSV that is not on disk raises FileNotFoundError."""
        datasets = {
            "MISSING_STIMULI": _dataset_entry("MISSING_STIMULI", STIMULI_DATASET_KIND),
        }

        def fake_load_dataset(name: str, *, low_memory: bool = False) -> pd.DataFrame:
            raise FileNotFoundError(name)

        monkeypatch.setattr(
            "data_platform.preprocessing.previously_used_stimuli.load_dataset",
            fake_load_dataset,
        )

        with pytest.raises(FileNotFoundError):
            load_previously_used_stimuli_ids(datasets)


class TestFilterPreviouslyUsedStimuli:
    """Tests for filter_previously_used_stimuli()."""

    def test_drops_rows_whose_record_id_was_used_as_stimuli(self) -> None:
        """Matching record_id values are removed, and the other rows stay."""
        records = _records_frame("twitter_1", "twitter_2")
        stimuli_ids = {"twitter_1"}
        expected_ids = ["twitter_2"]
        expected_skipped = 1

        result, skipped = filter_previously_used_stimuli(records, stimuli_ids)

        assert result["record_id"].tolist() == expected_ids
        assert skipped == expected_skipped

    def test_drops_reddit_ingest_id_for_catalog_post_comment_key(self) -> None:
        """A Reddit ingest record_id is dropped when the catalog uses post and comment ids."""
        records = _records_frame("reddit_t1_onxadx3")
        stimuli_ids = extract_stimuli_ids(
            _stimuli_frame("reddit_1tnobm9_onxadx3"),
            "TEST_STIMULI",
        )
        expected_skipped = 1

        result, skipped = filter_previously_used_stimuli(records, stimuli_ids)

        assert result.empty
        assert skipped == expected_skipped

    def test_keeps_all_rows_when_no_stimuli_match(self) -> None:
        """Rows stay when their record_id is not in the stimuli set."""
        records = _records_frame("twitter_1")
        stimuli_ids = {"twitter_other"}
        expected_skipped = 0

        result, skipped = filter_previously_used_stimuli(records, stimuli_ids)

        assert result["record_id"].tolist() == ["twitter_1"]
        assert skipped == expected_skipped

    def test_empty_frame_returns_copy_and_zero_skipped(self) -> None:
        """An empty candidate table returns an empty copy and a skipped count of 0."""
        records = pd.DataFrame(columns=["record_id"])
        expected_skipped = 0

        result, skipped = filter_previously_used_stimuli(records, {"twitter_1"})

        assert result.empty
        assert skipped == expected_skipped

    def test_does_not_mutate_input_frame(self) -> None:
        """Filtering returns a new frame."""
        records = _records_frame("twitter_1", "twitter_2")
        original_ids = records["record_id"].tolist()

        filter_previously_used_stimuli(records, {"twitter_1"})

        assert records["record_id"].tolist() == original_ids

    def test_raises_when_record_id_column_missing(self) -> None:
        """Candidates without record_id cannot be matched to stimuli."""
        records = pd.DataFrame({"text": ["hello"]})

        with pytest.raises(KeyError, match="record_id"):
            filter_previously_used_stimuli(records, {"twitter_1"})


class TestFilterDuplicateRecords:
    """Tests that filter_duplicate_records() drops previously used stimuli before it collapses duplicate ids."""

    def test_drops_previously_used_stimuli_before_collapse(
        self, data_root: Path
    ) -> None:
        """A record_id that is in the stimuli set is removed even when it is not in a prior preprocessed run."""
        used_id = "1000000000000000001"
        kept_id = "1000000000000000002"
        records = pd.DataFrame(
            [
                mock_tweet_row(used_id),
                mock_tweet_row(kept_id),
            ]
        )
        stimuli_ids = {f"twitter_{used_id}"}
        expected_ids = [kept_id]
        expected_preprocessed_skipped = 0
        expected_stimuli_skipped = 1

        result = filter_duplicate_records(
            records,
            TWITTER_SPEC,
            VALID_TWITTER_DATASET_ID,
            stimuli_ids,
        )

        assert result.records["tweet_id"].tolist() == expected_ids
        assert result.skipped_already_preprocessed == expected_preprocessed_skipped
        assert result.skipped_previously_used_stimuli == expected_stimuli_skipped
