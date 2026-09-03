from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from data_platform.generate_features.generate_bluesky_features import (
    BLUESKY_SPEC,
    generate_bluesky_features,
    generate_bluesky_features_from_checkpoint,
)
from tests.data_platform.constants import VALID_DATASET_ID


def _write_preprocessed_run(
    data_root: Path,
    dataset_id: str,
    run_name: str,
    *,
    sync_status: str,
) -> Path:
    run_dir = data_root / "bluesky" / dataset_id / "preprocessed" / run_name
    run_dir.mkdir(parents=True)
    (run_dir / "posts.csv").write_text("uri,text\nat://a/post/1,hello\n", encoding="utf-8")
    (run_dir / "metadata.json").write_text(
        json.dumps({"sync_status": sync_status}), encoding="utf-8"
    )
    return run_dir


class TestGenerateBlueskyFeatures:
    """Tests for generate_bluesky_features()."""

    def test_gate_fails_if_no_preprocessed_runs(self, data_root: Path) -> None:
        with pytest.raises(FileNotFoundError):
            generate_bluesky_features(VALID_DATASET_ID)

    def test_gate_fails_if_preprocessed_not_complete(self, data_root: Path) -> None:
        _write_preprocessed_run(
            data_root, VALID_DATASET_ID, "2026_01_01-00:00:00", sync_status="in_progress"
        )
        with pytest.raises(RuntimeError):
            generate_bluesky_features(VALID_DATASET_ID)

    def test_delegates_to_generate_platform_features(
        self, data_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_preprocessed_run(
            data_root, VALID_DATASET_ID, "2026_01_01-00:00:00", sync_status="completed"
        )
        mock_generate = MagicMock(return_value={})
        monkeypatch.setattr(
            "data_platform.generate_features.generate_bluesky_features.generate_platform_features",
            mock_generate,
        )

        generate_bluesky_features(
            VALID_DATASET_ID,
            batch_size=8,
            max_concurrency=4,
            feature_subset=["is_political"],
        )

        mock_generate.assert_called_once_with(
            BLUESKY_SPEC,
            VALID_DATASET_ID,
            batch_size=8,
            max_concurrency=4,
            feature_subset=["is_political"],
        )

    def test_from_checkpoint_delegates_named_checkpoint(
        self, data_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_preprocessed_run(
            data_root, VALID_DATASET_ID, "2026_01_01-00:00:00", sync_status="completed"
        )
        mock_generate = MagicMock(return_value={})
        monkeypatch.setattr(
            "data_platform.generate_features.generate_bluesky_features.generate_platform_features_from_checkpoint",
            mock_generate,
        )

        generate_bluesky_features_from_checkpoint(
            VALID_DATASET_ID,
            checkpoint="2026_01_01-00:00:00",
        )

        mock_generate.assert_called_once_with(
            BLUESKY_SPEC,
            VALID_DATASET_ID,
            "2026_01_01-00:00:00",
            batch_size=64,
            max_concurrency=80,
            feature_subset=None,
        )

    def test_require_all_runs_complete_is_on_spec(self) -> None:
        assert BLUESKY_SPEC.require_all_runs_complete is True
