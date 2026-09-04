from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from data_platform.preprocessing import preprocess_twitter
from data_platform.preprocessing.runner import collapse_candidates_by_id
from data_platform.preprocessing.validators import twitter_validators
from data_platform.utils.deduplication import DedupeConfig, DedupeSession
from data_platform.utils.storage import StorageStage, TwitterStorageManager
from tests.data_platform.constants import VALID_TWITTER_DATASET_ID
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row
from tests.data_platform.preprocessing.conftest import (
    EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT,
    LONG_ENGLISH_TEXT,
)


def _valid_text() -> str:
    return "This is a valid English tweet for preprocessing tests without external URLs."


def _tweet_row(**overrides: Any) -> dict[str, Any]:
    tweet_id = overrides.pop("tweet_id", "1000000000000000001")
    row = mock_tweet_row(tweet_id)
    row["text"] = _valid_text()
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Short", False),
        ("x" * 49, False),
        ("x" * 50, True),
        ("x" * 280, True),
        ("x" * 281, False),
    ],
)
def test_check_if_valid_twitter_post_length(text: str, expected: bool) -> None:
    assert twitter_validators.check_if_valid_twitter_post_length(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello world " + "x" * 40, True),
        (
            "Check this link https://t.co/abc123 " + "x" * 20,
            True,
        ),
        (
            "Visit https://example.com for details " + "x" * 10,
            False,
        ),
        (
            "Shared link https://t.co/xyz in this tweet body " + "x" * 15,
            True,
        ),
    ],
)
def test_check_if_twitter_text_has_no_external_urls(text: str, expected: bool) -> None:
    assert twitter_validators.check_if_twitter_text_has_no_external_urls(text) is expected


def test_strip_tco_links_removes_tco_urls() -> None:
    text = "Before https://t.co/abc after http://t.co/xyz end"
    assert twitter_validators.strip_tco_links(text) == "Before  after  end"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello https://t.co/abc", True),
        ("Hello https://example.com", False),
        ("no links " + "x" * 40, False),
    ],
)
def test_has_tco_links(text: str, expected: bool) -> None:
    assert twitter_validators.has_tco_links(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (_valid_text(), True),
        ("Bonjour tout le monde, ceci est un tweet en français assez long.", False),
    ],
)
def test_twitter_text_validators(text: str, expected: bool) -> None:
    assert preprocess_twitter.passes_all_validators(text) is expected


def test_preprocess_records_writes_output(data_root) -> None:
    dataset_id = VALID_TWITTER_DATASET_ID
    raw_storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
    run_dir = raw_storage.create_new_run_dir("2026_05_31-10:00:00")
    raw_storage.write_records(
        [
            _tweet_row(tweet_id="1000000000000000001"),
            _tweet_row(tweet_id="1000000000000000002", text="x" * 10),
        ],
        run_dir,
    )
    raw_storage.write_run_metadata(
        run_dir,
        {
            "sync_status": "completed",
            "row_count": 2,
        },
    )

    output_dir = preprocess_twitter.preprocess_records(dataset_id)

    preprocessed_storage = TwitterStorageManager(StorageStage.PREPROCESSED, dataset_id)
    output = preprocessed_storage.load_records(output_dir)
    metadata = preprocessed_storage.load_run_metadata(output_dir)

    assert len(output) == 1
    assert output.iloc[0]["tweet_id"] == "1000000000000000001"
    assert output.iloc[0]["author_handle"] == output.iloc[0]["username"]
    assert output.iloc[0]["source_record_id"] == output.iloc[0]["tweet_id"]
    assert output.iloc[0]["author_id"] == _tweet_row()["author_id"]
    assert metadata["row_counts"]["input"] == 2
    assert metadata["row_counts"]["output"] == 1
    assert metadata["files"]["posts"] == "posts.csv"


