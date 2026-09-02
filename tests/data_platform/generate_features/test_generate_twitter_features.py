from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from data_platform.generate_features.generate_features import generate_features
from data_platform.generate_features.generate_twitter_features import (
    generate_twitter_features,
    load_posts,
    twitter_feature_config,
)
from data_platform.utils.platform_specific_columns import TWITTER_COLUMNS
from data_platform.generate_features.metadata import flush_metadata, load_or_init_metadata
from data_platform.generate_features.models import (
    BatchRunStats,
    FeatureRunConfig,
    FeatureSpec,
    FeatureStatus,
)
from data_platform.utils.feature_labels import FeatureLabelQuery
from tests.data_platform.constants import LABEL_TIMESTAMP, VALID_TWITTER_DATASET_ID
from tests.data_platform.generate_features.conftest import DummyModel
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


def _sample_preprocessed_posts(count: int = 1) -> list[dict[str, Any]]:
    return [mock_tweet_row(f"100000000000000000{index}") for index in range(count)]


def write_preprocessed_posts(
    data_root: Path,
    records: list[dict[str, Any]],
    *,
    dataset_id: str = VALID_TWITTER_DATASET_ID,
    run_dir_name: str = "2026_06_01-00:00:00",
) -> Path:
    preprocessed_dir = data_root / "twitter" / dataset_id / "preprocessed" / run_dir_name
    preprocessed_dir.mkdir(parents=True)
    pd.DataFrame(records).to_csv(preprocessed_dir / "posts.csv", index=False)
    return preprocessed_dir


def make_twitter_feature_generation_config(
    *,
    dataset_id: str = VALID_TWITTER_DATASET_ID,
    feature_registry: dict[str, FeatureSpec] | None = None,
    run_config: FeatureRunConfig | None = None,
):
    return twitter_feature_config(
        dataset_id,
        run_config=run_config or FeatureRunConfig(opik_enabled=False),
        features_subset=tuple(feature_registry.keys()) if feature_registry else None,
    )


def test_twitter_feature_config_columns(data_root) -> None:
    config = twitter_feature_config(
        VALID_TWITTER_DATASET_ID,
        run_config=FeatureRunConfig(opik_enabled=False),
    )
    assert config.platform == "twitter"
    assert config.id_column == TWITTER_COLUMNS.records_id_column
    assert config.text_column == TWITTER_COLUMNS.text_column
    assert config.feature_label_query.id_column == TWITTER_COLUMNS.records_id_column
    assert config.feature_label_query.feature_file_id_column == TWITTER_COLUMNS.feature_file_id_column
    assert config.input_storage.platform == "twitter"


def test_load_posts_reads_all_preprocessed_runs(data_root) -> None:
    records = _sample_preprocessed_posts(2)
    write_preprocessed_posts(data_root, records)

    posts = load_posts(VALID_TWITTER_DATASET_ID)
    assert len(posts) == 2
    assert TWITTER_COLUMNS.records_id_column in posts.columns
    assert TWITTER_COLUMNS.text_column in posts.columns


def test_filter_unlabeled_matches_tweet_id_to_feature_uri_column(data_root) -> None:
    from pydantic import BaseModel

    from data_platform.utils.storage import StorageManager

    tweet_keep = "1000000000000000001"
    tweet_labeled = "1000000000000000002"
    feature_storage = StorageManager(
        "twitter", "features", BaseModel, VALID_TWITTER_DATASET_ID, records_filename="features"
    )
    feature_storage.root_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                TWITTER_COLUMNS.feature_file_id_column: tweet_labeled,
                "label_timestamp": LABEL_TIMESTAMP,
                "is_political": True,
            }
        ],
    ).to_csv(feature_storage.root_dir / "is_political.csv", index=False)

    records = pd.DataFrame(
        [
            {TWITTER_COLUMNS.records_id_column: tweet_labeled, TWITTER_COLUMNS.text_column: mock_tweet_row(tweet_labeled)["text"]},
            {TWITTER_COLUMNS.records_id_column: tweet_keep, TWITTER_COLUMNS.text_column: mock_tweet_row(tweet_keep)["text"]},
        ]
    )
    query = FeatureLabelQuery(
        feature_storage=feature_storage,
        id_column=TWITTER_COLUMNS.records_id_column,
        feature_file_id_column=TWITTER_COLUMNS.feature_file_id_column,
    )
    pending = query.filter_unlabeled(records, "is_political")
    assert len(pending) == 1
    assert pending.iloc[0][TWITTER_COLUMNS.records_id_column] == tweet_keep


def test_generate_twitter_features_skips_completed_feature(
    data_root,
    mock_build_engine,
) -> None:
    records = _sample_preprocessed_posts(1)
    write_preprocessed_posts(data_root, records)

    spec = FeatureSpec(
        name="is_political",
        model=DummyModel,  # type: ignore[arg-type]
        engine_type="thread_pool",
        generate_fn=lambda _u, _t: None,  # type: ignore[arg-type]
    )
    config = make_twitter_feature_generation_config(feature_registry={"is_political": spec})
    metadata = load_or_init_metadata(config, feature_names=("is_political",))
    metadata.features["is_political"] = FeatureStatus(status="completed", labeled=1)
    flush_metadata(config.features_dir, metadata)
    pd.DataFrame(
        [
            {
                TWITTER_COLUMNS.feature_file_id_column: records[0][TWITTER_COLUMNS.records_id_column],
                "label_timestamp": LABEL_TIMESTAMP,
                "is_political": True,
            }
        ],
    ).to_csv(config.features_dir / "is_political.csv", index=False)

    posts = pd.DataFrame(records)
    generate_features(posts, config)
    mock_build_engine.label_records.assert_not_called()


def test_generate_twitter_features_labels_pending_posts(
    data_root,
    mock_build_engine,
) -> None:
    records = _sample_preprocessed_posts(2)
    write_preprocessed_posts(data_root, records)

    mock_build_engine.label_records.return_value = BatchRunStats(labeled=2, failed_batches=0)

    written = generate_twitter_features(
        VALID_TWITTER_DATASET_ID,
        feature_subset=["is_political"],
    )
    assert "is_political" in written
    mock_build_engine.label_records.assert_called_once()


def test_generate_twitter_features_defaults_to_opik_disabled(monkeypatch) -> None:
    captured = {}

    def fake_run_feature_generation(records, config, *, empty_message):
        captured["opik_enabled"] = config.run_config.opik_enabled
        return {}

    monkeypatch.setattr(
        "data_platform.generate_features.platform_cli.run_feature_generation",
        fake_run_feature_generation,
    )
    monkeypatch.setattr(
        "data_platform.generate_features.platform_cli.load_preprocessed_records",
        lambda spec, dataset_id: pd.DataFrame([{TWITTER_COLUMNS.records_id_column: "1", TWITTER_COLUMNS.text_column: "hello"}]),
    )

    generate_twitter_features(VALID_TWITTER_DATASET_ID)
    assert captured["opik_enabled"] is False


def test_twitter_feature_cli_does_not_reexport_column_aliases() -> None:
    import data_platform.generate_features.generate_twitter_features as twitter_features

    assert not hasattr(twitter_features, "ID_COLUMN")
    assert not hasattr(twitter_features, "TEXT_COLUMN")
    assert not hasattr(twitter_features, "FEATURE_FILE_ID_COLUMN")
