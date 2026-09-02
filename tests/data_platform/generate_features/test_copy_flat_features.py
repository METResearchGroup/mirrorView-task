from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.generate_features.copy_flat_features import (
    copy_flat_features_for_dataset,
    copy_flat_features_into_run,
    flat_feature_files,
)
from tests.data_platform.conftest import write_feature_csv
from tests.data_platform.constants import FEATURES_DATASET_ID, LABEL_TIMESTAMP, URI_POST_A


def test_flat_feature_files_ignores_run_directories(tmp_path: Path) -> None:
    """Given a timestamped run and a leftover csv, when listing, then only the leftover file is returned."""
    features_root = tmp_path / "features"
    write_feature_csv(
        features_root,
        "is_political",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_political": True}],
    )
    write_feature_csv(
        features_root / "2026_01_01-00:00:00",
        "is_likely_spam",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_likely_spam": False}],
    )

    leftover = flat_feature_files(features_root)

    assert [path.name for path in leftover] == ["is_political.csv"]


def test_copy_flat_features_into_run_deletes_leftovers(tmp_path: Path) -> None:
    """Given leftover files, when copying, then the timestamp folder has copies and the leftovers are gone."""
    features_root = tmp_path / "features"
    write_feature_csv(
        features_root,
        "is_political",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_political": True}],
    )
    (features_root / "metadata.json").write_text("{}", encoding="utf-8")
    (features_root / "deadletter.jsonl").write_text("{}\n", encoding="utf-8")
    run_dir = features_root / "2026_02_01-00:00:00"

    copied = copy_flat_features_into_run(features_root, run_dir)

    assert {path.name for path in copied} == {
        "is_political.csv",
        "metadata.json",
        "deadletter.jsonl",
    }
    assert not (features_root / "is_political.csv").exists()
    assert not (features_root / "metadata.json").exists()
    assert not (features_root / "deadletter.jsonl").exists()
    assert (run_dir / "is_political.csv").exists()
    assert (run_dir / "metadata.json").read_text(encoding="utf-8") == "{}"


def test_copy_flat_features_into_run_refuses_overwrite(tmp_path: Path) -> None:
    """Given a destination file that already exists, when copying, then raise."""
    features_root = tmp_path / "features"
    write_feature_csv(
        features_root,
        "is_political",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_political": True}],
    )
    run_dir = features_root / "2026_02_01-00:00:00"
    write_feature_csv(
        run_dir,
        "is_political",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_political": False}],
    )

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        copy_flat_features_into_run(features_root, run_dir)

    assert (features_root / "is_political.csv").exists()


def test_copy_flat_features_into_run_preflights_second_file_collision(tmp_path: Path) -> None:
    """Given two leftovers and a collision on the later name, when copying, then neither dest file is written."""
    features_root = tmp_path / "features"
    write_feature_csv(
        features_root,
        "is_political",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_political": True}],
    )
    write_feature_csv(
        features_root,
        "is_likely_spam",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_likely_spam": False}],
    )
    run_dir = features_root / "2026_02_01-00:00:00"
    write_feature_csv(
        run_dir,
        "is_political",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_political": False}],
    )

    with pytest.raises(FileExistsError, match="is_political.csv"):
        copy_flat_features_into_run(features_root, run_dir)

    assert not (run_dir / "is_likely_spam.csv").exists()
    assert (features_root / "is_political.csv").exists()
    assert (features_root / "is_likely_spam.csv").exists()


def test_copy_flat_features_for_dataset_creates_run(data_root: Path) -> None:
    """Given leftover files on a dataset, when copying, then they land in a timestamped run."""
    features_root = data_root / "bluesky" / FEATURES_DATASET_ID / "features"
    write_feature_csv(
        features_root,
        "is_political",
        [{"uri": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "is_political": True}],
    )

    dest = copy_flat_features_for_dataset("bluesky", FEATURES_DATASET_ID)

    assert dest is not None
    assert dest.parent == features_root
    assert (dest / "is_political.csv").exists()
    assert not (features_root / "is_political.csv").exists()


def test_copy_flat_features_for_dataset_noop_when_nothing_leftover(data_root: Path) -> None:
    """Given only timestamped runs, when copying, then return None and create no new run."""
    dest = copy_flat_features_for_dataset("bluesky", FEATURES_DATASET_ID)

    assert dest is None
    features_root = data_root / "bluesky" / FEATURES_DATASET_ID / "features"
    assert not features_root.exists()
