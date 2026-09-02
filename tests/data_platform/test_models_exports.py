from __future__ import annotations

import data_platform.models as models

EXPECTED_SYNC_MODELS = (
    "SyncBlueskyPostModel",
    "SyncRedditCommentModel",
    "SyncRedditPostModel",
    "SyncTwitterPostModel",
)


class TestModelsPackageExports:
    """Tests for data_platform.models public exports."""

    def test_exports_every_sync_model(self) -> None:
        result = tuple(models.__all__)

        assert result == EXPECTED_SYNC_MODELS
        for name in EXPECTED_SYNC_MODELS:
            assert getattr(models, name).__name__ == name
