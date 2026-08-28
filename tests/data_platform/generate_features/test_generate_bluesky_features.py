from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from data_platform.generate_features.generate_bluesky_features import generate_bluesky_features
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


class TestFeatureGenGates:
    def test_gate_fails_if_no_preprocessed_runs(self, data_root: Path) -> None:
        with pytest.raises(FileNotFoundError):
            generate_bluesky_features(VALID_DATASET_ID)

    def test_gate_fails_if_preprocessed_not_complete(self, data_root: Path) -> None:
        _write_preprocessed_run(
            data_root, VALID_DATASET_ID, "2026_01_01-00:00:00", sync_status="in_progress"
        )
        with pytest.raises(RuntimeError):
            generate_bluesky_features(VALID_DATASET_ID)


class TestFeatureGeneration:
    def test_generate_with_complete_preprocessed_runs(
        self, data_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_preprocessed_run(
            data_root, VALID_DATASET_ID, "2026_01_01-00:00:00", sync_status="completed"
        )
        monkeypatch.setattr(
            "data_platform.generate_features.generate_bluesky_features.load_all_posts",
            lambda *_: pd.DataFrame(),
        )
        mock_run = MagicMock(return_value={})
        monkeypatch.setattr(
            "data_platform.generate_features.generate_bluesky_features.run_feature_generation",
            mock_run,
        )

        generate_bluesky_features(VALID_DATASET_ID)

        mock_run.assert_called_once()
