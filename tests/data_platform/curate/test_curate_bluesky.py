from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from data_platform.curate.curate_bluesky import curate
from data_platform.generate_features.models import FeatureRunMetadata
from tests.data_platform.constants import VALID_DATASET_ID

MINIMAL_CONFIG = "name: test\noutput:\n  filename: test.csv\nfilters: []\n"


def _package_preprocessed_run(
    dataset_id: str, run_name: str = "2026_01_01-00:00:00"
) -> str:
    return f"data/bluesky/{dataset_id}/preprocessed/{run_name}"


def _write_preprocessed_run(
    data_root: Path,
    dataset_id: str,
    run_name: str,
    *,
    sync_status: str = "completed",
) -> Path:
    run_dir = data_root / "bluesky" / dataset_id / "preprocessed" / run_name
    run_dir.mkdir(parents=True)
    (run_dir / "posts.csv").write_text("uri,text\nat://a/post/1,hello\n", encoding="utf-8")
    (run_dir / "metadata.json").write_text(
        json.dumps({"sync_status": sync_status}), encoding="utf-8"
    )
    return run_dir


def _write_features_meta(
    data_root: Path,
    dataset_id: str,
    *,
    sync_status: str = "completed",
    source_preprocessed_runs: list[str] | None = None,
) -> None:
    features_dir = data_root / "bluesky" / dataset_id / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    meta = FeatureRunMetadata(
        dataset_id=dataset_id,
        source_preprocessed_runs=source_preprocessed_runs or [],
        sync_status=sync_status,
    )
    (features_dir / "metadata.json").write_text(json.dumps(meta.to_dict()), encoding="utf-8")


def _write_curated_run(
    data_root: Path,
    dataset_id: str,
    run_name: str,
    *,
    source_preprocessed_runs: list[str],
    rules_hash: str,
    export_filename: str = "test.csv",
    write_output_file: bool = True,
) -> Path:
    run_dir = data_root / "bluesky" / dataset_id / "curated" / run_name
    run_dir.mkdir(parents=True)
    if write_output_file:
        (run_dir / export_filename).write_text("uri\n", encoding="utf-8")
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "source_preprocessed_runs": source_preprocessed_runs,
                "rules_hash": rules_hash,
                "files": {"export": export_filename},
            }
        ),
        encoding="utf-8",
    )
    return run_dir


def _make_fake_new_run(
    data_root: Path, dataset_id: str, run_name: str = "2026_06_26-00:00:00"
) -> str:
    new_run_dir = data_root / "bluesky" / dataset_id / "curated" / run_name
    new_run_dir.mkdir(parents=True)
    fake_output = new_run_dir / "test.csv"
    fake_output.write_text("")
    (new_run_dir / "metadata.json").write_text(json.dumps({}), encoding="utf-8")
    return f"data/bluesky/{dataset_id}/curated/{run_name}/test.csv"


def _config_and_hash(tmp_path: Path, content: str = MINIMAL_CONFIG) -> tuple[Path, str]:
    config_path = tmp_path / "test.yaml"
    config_path.write_text(content)
    rules_hash = hashlib.sha256(content.encode()).hexdigest()
    return config_path, rules_hash


class TestCurateGates:
    def test_gate_fails_if_features_metadata_missing(self, data_root: Path, tmp_path: Path) -> None:
        config_path, _ = _config_and_hash(tmp_path)
        with pytest.raises(FileNotFoundError):
            curate(config_path, VALID_DATASET_ID)

    def test_gate_fails_if_features_not_complete(self, data_root: Path, tmp_path: Path) -> None:
        _write_features_meta(data_root, VALID_DATASET_ID, sync_status="in_progress")
        config_path, _ = _config_and_hash(tmp_path)
        with pytest.raises(RuntimeError):
            curate(config_path, VALID_DATASET_ID)

    def test_gate_fails_if_preprocessed_not_complete(self, data_root: Path, tmp_path: Path) -> None:
        _write_features_meta(data_root, VALID_DATASET_ID)
        _write_preprocessed_run(
            data_root, VALID_DATASET_ID, "2026_01_01-00:00:00", sync_status="in_progress"
        )
        config_path, _ = _config_and_hash(tmp_path)
        with pytest.raises(RuntimeError):
            curate(config_path, VALID_DATASET_ID)