def test_preprocess_records_strips_tco_from_saved_text(data_root) -> None:
    dataset_id = VALID_TWITTER_DATASET_ID
    raw_storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
    run_dir = raw_storage.create_new_run_dir("2026_05_31-11:00:00")
    text_with_tco = _valid_text() + " https://t.co/abc123"
    row = _tweet_row(tweet_id="1000000000000000001", text=text_with_tco)
    raw_storage.write_records([row], run_dir)
    raw_storage.write_run_metadata(
        run_dir,
        {
            "sync_status": "completed",
            "row_count": 1,
        },
    )

    output_dir = preprocess_twitter.preprocess_records(dataset_id)

    preprocessed_storage = TwitterStorageManager(StorageStage.PREPROCESSED, dataset_id)
    output = preprocessed_storage.load_records(output_dir)

    assert len(output) == 1
    assert not twitter_validators.has_tco_links(output.iloc[0]["text"])
    assert "https://t.co/" not in output.iloc[0]["text"]
    assert output.iloc[0]["tweet_id"] == row["tweet_id"]
    assert output.iloc[0]["url"] == row["url"]


def test_preprocess_records_truncates_long_text_after_stripping_tco(
    data_root,
) -> None:
    """Long tweets are saved without t.co URLs and with truncated standardized text."""
    dataset_id = VALID_TWITTER_DATASET_ID
    raw_storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
    run_dir = raw_storage.create_new_run_dir("2026_05_31-15:00:00")
    raw_storage.write_records(
        [
            _tweet_row(
                tweet_id="1000000000000000001",
                text=LONG_ENGLISH_TEXT + " https://t.co/abc123",
            )
        ],
        run_dir,
    )
    raw_storage.write_run_metadata(
        run_dir,
        {
            "sync_status": "completed",
            "row_count": 1,
        },
    )
    expected = EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT

    output_dir = preprocess_twitter.preprocess_records(dataset_id)
    output = TwitterStorageManager(StorageStage.PREPROCESSED, dataset_id).load_records(
        output_dir
    )

    assert len(output) == 1
    assert output.iloc[0]["text"] == expected
    assert "https://t.co/" not in output.iloc[0]["text"]


def test_preprocess_records_merges_all_raw_runs_and_sets_source_raw_runs(data_root) -> None:
    dataset_id = VALID_TWITTER_DATASET_ID
    raw_storage = TwitterStorageManager(StorageStage.RAW, dataset_id)

    older_run = raw_storage.create_new_run_dir("2026_05_31-11:00:00")
    newer_run = raw_storage.create_new_run_dir("2026_05_31-12:00:00")

    shared_tweet_id = "1000000000000000001"
    older_text = _valid_text() + " (older run)"
    newer_text = _valid_text() + " (newer run)"

    raw_storage.write_records(
        [_tweet_row(tweet_id=shared_tweet_id, text=older_text)],
        older_run,
    )
    raw_storage.write_run_metadata(
        older_run,
        {
            "sync_status": "completed",
            "row_count": 1,
        },
    )

    raw_storage.write_records(
        [_tweet_row(tweet_id=shared_tweet_id, text=newer_text)],
        newer_run,
    )
    raw_storage.write_run_metadata(
        newer_run,
        {
            "sync_status": "completed",
            "row_count": 1,
        },
    )

    output_dir = preprocess_twitter.preprocess_records(dataset_id)
    preprocessed_storage = TwitterStorageManager(StorageStage.PREPROCESSED, dataset_id)
    output_df = preprocessed_storage.load_records(output_dir)
    metadata = preprocessed_storage.load_run_metadata(output_dir)

    assert len(output_df) == 1
    assert output_df.iloc[0]["tweet_id"] == shared_tweet_id
    # Newest wins: we keep the row from the newer run after deduping.
    assert output_df.iloc[0]["text"] == newer_text

    assert "source_raw_runs" in metadata
    assert len(metadata["source_raw_runs"]) == 2
    assert metadata["source_raw_runs"][-1] == metadata["source_raw_run"]


def test_second_preprocess_run_skips_already_preprocessed_ids(data_root) -> None:
    dataset_id = VALID_TWITTER_DATASET_ID
    raw_storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
    run_dir = raw_storage.create_new_run_dir("2026_05_31-13:00:00")
    tweet_id = "1000000000000000001"
    raw_storage.write_records([_tweet_row(tweet_id=tweet_id)], run_dir)
    raw_storage.write_run_metadata(
        run_dir,
        {
            "sync_status": "completed",
            "row_count": 1,
        },
    )

    first_output = preprocess_twitter.preprocess_records(dataset_id)
    preprocessed_storage = TwitterStorageManager(StorageStage.PREPROCESSED, dataset_id)
    assert len(preprocessed_storage.load_records(first_output)) == 1

    second_output = preprocess_twitter.preprocess_records(dataset_id)
    second_metadata = preprocessed_storage.load_run_metadata(second_output)
    assert second_metadata["row_counts"]["input"] == 0
    assert second_metadata["row_counts"]["output"] == 0
    assert len(preprocessed_storage.load_records(second_output)) == 0


