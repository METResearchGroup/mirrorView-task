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
from shared.data.registry import DatasetEntry
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


def _dataset_entry(name: str, kind: str) -> DatasetEntry:
    return DatasetEntry(
        name=name,
        relative_path=Path(f"{name}.csv"),
        kind=kind,  # type: ignore[arg-type]
        study_phase="test",
    )


class TestExtractStimuliIds:
    """Tests for extract_stimuli_ids()."""

    def test_returns_post_primary_keys(self) -> None:
        """Collects distinct stimuli keys from the catalog column."""
        frame = _stimuli_frame("twitter_1", "bluesky_2")
        expected = {"twitter_1", "bluesky_2"}

        result = extract_stimuli_ids(frame, "TEST_STIMULI")

        assert result == expected

    def test_omits_blank_and_duplicate_keys(self) -> None:
        """Blank, whitespace, and missing cells are dropped; duplicates collapse."""
        frame = _stimuli_frame("twitter_1", "twitter_1", "", "   ", None)
        expected = {"twitter_1"}

        result = extract_stimuli_ids(frame, "TEST_STIMULI")

        assert result == expected

    def test_raises_when_id_column_missing(self) -> None:
        """A stimuli table without post_primary_key is invalid."""
        frame = pd.DataFrame({"other": ["twitter_1"]})

        with pytest.raises(ValueError, match=STIMULI_ID_COLUMN):
            extract_stimuli_ids(frame, "TEST_STIMULI")


class TestLoadPreviouslyUsedStimuliIds:
    """Tests for load_previously_used_stimuli_ids()."""

    def test_unions_ids_from_stimuli_datasets_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Results tables are ignored; stimuli tables are unioned."""
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
        """A registered stimuli CSV that is not on disk fails fast."""
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
        """Matching record_id values are removed; other rows stay."""
        records = _records_frame("twitter_1", "twitter_2")
        stimuli_ids = {"twitter_1"}
        expected_ids = ["twitter_2"]
        expected_skipped = 1

        result, skipped = filter_previously_used_stimuli(records, stimuli_ids)

        assert result["record_id"].tolist() == expected_ids
        assert skipped == expected_skipped

    def test_keeps_all_rows_when_no_stimuli_match(self) -> None:
        """Unrelated stimuli ids do not drop candidates."""
        records = _records_frame("twitter_1")
        stimuli_ids = {"twitter_other"}
        expected_skipped = 0

        result, skipped = filter_previously_used_stimuli(records, stimuli_ids)

        assert result["record_id"].tolist() == ["twitter_1"]
        assert skipped == expected_skipped

    def test_empty_frame_returns_copy_and_zero_skipped(self) -> None:
        """An empty candidate table is a no-op."""
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
    """Tests for filter_duplicate_records() README 4c behavior."""

    def test_drops_previously_used_stimuli_before_collapse(
        self, data_root: Path
    ) -> None:
        """A stimuli record_id is removed even when it is new to preprocess."""
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
