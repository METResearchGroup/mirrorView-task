from __future__ import annotations

from data_platform import models

EXPECTED_SYNC_MODELS = (
    "SyncBlueskyPostModel",
    "SyncRedditCommentModel",
    "SyncTwitterPostModel",
)


class TestModelsPackageExports:
    """Tests for data_platform.models public exports."""

    def test_exports_every_sync_model(self) -> None:
        result = tuple(models.__all__)

        assert result == EXPECTED_SYNC_MODELS
        for name in EXPECTED_SYNC_MODELS:
            assert getattr(models, name).__name__ == name
