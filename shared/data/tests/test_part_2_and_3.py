"""The combined Part 2 and Part 3 study tables load from S3."""

from __future__ import annotations

from botocore.exceptions import ClientError

from shared.data.dataloader import STUDY_DATA_BUCKET, load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_AND_3_STIMULI,
    STUDY_PHASE_2_PART_2_STIMULI,
)

RESULTS_ROW_COUNT = 168871
PROLIFIC_ACCOUNT_COUNT = 5051
STIMULI_ROW_COUNT = 20000
PART_2_STIMULI_KEY = "shared/data/raw/study_phase_2_part_2/stimuli/flips.csv"


def test_load_dataset_reads_the_repo_relative_s3_key(monkeypatch) -> None:
    """The loader fetches the registry path as the object key."""
    seen: dict[str, str] = {}

    def fake_get_bytes(self, key: str) -> bytes:
        seen["bucket"] = self.bucket
        seen["key"] = key
        return b"post_primary_key\nabc\n"

    monkeypatch.setattr("lib.aws.s3.S3.get_bytes", fake_get_bytes)

    frame = load_dataset(STUDY_PHASE_2_PART_2_STIMULI)

    assert seen["bucket"] == STUDY_DATA_BUCKET
    assert seen["key"] == PART_2_STIMULI_KEY
    assert frame["post_primary_key"].tolist() == ["abc"]


def test_missing_s3_object_raises_file_not_found(monkeypatch) -> None:
    """A missing study object is reported as FileNotFoundError."""

    def fake_get_bytes(self, key: str) -> bytes:
        raise ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
            "GetObject",
        )

    monkeypatch.setattr("lib.aws.s3.S3.get_bytes", fake_get_bytes)

    try:
        load_dataset(STUDY_PHASE_2_PART_2_STIMULI)
    except FileNotFoundError as exc:
        assert PART_2_STIMULI_KEY in str(exc)
        return
    raise AssertionError("expected FileNotFoundError")


def test_combined_results_csv() -> None:
    """The combined session export is the Part 2 file followed by Part 3."""
    frame = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False)

    assert len(frame) == RESULTS_ROW_COUNT
    assert frame["prolific_id"].nunique() == PROLIFIC_ACCOUNT_COUNT
    assert "attention_check_passed" in frame.columns


def test_combined_stimuli_csv() -> None:
    """The combined catalog has one row per post across both collections."""
    frame = load_dataset(STUDY_PHASE_2_PART_2_AND_3_STIMULI)

    assert len(frame) == STIMULI_ROW_COUNT
    assert frame["post_primary_key"].is_unique
