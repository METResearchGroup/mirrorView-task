"""Tests for experiment artifact download and upload helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data_platform.generate_features.s3_feature_campaign import StoredObject
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts import (
    EXPERIMENT_S3_PREFIX,
    download_if_missing,
    upload_under_prefix,
)


class TestUploadUnderPrefix:
    """Tests for upload_under_prefix."""

    def test_put_new_when_object_absent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifies put_new is called for a new object under the experiment prefix."""
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.REPO_ROOT",
            tmp_path,
        )
        file_path = (
            tmp_path
            / "experiments"
            / "predict_keep_remove_jev_gepa_2026_09_23"
            / "data"
            / "foo.parquet"
        )
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"parquet-data")
        mock_store = MagicMock()
        mock_store.get.return_value = None

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.CampaignObjectStore",
            return_value=mock_store,
        ):
            upload_under_prefix(file_path)

        mock_store.put_new.assert_called_once_with(
            f"{EXPERIMENT_S3_PREFIX}/data/foo.parquet",
            b"parquet-data",
        )
        mock_store.replace.assert_not_called()

    def test_replace_when_object_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies replace is called when the S3 object already exists."""
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.REPO_ROOT",
            tmp_path,
        )
        file_path = (
            tmp_path
            / "experiments"
            / "predict_keep_remove_jev_gepa_2026_09_23"
            / "data"
            / "foo.parquet"
        )
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"parquet-data")
        existing = StoredObject(body=b"old", etag='"etag-1"')
        mock_store = MagicMock()
        mock_store.get.return_value = existing

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.CampaignObjectStore",
            return_value=mock_store,
        ):
            upload_under_prefix(file_path)

        mock_store.replace.assert_called_once_with(
            f"{EXPERIMENT_S3_PREFIX}/data/foo.parquet",
            b"parquet-data",
            etag='"etag-1"',
        )
        mock_store.put_new.assert_not_called()

    def test_refuses_keys_outside_allowed_prefix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies uploads outside the experiment prefix are refused."""
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.REPO_ROOT",
            tmp_path,
        )
        file_path = tmp_path / "experiments" / "other" / "data" / "foo.parquet"
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"parquet-data")

        with pytest.raises(ValueError, match=EXPERIMENT_S3_PREFIX):
            upload_under_prefix(file_path)


class TestDownloadIfMissing:
    """Tests for download_if_missing."""

    def test_skips_download_when_local_file_exists(self, tmp_path: Path) -> None:
        """Verifies S3 is not queried when the local file already exists."""
        file_path = tmp_path / "local.parquet"
        file_path.write_bytes(b"local")

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.CampaignObjectStore"
        ) as mock_store_cls:
            download_if_missing(file_path, "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/foo.parquet")

        mock_store_cls.return_value.get.assert_not_called()

    def test_writes_file_when_missing_locally(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies missing local files are downloaded and parent dirs are created."""
        file_path = tmp_path / "nested" / "data" / "foo.parquet"
        mock_store = MagicMock()
        mock_store.get.return_value = StoredObject(body=b"from-s3", etag='"etag-1"')

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.CampaignObjectStore",
            return_value=mock_store,
        ):
            download_if_missing(
                file_path,
                f"{EXPERIMENT_S3_PREFIX}/data/foo.parquet",
            )

        assert file_path.read_bytes() == b"from-s3"
        assert file_path.parent.is_dir()
        mock_store.get.assert_called_once_with(f"{EXPERIMENT_S3_PREFIX}/data/foo.parquet")

    def test_raises_when_object_missing_on_s3(self, tmp_path: Path) -> None:
        """Verifies FileNotFoundError when the S3 object does not exist."""
        file_path = tmp_path / "missing.parquet"
        mock_store = MagicMock()
        mock_store.get.return_value = None

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.CampaignObjectStore",
            return_value=mock_store,
        ):
            with pytest.raises(FileNotFoundError):
                download_if_missing(file_path, f"{EXPERIMENT_S3_PREFIX}/data/missing.parquet")
