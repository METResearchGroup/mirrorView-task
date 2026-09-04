"""Tests for the training-set experiment CLI."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from experiments.create_feature_generation_training_sets_2026_09_04.main import main
from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    DEFAULT_DATA_ROOT,
)

RUN_TIMESTAMP = "2026_09_04-12:00:00"
SHARED_URI = "at://did:plc:abc/app.bsky.feed.post/1"


def _write_minimal_dataset(data_root: Path) -> None:
    dataset_dir = data_root / "bluesky" / "ds1"
    run_dir = dataset_dir / "preprocessed" / "run1"
    run_dir.mkdir(parents=True)
    pd.DataFrame({"uri": [SHARED_URI], "text": ["hello bluesky"]}).to_csv(
        run_dir / "posts.csv",
        index=False,
    )
    features_dir = dataset_dir / "features"
    features_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "uri": [SHARED_URI],
            "label_timestamp": ["2026_09_04-11:00:00"],
            "is_political": [True],
        }
    ).to_csv(features_dir / "is_political.csv", index=False)


class TestMain:
    """Tests for main."""

    @patch(
        "experiments.create_feature_generation_training_sets_2026_09_04.main.build_training_sets",
        side_effect=NotImplementedError,
    )
    @patch("pathlib.Path.iterdir")
    def test_main_calls_build_training_sets_without_reading_data_root(
        self,
        mock_iterdir,
        mock_build_training_sets,
    ):
        """Verify main delegates to build_training_sets and does not walk the data root."""
        with pytest.raises(NotImplementedError):
            main([])

        mock_build_training_sets.assert_called_once()
        mock_iterdir.assert_not_called()

        call_args, call_kwargs = mock_build_training_sets.call_args
        assert call_args[0] == DEFAULT_DATA_ROOT
        assert "timestamp" in call_kwargs
        assert "output_root" in call_kwargs

    @patch(
        "experiments.create_feature_generation_training_sets_2026_09_04.src.upload.S3"
    )
    def test_main_local_build_without_upload_succeeds(
        self,
        mock_s3,
        tmp_path: Path,
    ):
        """Verify local build exits 0 and does not construct S3."""
        data_root = tmp_path / "data"
        output_root = tmp_path / "training_data"
        _write_minimal_dataset(data_root)

        result = main(
            [
                "--data-root",
                str(data_root),
                "--output-root",
                str(output_root),
                "--timestamp",
                RUN_TIMESTAMP,
            ]
        )

        assert result == 0
        mock_s3.assert_not_called()
        expected_parquet = (
            output_root / "is_political" / f"ds1_{RUN_TIMESTAMP}.parquet"
        )
        assert expected_parquet.exists()

    @patch(
        "experiments.create_feature_generation_training_sets_2026_09_04.src.upload.S3"
    )
    def test_main_upload_writes_summary_and_calls_s3(
        self,
        mock_s3_class,
        tmp_path: Path,
    ):
        """Verify --upload uploads parquets and writes SUMMARY via --summary-path."""
        data_root = tmp_path / "data"
        output_root = tmp_path / "training_data"
        summary_path = tmp_path / "SUMMARY.md"
        _write_minimal_dataset(data_root)
        mock_s3_instance = mock_s3_class.return_value

        result = main(
            [
                "--data-root",
                str(data_root),
                "--output-root",
                str(output_root),
                "--timestamp",
                RUN_TIMESTAMP,
                "--upload",
                "--summary-path",
                str(summary_path),
            ]
        )

        assert result == 0
        mock_s3_class.assert_called_once()
        mock_s3_instance.upload_file.assert_called_once()
        assert summary_path.exists()
        summary_text = summary_path.read_text(encoding="utf-8")
        assert "## is_political" in summary_text
        assert "| category | n_rows |" in summary_text
