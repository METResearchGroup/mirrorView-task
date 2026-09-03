"""Phase 3 contract tests for ``data_platform.preprocessing.runner`` helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd
import pytest

import data_platform.preprocessing.runner as runner
from data_platform.preprocessing.preprocess_twitter import TWITTER_SPEC
from data_platform.preprocessing.validators import twitter_validators
from data_platform.utils.storage import StorageStage, TwitterStorageManager
from tests.data_platform.constants import VALID_TWITTER_DATASET_ID
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


def _valid_text() -> str:
    return "This is a valid English tweet for preprocessing tests without external URLs."


def _tweet_row(**overrides: Any) -> dict[str, Any]:
    tweet_id = overrides.pop("tweet_id", "1000000000000000001")
    row = mock_tweet_row(tweet_id)
    row["text"] = _valid_text()
    row.update(overrides)
    return row


def _preprocessed_row(**overrides: Any) -> dict[str, Any]:
    row = _tweet_row(**overrides)
    row["author_handle"] = row["username"]
    row["source_record_id"] = row["tweet_id"]
    return row


def _write_preprocessed_run_with_ids(
    dataset_id: str,
    tweet_ids: list[str],
    *,
    run_name: str = "2026_05_31-09:00:00",
) -> Path:
    """Seed a prior preprocessed run so dedupe can load seen ids from disk."""
    preprocessed_storage = TwitterStorageManager(StorageStage.PREPROCESSED, dataset_id)
    run_dir = preprocessed_storage.create_new_run_dir(run_name)
    preprocessed_storage.write_records(
        [_preprocessed_row(tweet_id=tweet_id) for tweet_id in tweet_ids],
        run_dir,
    )
    preprocessed_storage.write_run_metadata(
        run_dir,
        {
            "dataset_id": dataset_id,
            "row_counts": {"input": len(tweet_ids), "output": len(tweet_ids)},
        },
    )
    return run_dir


def _write_raw_run(
    dataset_id: str,
    run_name: str,
    *,
    sync_status: str,
    records: list[dict[str, Any]] | None = None,
) -> Path:
    raw_storage = TwitterStorageManager(StorageStage.RAW, dataset_id)
    run_dir = raw_storage.create_new_run_dir(run_name)
    if records is not None:
        raw_storage.write_records(records, run_dir)
    raw_storage.write_run_metadata(
        run_dir,
        {
            "sync_status": sync_status,
            "row_count": len(records) if records else 0,
        },
    )
    return run_dir


# --- A. Orchestrator call order ------------------------------------------------


def test_preprocess_records_invokes_helpers_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given mocks of runner helpers after validate, when preprocess_records runs,
    then helpers run in pipeline order with preprocessing before filters."""
    # given: mocks of the six runner helpers after validate_dataset_id
    dataset_id = VALID_TWITTER_DATASET_ID
    dummy_df = pd.DataFrame([_tweet_row(tweet_id="1000000000000000001")])
    call_order: list[str] = []
    expected_output = Path("/tmp/preprocessed-run")

    def track(name: str, fn):
        def wrapper(*args: Any, **kwargs: Any):
            call_order.append(name)
            return fn(*args, **kwargs)

        return wrapper

    monkeypatch.setattr(
        runner,
        "load_raw_records",
        track(
            "load_raw_records",
            lambda spec, ds_id: (dummy_df.copy(), []),
        ),
    )
    monkeypatch.setattr(
        runner,
        "add_standardized_columns",
        track("add_standardized_columns", lambda records, spec: records.copy()),
    )
    monkeypatch.setattr(
        runner,
        "filter_duplicate_records",
        track(
            "filter_duplicate_records",
            lambda records, spec, ds_id: (records.copy(), 0),
        ),
    )
    monkeypatch.setattr(
        runner,
        "apply_integration_specific_preprocessing",
        track(
            "apply_integration_specific_preprocessing",
            lambda df, spec: df.copy(),
        ),
    )
    monkeypatch.setattr(
        runner,
        "apply_integration_specific_filters",
        track(
            "apply_integration_specific_filters",
            lambda df, spec: df.copy(),
        ),
    )
    monkeypatch.setattr(
        runner,
        "export_preprocessed_records",
        track(
            "export_preprocessed_records",
            lambda records, spec, ds_id, input_count, **kwargs: expected_output,
        ),
    )

    # when: preprocess_records(dataset_id, spec)
    result = runner.preprocess_records(dataset_id, TWITTER_SPEC)

    # then: helpers run in contract order; preprocessing before filters
    assert result == expected_output
    assert call_order == [
        "load_raw_records",
        "add_standardized_columns",
        "filter_duplicate_records",
        "apply_integration_specific_preprocessing",
        "apply_integration_specific_filters",
        "export_preprocessed_records",
    ]
    preprocess_idx = call_order.index("apply_integration_specific_preprocessing")
    filters_idx = call_order.index("apply_integration_specific_filters")
    assert preprocess_idx < filters_idx


# --- B. filter_duplicate_records (4a + 4b) -----------------------------------


def test_filter_duplicate_records_skips_prior_ids_and_collapses_candidates(
    data_root: Path,
) -> None:
    """Given a prior preprocessed tweet_id ``a`` and duplicate new id ``b``,
    when filter_duplicate_records runs, then skipped is 4a-only and id ``b`` keeps last text."""
    # given: existing preprocessed run with tweet_id "a"; candidates a, b, b
    dataset_id = VALID_TWITTER_DATASET_ID
    _write_preprocessed_run_with_ids(dataset_id, ["a"])
    records = pd.DataFrame(
        [
            _tweet_row(tweet_id="a", text="seen"),
            _tweet_row(tweet_id="b", text="first-new"),
            _tweet_row(tweet_id="b", text="last-new"),
        ]
    )

    # when: filter_duplicate_records(records, TWITTER_SPEC, dataset_id)
    surviving, skipped = runner.filter_duplicate_records(
        records, TWITTER_SPEC, dataset_id
    )

    # then: skipped == 1 (4a only); one surviving row id b with text last-new
    assert skipped == 1
    assert len(surviving) == 1
    assert surviving.iloc[0]["tweet_id"] == "b"
    assert surviving.iloc[0]["text"] == "last-new"


