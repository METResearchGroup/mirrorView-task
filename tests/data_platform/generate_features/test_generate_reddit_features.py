from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from data_platform.generate_features.generate_features import generate_features
from data_platform.generate_features.generate_reddit_features import (
    generate_reddit_features,
    load_comments,
    reddit_feature_config,
)
from data_platform.generate_features.metadata import flush_metadata, load_or_init_metadata
from data_platform.generate_features.models import (
    BatchRunStats,
    FeatureRunConfig,
    FeatureSpec,
    FeatureStatus,
)
from data_platform.utils.platform_specific_columns import REDDIT_COLUMNS, STANDARDIZED_TEXT_COLUMN
from tests.data_platform.constants import (
    LABEL_TIMESTAMP,
    PREPROCESSED_RUN_DIR,
    VALID_REDDIT_DATASET_ID,
)
from tests.data_platform.generate_features.conftest import DummyModel
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row


def _sample_preprocessed_comments(count: int = 1) -> list[dict[str, Any]]:
    rows = [
        mock_comment_row(f"t1_comment_{index}")
        for index in range(count)
    ]
    for row in rows:
        row["text"] = row["body"]
        row["author_handle"] = row["author"]
        row["source_record_id"] = row["comment_fullname"]
    return rows


def write_preprocessed_comments(
    data_root: Path,
    records: list[dict[str, Any]],
    *,
    dataset_id: str = VALID_REDDIT_DATASET_ID,
    run_dir_name: str = "2026_06_01-00:00:00",
) -> Path:
    preprocessed_dir = data_root / "reddit" / dataset_id / "preprocessed" / run_dir_name
    preprocessed_dir.mkdir(parents=True)
    pd.DataFrame(records).to_csv(preprocessed_dir / "comments.csv", index=False)
    (preprocessed_dir / "metadata.json").write_text(
        json.dumps({"sync_status": "completed"}), encoding="utf-8"
    )
    return preprocessed_dir


def _write_preprocessed_run(
    data_root: Path,
    dataset_id: str,
    run_name: str,
    *,
    sync_status: str,
) -> Path:
    run_dir = data_root / "reddit" / dataset_id / "preprocessed" / run_name
    run_dir.mkdir(parents=True)
    (run_dir / "comments.csv").write_text("comment_fullname,body\n", encoding="utf-8")
    (run_dir / "metadata.json").write_text(
        json.dumps({"sync_status": sync_status}), encoding="utf-8"
    )
    return run_dir


def make_reddit_feature_generation_config(
    *,
    dataset_id: str = VALID_REDDIT_DATASET_ID,
    feature_registry: dict[str, FeatureSpec] | None = None,
    run_config: FeatureRunConfig | None = None,
):
    return reddit_feature_config(
        dataset_id,
        run_config=run_config or FeatureRunConfig(),
        features_subset=tuple(feature_registry.keys()) if feature_registry else None,
    )


def test_reddit_feature_config_columns(data_root) -> None:
    config = reddit_feature_config(
        VALID_REDDIT_DATASET_ID,
        run_config=FeatureRunConfig(),
    )
    assert config.platform == "reddit"
    assert config.id_column == REDDIT_COLUMNS.records_id_column
    assert config.text_column == REDDIT_COLUMNS.text_column
    assert REDDIT_COLUMNS.text_column == STANDARDIZED_TEXT_COLUMN
    assert config.feature_label_query.id_column == REDDIT_COLUMNS.records_id_column
    assert config.feature_label_query.feature_file_id_column == REDDIT_COLUMNS.feature_file_id_column
    assert config.input_storage.platform == "reddit"


def test_load_comments_reads_all_preprocessed_runs(data_root) -> None:
    records = _sample_preprocessed_comments(2)
    write_preprocessed_comments(data_root, records)

    comments = load_comments(VALID_REDDIT_DATASET_ID)
    assert len(comments) == 2
    assert REDDIT_COLUMNS.records_id_column in comments.columns
    assert REDDIT_COLUMNS.text_column in comments.columns


def test_generate_reddit_features_skips_completed_feature(
    data_root,
    mock_build_engine,
) -> None:
    records = _sample_preprocessed_comments(1)
    write_preprocessed_comments(data_root, records)

    spec = FeatureSpec(
        name="is_political",
        model=DummyModel,  # type: ignore[arg-type]
        engine_type="thread_pool",
        generate_fn=lambda _u, _t: None,  # type: ignore[arg-type]
    )
    config = make_reddit_feature_generation_config(feature_registry={"is_political": spec})
    metadata = load_or_init_metadata(config, feature_names=("is_political",))
    metadata.features["is_political"] = FeatureStatus(status="completed", labeled=1)
    flush_metadata(config.features_dir, metadata)
    pd.DataFrame(
        [
            {
                REDDIT_COLUMNS.feature_file_id_column: records[0][REDDIT_COLUMNS.records_id_column],
                "label_timestamp": LABEL_TIMESTAMP,
                "is_political": True,
            }
        ],
    ).to_csv(config.features_dir / "is_political.csv", index=False)

    comments = pd.DataFrame(records)
    generate_features(comments, config)
    mock_build_engine.label_records.assert_not_called()


def test_generate_reddit_features_labels_pending_comments(
    data_root,
    mock_build_engine,
) -> None:
    records = _sample_preprocessed_comments(2)
    write_preprocessed_comments(data_root, records)

    mock_build_engine.label_records.return_value = BatchRunStats(labeled=2, failed_batches=0)

    written = generate_reddit_features(
        VALID_REDDIT_DATASET_ID,
        feature_subset=["is_political"],
    )
    assert "is_political" in written
    mock_build_engine.label_records.assert_called_once()


def test_reddit_feature_cli_does_not_reexport_column_aliases() -> None:
    import data_platform.generate_features.generate_reddit_features as reddit_features

    assert not hasattr(reddit_features, "ID_COLUMN")
    assert not hasattr(reddit_features, "TEXT_COLUMN")
    assert not hasattr(reddit_features, "FEATURE_FILE_ID_COLUMN")


class TestGenerateRedditFeatures:
    """Tests for generate_reddit_features()."""

    def test_gate_fails_if_no_preprocessed_runs(self, data_root: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No preprocessed runs found"):
            generate_reddit_features(VALID_REDDIT_DATASET_ID)

    def test_gate_fails_if_preprocessed_not_complete(self, data_root: Path) -> None:
        _write_preprocessed_run(
            data_root,
            VALID_REDDIT_DATASET_ID,
            PREPROCESSED_RUN_DIR,
            sync_status="in_progress",
        )
        with pytest.raises(RuntimeError):
            generate_reddit_features(VALID_REDDIT_DATASET_ID)

    def test_gate_fails_if_preprocessed_metadata_missing(self, data_root: Path) -> None:
        run_dir = _write_preprocessed_run(
            data_root,
            VALID_REDDIT_DATASET_ID,
            PREPROCESSED_RUN_DIR,
            sync_status="completed",
        )
        (run_dir / "metadata.json").unlink()
        with pytest.raises(RuntimeError):
            generate_reddit_features(VALID_REDDIT_DATASET_ID)

    def test_gate_allows_completed_preprocessed_runs(self, data_root: Path) -> None:
        _write_preprocessed_run(
            data_root,
            VALID_REDDIT_DATASET_ID,
            PREPROCESSED_RUN_DIR,
            sync_status="completed",
        )
        result = generate_reddit_features(VALID_REDDIT_DATASET_ID)
        assert result == {}
