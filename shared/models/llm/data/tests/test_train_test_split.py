"""Tests for the Study 2 unique-ID train/test split."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from shared.data.dataloader import STUDY_DATA_BUCKET
from shared.data.registry import (
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)
from shared.models.llm.data.dataloader import Split, load_split
from shared.models.llm.data.generate_train_test_split import (
    TEST_FRACTION,
    assign_train_test,
    upload_split_files,
    write_split_frames,
)
from shared.models.llm.data.registry import split_relative_path


def _frame() -> pd.DataFrame:
    """Ten unique keep IDs and ten unique remove IDs, with remove rows copied."""
    keep = pd.DataFrame(
        {
            "post_id": [f"k{index}" for index in range(10)],
            "keep_remove_label": [0] * 10,
            "original_text": [f"keep {index}" for index in range(10)],
        }
    )
    remove_ids = [f"r{index}" for index in range(10) for _ in range(3)]
    remove = pd.DataFrame(
        {
            "post_id": remove_ids,
            "keep_remove_label": [1] * len(remove_ids),
            "original_text": [f"remove {post_id}" for post_id in remove_ids],
        }
    )
    return pd.concat([keep, remove], ignore_index=True)


class TestAssignTrainTest:
    """Tests for assign_train_test()."""

    def test_each_class_contributes_twenty_percent_of_unique_ids(self) -> None:
        """Test receives floor(20%) of the unique post IDs in each class."""
        frame = _frame()
        train, test = assign_train_test(frame)
        for label in (0, 1):
            source_ids = set(frame.loc[frame["keep_remove_label"] == label, "post_id"])
            test_ids = set(test.loc[test["keep_remove_label"] == label, "post_id"].astype(str))
            train_ids = set(train.loc[train["keep_remove_label"] == label, "post_id"].astype(str))
            assert len(test_ids) == int(TEST_FRACTION * len(source_ids))
            assert test_ids.isdisjoint(train_ids)
            assert test_ids | train_ids == source_ids

    def test_copied_rows_follow_their_post_id(self) -> None:
        """Every copy of a post ID lands in the same split."""
        frame = _frame()
        train, test = assign_train_test(frame)
        for post_id, copies in frame["post_id"].value_counts().items():
            train_copies = int((train["post_id"] == post_id).sum())
            test_copies = int((test["post_id"] == post_id).sum())
            assert train_copies + test_copies == copies
            assert train_copies == 0 or test_copies == 0

    def test_repeated_call_writes_the_same_rows(self) -> None:
        """The same seed assigns the same rows on a second call."""
        frame = _frame()
        first_train, first_test = assign_train_test(frame)
        second_train, second_test = assign_train_test(frame)
        pd.testing.assert_frame_equal(first_train, second_train)
        pd.testing.assert_frame_equal(first_test, second_test)

    def test_post_id_with_two_classes_raises(self) -> None:
        """A post ID cannot be keep in one row and remove in another."""
        frame = _frame()
        frame.loc[0, "post_id"] = "r0"
        with pytest.raises(ValueError, match="more than one"):
            assign_train_test(frame)

    def test_missing_column_raises_key_error(self) -> None:
        """The split requires post_id and keep_remove_label."""
        frame = _frame().drop(columns=["post_id"])
        with pytest.raises(KeyError, match="post_id"):
            assign_train_test(frame)


class TestRegistryPaths:
    """Tests for the train/test object keys."""

    def test_split_paths_match_the_data_layout(self) -> None:
        """Each upsampled dataset has a train.csv and a test.csv under data/."""
        expected = {
            UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS: (
                "shared/models/llm/data/upsampled_study_2_keep_remove_unanimous_labels"
            ),
            UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS: (
                "shared/models/llm/data/upsampled_study_2_keep_remove_split_labels"
            ),
            UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS: (
                "shared/models/llm/data/upsampled_study_2_keep_remove_labels"
            ),
        }
        for dataset_name, directory in expected.items():
            assert split_relative_path(dataset_name, Split.TRAIN.value).as_posix() == (
                f"{directory}/train.csv"
            )
            assert split_relative_path(dataset_name, "test").as_posix() == f"{directory}/test.csv"

    def test_unknown_dataset_raises_key_error(self) -> None:
        """An unregistered dataset name is rejected before any file is read."""
        with pytest.raises(KeyError, match="Unknown dataset"):
            split_relative_path("UPSAMPLED_OTHER", "train")


class TestWriteAndLoad:
    """Tests for writing CSV files and loading them through the registry key."""

    def test_write_split_frames_creates_both_csv_files(self, tmp_path: Path) -> None:
        """write_split_frames stores train and test under the registry directory."""
        train, test = assign_train_test(_frame())
        paths = write_split_frames(
            UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
            train,
            test,
            root=tmp_path,
        )
        assert paths[Split.TRAIN].name == "train.csv"
        assert paths[Split.TEST].name == "test.csv"
        assert list(pd.read_csv(paths[Split.TRAIN])["post_id"]) == list(train["post_id"])
        assert list(pd.read_csv(paths[Split.TEST])["post_id"]) == list(test["post_id"])

    def test_load_split_reads_the_registry_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_split fetches the CSV at the registry key."""
        captured: dict[str, str] = {}

        def fake_read(key: str) -> bytes:
            captured["key"] = key
            return b"post_id,keep_remove_label\na,0\n"

        monkeypatch.setattr(
            "shared.models.llm.data.dataloader._read_study_object",
            fake_read,
        )
        frame = load_split(UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS, Split.TEST)
        assert captured["key"] == (
            "shared/models/llm/data/upsampled_study_2_keep_remove_split_labels/test.csv"
        )
        assert frame["post_id"].tolist() == ["a"]

    def test_load_split_rejects_an_unknown_split(self) -> None:
        """Only train and test are valid split names."""
        with pytest.raises(ValueError, match="Unknown split"):
            load_split(UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS, "validation")

    def test_upload_uses_registry_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Upload sends each local CSV to its registry key in the study bucket."""
        calls: list[tuple[str, object, object]] = []

        class FakeS3:
            def __init__(self, bucket: str, *, region_name: str | None = None) -> None:
                calls.append(("init", bucket, region_name))

            def upload_file(
                self,
                local_path: str | Path,
                key: str,
                *,
                content_type: str | None = None,
            ) -> None:
                calls.append(("upload", Path(local_path), key))

        monkeypatch.setattr("shared.models.llm.data.generate_train_test_split.S3", FakeS3)
        monkeypatch.setattr(
            "shared.models.llm.data.generate_train_test_split._use_lab_credentials_when_unset",
            lambda: None,
        )
        train_path = tmp_path / "train.csv"
        test_path = tmp_path / "test.csv"
        train_path.write_text("post_id\n")
        test_path.write_text("post_id\n")
        upload_split_files(
            {
                UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS: {
                    Split.TRAIN: train_path,
                    Split.TEST: test_path,
                }
            }
        )
        assert calls[0][1] == STUDY_DATA_BUCKET
        uploaded = [call for call in calls if call[0] == "upload"]
        assert uploaded[0][2] == (
            "shared/models/llm/data/upsampled_study_2_keep_remove_unanimous_labels/train.csv"
        )
        assert uploaded[1][2] == (
            "shared/models/llm/data/upsampled_study_2_keep_remove_unanimous_labels/test.csv"
        )
