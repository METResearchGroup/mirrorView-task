"""Tests for S3 upload helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.s3_sync import (
    s3_key_for_local,
    upload_paths,
)


class TestS3KeyForLocal:
    """Tests for s3_key_for_local."""

    def test_s3_key_for_local_prepends_prefix(self, tmp_path: Path) -> None:
        """Local paths map to S3_PREFIX plus the relative posix path."""
        local_file = paths.EXPERIMENT_ROOT / "data" / "post_split" / "test.csv"
        result = s3_key_for_local(local_file)
        expected = (
            f"{constants.S3_PREFIX}data/post_split/test.csv"
        )
        assert result == expected


class TestUploadPaths:
    """Tests for upload_paths."""

    def test_upload_paths_calls_s3_upload_file(self, tmp_path: Path) -> None:
        """Each file under the given directories is uploaded."""
        upload_dir = paths.EXPERIMENT_ROOT / "data" / f"_pytest_upload_{tmp_path.name}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        sample_file = upload_dir / "sample.txt"
        sample_file.write_text("demo", encoding="utf-8")
        mock_s3 = MagicMock()
        keys = upload_paths([upload_dir], mock_s3)
        assert mock_s3.upload_file.called
        assert len(keys) >= 1
        sample_file.unlink()
        upload_dir.rmdir()


class TestUploadSkipsMissingPaths:
    """Tests for missing path handling."""

    def test_upload_skips_missing_paths(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Missing paths print a warning and upload continues."""
        missing = paths.EXPERIMENT_ROOT / "does_not_exist"
        mock_s3 = MagicMock()
        keys = upload_paths([missing], mock_s3)
        captured = capsys.readouterr()
        assert "warning" in captured.out.lower() or "missing" in captured.out.lower()
        assert keys == []
        mock_s3.upload_file.assert_not_called()
