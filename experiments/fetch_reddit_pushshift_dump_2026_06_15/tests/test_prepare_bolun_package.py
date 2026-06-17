"""Unit tests for Bolun package ingest helpers."""

from pathlib import Path

from experiments.fetch_reddit_pushshift_dump_2026_06_15.bolun_ingest import infer_kind, infer_month


def test_infer_kind_comment_zst():
    assert infer_kind(Path("RC_2024-06.zst")) == "comment_zst"


def test_infer_kind_submission_zst():
    assert infer_kind(Path("RS_2005-12.zst")) == "submission_zst"


def test_infer_month_from_stem():
    assert infer_month(Path("comments/RC_2024-06.zst")) == "2024-06"
