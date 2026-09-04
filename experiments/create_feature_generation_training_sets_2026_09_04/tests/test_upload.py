"""Tests for S3 upload helpers."""

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    S3_PREFIX,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.upload import (
    s3_key_for,
    upload_training_parquets,
)

RUN_TIMESTAMP = "2026_09_04-12:00:00"


class TestS3KeyFor:
    """Tests for s3_key_for."""

    def test_builds_key_from_relative_output_path(self, tmp_path: Path):
        """Verify the object key mirrors the local classifier layout."""
        output_root = tmp_path / "training_data"
        local_path = output_root / "is_political" / f"ds1_{RUN_TIMESTAMP}.parquet"

        result = s3_key_for(local_path, output_root)

        expected = (
            f"{S3_PREFIX}/is_political/ds1_{RUN_TIMESTAMP}.parquet"
        )
        assert result == expected


class TestUploadTrainingParquets:
    """Tests for upload_training_parquets."""

    def test_uploads_parquets_and_skips_gitkeep(self, tmp_path: Path):
        """Verify only parquet files upload and keys match s3_key_for."""
        output_root = tmp_path / "training_data"
        political_dir = output_root / "is_political"
        spam_dir = output_root / "is_likely_spam"
        political_dir.mkdir(parents=True)
        spam_dir.mkdir(parents=True)

        political_path = political_dir / f"ds1_{RUN_TIMESTAMP}.parquet"
        spam_path = spam_dir / f"ds2_{RUN_TIMESTAMP}.parquet"
        gitkeep_path = political_dir / ".gitkeep"
        pd.DataFrame({"uri": ["a"], "text": ["one"]}).to_parquet(political_path)
        pd.DataFrame({"uri": ["b"], "text": ["two"]}).to_parquet(spam_path)
        gitkeep_path.write_text("")

        paths = [political_path, spam_path, gitkeep_path]
        fake_s3 = MagicMock()

        result = upload_training_parquets(paths, output_root, s3_client=fake_s3)

        expected_keys = [
            s3_key_for(political_path, output_root),
            s3_key_for(spam_path, output_root),
        ]
        assert result == expected_keys
        assert fake_s3.upload_file.call_count == 2
        fake_s3.upload_file.assert_any_call(political_path, expected_keys[0])
        fake_s3.upload_file.assert_any_call(spam_path, expected_keys[1])
