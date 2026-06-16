"""Unit tests for metadata merge logic."""

from experiments.fetch_reddit_pushshift_dump_2026_06_15.writer import (
    load_total_metadata,
    merge_file_into_total_metadata,
    total_metadata_path,
)


def test_merge_file_into_total_metadata_accumulates(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "experiments.fetch_reddit_pushshift_dump_2026_06_15.writer.OUTPUTS_DIR",
        tmp_path,
    )
    merge_file_into_total_metadata("RC_2024-06", 12)
    merge_file_into_total_metadata("RC_2024-05", 8)
    total = load_total_metadata()
    assert total.total_high_toxic == 20
    assert total.high_toxic_by_file == {"RC_2024-06": 12, "RC_2024-05": 8}
    assert total_metadata_path().is_file()