# --- C. apply_integration_specific_preprocessing -------------------------------


def test_apply_integration_specific_preprocessing_strips_tco_links() -> None:
    """Given tweet text containing a t.co URL, when preprocessing runs,
    then t.co links are stripped like strip_tco_links."""
    # given: DataFrame whose text contains https://t.co/abc
    text_with_tco = _valid_text() + " https://t.co/abc"
    df = pd.DataFrame([_tweet_row(text=text_with_tco)])

    # when: apply_integration_specific_preprocessing(df, TWITTER_SPEC)
    result = runner.apply_integration_specific_preprocessing(df, TWITTER_SPEC)

    # then: t.co URLs are removed
    assert len(result) == 1
    assert "https://t.co/" not in result.iloc[0]["text"]
    assert result.iloc[0]["text"] == twitter_validators.strip_tco_links(text_with_tco)


def test_apply_integration_specific_preprocessing_empty_df_is_noop() -> None:
    """Given an empty DataFrame, when preprocessing runs, then it returns empty safely."""
    # given: empty DataFrame
    df = pd.DataFrame(columns=list(TWITTER_SPEC.model_cls.model_fields.keys()))

    # when / then: no explosion; frame stays empty
    result = runner.apply_integration_specific_preprocessing(df, TWITTER_SPEC)
    assert result.empty


# --- D. apply_integration_specific_filters -----------------------------------


def test_apply_integration_specific_filters_keeps_valid_rows_only() -> None:
    """Given one valid tweet and one too-short tweet, when filters run,
    then only the valid row remains (same rule as filter_posts)."""
    # given: valid tweet + too-short tweet
    df = pd.DataFrame(
        [
            _tweet_row(tweet_id="1000000000000000001"),
            _tweet_row(tweet_id="1000000000000000002", text="too short"),
        ]
    )

    # when: apply_integration_specific_filters(df, TWITTER_SPEC)
    result = runner.apply_integration_specific_filters(df, TWITTER_SPEC)

    # then: only the valid row remains
    assert len(result) == 1
    assert result.iloc[0]["tweet_id"] == "1000000000000000001"


# --- E. export_preprocessed_records ------------------------------------------


def test_export_preprocessed_records_writes_run_dir_and_metadata(
    data_root: Path,
) -> None:
    """Given records and provenance, when export_preprocessed_records runs,
    then a new preprocessed run is written with expected metadata."""
    # given: small DataFrame, dataset_id, input_count, source_raw_run_dirs
    dataset_id = VALID_TWITTER_DATASET_ID
    raw_run = _write_raw_run(
        dataset_id,
        "2026_05_31-10:00:00",
        sync_status="completed",
        records=[_tweet_row(tweet_id="1000000000000000001")],
    )
    records = pd.DataFrame([_preprocessed_row(tweet_id="1000000000000000001")])
    input_count = 3

    # when: export_preprocessed_records(...)
    output_dir = runner.export_preprocessed_records(
        records,
        TWITTER_SPEC,
        dataset_id,
        input_count,
        source_raw_run_dirs=[raw_run],
    )

    # then: new preprocessed run dir; loadable records; metadata shape
    preprocessed_storage = TwitterStorageManager(StorageStage.PREPROCESSED, dataset_id)
    assert output_dir.is_dir()
    assert output_dir.parent == preprocessed_storage.root_dir
    loaded = preprocessed_storage.load_records(output_dir)
    metadata = preprocessed_storage.load_run_metadata(output_dir)

    assert len(loaded) == 1
    assert loaded.iloc[0]["tweet_id"] == "1000000000000000001"
    assert metadata["dataset_id"] == dataset_id
    assert metadata["source_raw_runs"] == [f"raw/{raw_run.name}"]
    assert metadata["row_counts"]["input"] == input_count
    assert metadata["row_counts"]["output"] == len(records)
    assert metadata["files"]["posts"] == preprocessed_storage.records_filename


# --- F. load_raw_records gates -----------------------------------------------


def test_load_raw_records_raises_when_no_raw_runs(data_root: Path) -> None:
    """Given no raw runs for the dataset, when load_raw_records runs,
    then FileNotFoundError is raised."""
    # given: no raw runs (empty dataset root)
    dataset_id = VALID_TWITTER_DATASET_ID

    # when / then: FileNotFoundError
    with pytest.raises(FileNotFoundError):
        runner.load_raw_records(TWITTER_SPEC, dataset_id)


def test_load_raw_records_raises_when_raw_sync_not_complete(data_root: Path) -> None:
    """Given a raw run with sync_status in_progress, when load_raw_records runs,
    then RuntimeError is raised."""
    # given: raw run with sync_status in_progress
    dataset_id = VALID_TWITTER_DATASET_ID
    _write_raw_run(
        dataset_id,
        "2026_05_31-11:00:00",
        sync_status="in_progress",
        records=[_tweet_row(tweet_id="1000000000000000001")],
    )

    # when / then: RuntimeError
    with pytest.raises(RuntimeError):
        runner.load_raw_records(TWITTER_SPEC, dataset_id)
