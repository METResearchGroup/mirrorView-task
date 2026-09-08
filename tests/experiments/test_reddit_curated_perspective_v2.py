"""Tests for the Reddit curated Perspective v2 load helpers."""

from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd
import pytest

from data_platform.utils.object_store import sha256_hex
from experiments.reddit_curated_perspective_v2_2026_09_08 import load_curated
from experiments.reddit_curated_perspective_v2_2026_09_08.load_curated import (
    LLM_TOXICITY_TIER_COLUMN,
    SOURCE_RECORD_ID_COLUMN,
    TEXT_COLUMN,
    load_pinned_curated,
    medium_rows,
)


@dataclass(frozen=True)
class FakeStoredObject:
    body: bytes
    etag: str = '"etag"'


class FakeStore:
    """Public test double for CampaignObjectStore.get and put_new."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.put_new_calls: list[str] = []

    def get(self, key: str) -> FakeStoredObject:
        del key
        return FakeStoredObject(body=self.body)

    def put_new(self, key: str, body: bytes, tags: dict[str, str] | None = None) -> None:
        del body, tags
        self.put_new_calls.append(key)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _curated_frame(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                SOURCE_RECORD_ID_COLUMN: source_record_id,
                TEXT_COLUMN: text,
                LLM_TOXICITY_TIER_COLUMN: tier,
            }
            for source_record_id, text, tier in rows
        ]
    )


class TestMediumRows:
    """Tests for medium_rows()."""

    def test_keeps_only_medium_tier_rows(self) -> None:
        """Keep the medium row and drop low and high."""
        curated = _curated_frame(
            [
                ("id-low", "civil text", "low"),
                ("id-medium", "rude text", "medium"),
                ("id-high", "threat text", "high"),
            ]
        )

        result = medium_rows(curated)

        expected = _curated_frame([("id-medium", "rude text", "medium")])
        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


class TestLoadPinnedCurated:
    """Tests for load_pinned_curated()."""

    def test_returns_frame_when_hash_and_counts_match(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Accept a fake store body whose hash and medium count match the pinned checks."""
        curated = _curated_frame(
            [
                ("a", "text a", "low"),
                ("b", "text b", "medium"),
                ("c", "text c", "high"),
            ]
        )
        body = _parquet_bytes(curated)
        monkeypatch.setattr(load_curated, "PINNED_CURATED_SHA256", sha256_hex(body))
        monkeypatch.setattr(load_curated, "EXPECTED_CURATED_ROW_COUNT", 3)
        monkeypatch.setattr(load_curated, "EXPECTED_MEDIUM_ROW_COUNT", 1)
        store = FakeStore(body)

        result = load_pinned_curated(store=store, cache_path=tmp_path / "curated.parquet")

        assert len(result) == 3
        assert store.put_new_calls == []

    def test_raises_when_hash_does_not_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reject bytes whose SHA-256 is not the pinned digest."""
        curated = _curated_frame([("a", "text a", "medium")])
        body = _parquet_bytes(curated)
        monkeypatch.setattr(load_curated, "PINNED_CURATED_SHA256", "0" * 64)
        store = FakeStore(body)

        with pytest.raises(ValueError):
            load_pinned_curated(store=store)

        assert store.put_new_calls == []

    def test_raises_when_medium_count_is_wrong(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Reject a table whose medium count does not match the pinned medium count."""
        curated = _curated_frame(
            [
                ("a", "text a", "medium"),
                ("b", "text b", "low"),
            ]
        )
        body = _parquet_bytes(curated)
        monkeypatch.setattr(load_curated, "PINNED_CURATED_SHA256", sha256_hex(body))
        monkeypatch.setattr(load_curated, "EXPECTED_CURATED_ROW_COUNT", 2)
        monkeypatch.setattr(load_curated, "EXPECTED_MEDIUM_ROW_COUNT", 2)
        store = FakeStore(body)

        with pytest.raises(ValueError):
            load_pinned_curated(store=store, cache_path=tmp_path / "curated.parquet")