class TestCurateEarlyExit:
    def test_skips_if_already_up_to_date(
        self, data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path, rules_hash = _config_and_hash(tmp_path)
        _write_features_meta(
            data_root,
            VALID_DATASET_ID,
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
        )
        _write_preprocessed_run(data_root, VALID_DATASET_ID, "2026_01_01-00:00:00")
        existing_run = _write_curated_run(
            data_root,
            VALID_DATASET_ID,
            "2026_06_01-00:00:00",
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
            rules_hash=rules_hash,
        )

        mock_run_curation = MagicMock()
        monkeypatch.setattr("data_platform.curate.curate_bluesky.run_curation", mock_run_curation)

        result = curate(config_path, VALID_DATASET_ID)

        mock_run_curation.assert_not_called()
        assert result == existing_run

    def test_reruns_if_new_preprocessed_run(
        self, data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path, rules_hash = _config_and_hash(tmp_path)
        _write_features_meta(
            data_root,
            VALID_DATASET_ID,
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
        )
        _write_preprocessed_run(data_root, VALID_DATASET_ID, "2026_01_01-00:00:00")
        _write_curated_run(
            data_root,
            VALID_DATASET_ID,
            "2026_06_01-00:00:00",
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
            rules_hash=rules_hash,
        )
        _write_preprocessed_run(data_root, VALID_DATASET_ID, "2026_02_01-00:00:00")

        fake_output = _make_fake_new_run(data_root, VALID_DATASET_ID)
        mock_run_curation = MagicMock(return_value=fake_output)
        monkeypatch.setattr("data_platform.curate.curate_bluesky.run_curation", mock_run_curation)

        curate(config_path, VALID_DATASET_ID)

        mock_run_curation.assert_called_once()

    def test_reruns_if_rules_hash_changed(
        self, data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path, _ = _config_and_hash(tmp_path)
        _write_features_meta(
            data_root,
            VALID_DATASET_ID,
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
        )
        _write_preprocessed_run(data_root, VALID_DATASET_ID, "2026_01_01-00:00:00")
        _write_curated_run(
            data_root,
            VALID_DATASET_ID,
            "2026_06_01-00:00:00",
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
            rules_hash="stale_hash_from_old_config",
        )

        fake_output = _make_fake_new_run(data_root, VALID_DATASET_ID)
        mock_run_curation = MagicMock(return_value=fake_output)
        monkeypatch.setattr("data_platform.curate.curate_bluesky.run_curation", mock_run_curation)

        curate(config_path, VALID_DATASET_ID)

        mock_run_curation.assert_called_once()

    def test_reruns_if_features_preprocessed_runs_changed(
        self, data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path, rules_hash = _config_and_hash(tmp_path)
        _write_preprocessed_run(data_root, VALID_DATASET_ID, "2026_01_01-00:00:00")
        features_dir = data_root / "bluesky" / VALID_DATASET_ID / "features"
        features_dir.mkdir(parents=True, exist_ok=True)
        meta = FeatureRunMetadata(
            dataset_id=VALID_DATASET_ID,
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID, "stale_run")],
            sync_status="completed",
        )
        (features_dir / "metadata.json").write_text(json.dumps(meta.to_dict()), encoding="utf-8")
        _write_curated_run(
            data_root,
            VALID_DATASET_ID,
            "2026_06_01-00:00:00",
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
            rules_hash=rules_hash,
        )

        fake_output = _make_fake_new_run(data_root, VALID_DATASET_ID)
        mock_run_curation = MagicMock(return_value=fake_output)
        monkeypatch.setattr("data_platform.curate.curate_bluesky.run_curation", mock_run_curation)

        curate(config_path, VALID_DATASET_ID)

        mock_run_curation.assert_called_once()

    def test_reruns_if_export_file_missing(
        self, data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path, rules_hash = _config_and_hash(tmp_path)
        _write_features_meta(
            data_root,
            VALID_DATASET_ID,
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
        )
        _write_preprocessed_run(data_root, VALID_DATASET_ID, "2026_01_01-00:00:00")
        _write_curated_run(
            data_root,
            VALID_DATASET_ID,
            "2026_06_01-00:00:00",
            source_preprocessed_runs=[_package_preprocessed_run(VALID_DATASET_ID)],
            rules_hash=rules_hash,
            write_output_file=False,
        )

        fake_output = _make_fake_new_run(data_root, VALID_DATASET_ID)
        mock_run_curation = MagicMock(return_value=fake_output)
        monkeypatch.setattr("data_platform.curate.curate_bluesky.run_curation", mock_run_curation)

        curate(config_path, VALID_DATASET_ID)

        mock_run_curation.assert_called_once()
