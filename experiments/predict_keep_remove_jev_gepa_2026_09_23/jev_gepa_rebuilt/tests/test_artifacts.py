"""Tests for jev_gepa_rebuilt artifact upload helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.artifacts import (
    rebuilt_s3_prefix,
    upload_rebuilt,
)


class TestUploadRebuilt:
    """Tests for upload_rebuilt."""

    def test_put_new_key_under_rebuilt_prefix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies upload keys start with the jev_gepa_rebuilt S3 subprefix."""
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.REPO_ROOT",
            tmp_path,
        )
        file_path = (
            tmp_path
            / "experiments"
            / "predict_keep_remove_jev_gepa_2026_09_23"
            / "jev_gepa_rebuilt"
            / "outputs"
            / "R1_gepa_pair"
            / "foo.json"
        )
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(b"{}")
        expected_prefix = rebuilt_s3_prefix()
        mock_store = MagicMock()
        mock_store.get.return_value = None

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts.CampaignObjectStore",
            return_value=mock_store,
        ):
            upload_rebuilt(file_path)

        mock_store.put_new.assert_called_once()
        key = mock_store.put_new.call_args[0][0]
        assert key.startswith(f"{expected_prefix}/")