def test_collapse_candidates_by_id_keeps_last_row() -> None:
    """Verifies last-wins collapse keeps one row per id."""
    records = pd.DataFrame(
        [
            {"tweet_id": "a", "text": "first"},
            {"tweet_id": "a", "text": "second"},
        ]
    )
    expected_text = "second"

    result = collapse_candidates_by_id(records, "tweet_id", keep="last")

    assert len(result) == 1
    assert result.iloc[0]["text"] == expected_text


def test_prior_run_skip_count_excludes_collapse_duplicates() -> None:
    """Verifies pandas drop counts prior-run ids only, then collapse keeps one new id."""
    records = pd.DataFrame(
        [
            {"tweet_id": "a", "text": "seen"},
            {"tweet_id": "b", "text": "first-new"},
            {"tweet_id": "b", "text": "last-new"},
        ]
    )
    session = DedupeSession(DedupeConfig(id_column="tweet_id"))
    session.seen_ids = {"a"}  # public skip-set seed for this helper-path test
    id_col = "tweet_id"
    is_new = ~records[id_col].isin(list(session.seen_ids))
    skipped = len(records) - int(is_new.sum())
    surviving = collapse_candidates_by_id(
        records.loc[is_new].reset_index(drop=True), id_col, keep="last"
    )
    expected_skipped = 1
    expected_ids = ["b"]
    expected_text = "last-new"

    assert skipped == expected_skipped
    assert surviving["tweet_id"].tolist() == expected_ids
    assert surviving.iloc[0]["text"] == expected_text


def test_second_preprocess_run_print_names_prior_preprocessed_run(
    data_root, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verifies the skip print names prior preprocessed runs and counts one known id."""
    dataset_id = VALID_TWITTER_DATASET_ID
    raw_storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
    run_dir = raw_storage.create_new_run_dir("2026_05_31-13:00:00")
    tweet_id = "1000000000000000001"
    raw_storage.write_records([_tweet_row(tweet_id=tweet_id)], run_dir)
    raw_storage.write_run_metadata(
        run_dir,
        {
            "sync_status": "completed",
            "row_count": 1,
        },
    )
    preprocess_twitter.preprocess_records(dataset_id)
    capsys.readouterr()

    preprocess_twitter.preprocess_records(dataset_id)
    printed = capsys.readouterr().out

    assert "already in a prior preprocessed run" in printed
    assert "skipped 1 already in a prior preprocessed run" in printed


def test_preprocess_drops_previously_used_stimuli(
    data_root, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A raw row whose record_id is a prior study stimulus is not written."""
    dataset_id = VALID_TWITTER_DATASET_ID
    tweet_id = "1000000000000000001"
    stimuli_ids = {f"twitter_{tweet_id}"}
    monkeypatch.setattr(
        "data_platform.preprocessing.runner.load_previously_used_stimuli_ids",
        lambda datasets: stimuli_ids,
    )
    raw_storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
    run_dir = raw_storage.create_new_run_dir("2026_05_31-14:00:00")
    raw_storage.write_records([_tweet_row(tweet_id=tweet_id)], run_dir)
    raw_storage.write_run_metadata(
        run_dir,
        {
            "sync_status": "completed",
            "row_count": 1,
        },
    )

    output_dir = preprocess_twitter.preprocess_records(dataset_id)

    preprocessed_storage = TwitterStorageManager(StorageStage.PREPROCESSED, dataset_id)
    output = preprocessed_storage.load_records(output_dir)
    metadata = preprocessed_storage.load_run_metadata(output_dir)
    printed = capsys.readouterr().out
    expected_rows = 0

    assert len(output) == expected_rows
    assert metadata["row_counts"]["input"] == expected_rows
    assert metadata["row_counts"]["output"] == expected_rows
    assert "skipped 1 already used as stimuli" in printed
