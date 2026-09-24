"""Tests for the Titan embedding cache writer."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    METADATA_KEYS,
    assert_full_coverage,
    build_index,
    build_titan_metadata,
    select_text_for_role,
    write_cache,
)
from shared.embeddings.bedrock import EMBEDDING_DIMENSIONS


class TestSelectTextForRole:
    """Tests for select_text_for_role."""

    def test_select_text_for_role_original(self) -> None:
        """Original role embeds original_text."""
        posts = pd.DataFrame([{"original_text": "orig", "mirror_text": "flip"}])

        result = select_text_for_role(posts, "original")

        assert result.tolist() == ["orig"]

    def test_select_text_for_role_mirror(self) -> None:
        """Mirror role embeds mirror_text."""
        posts = pd.DataFrame([{"original_text": "orig", "mirror_text": "flip"}])

        result = select_text_for_role(posts, "mirror")

        assert result.tolist() == ["flip"]


class TestWriteCache:
    """Tests for write_cache and build_index."""

    def test_write_cache_metadata_schema(self, tmp_path) -> None:
        """A two-row cache writes the required metadata keys."""
        embeddings = np.zeros((2, EMBEDDING_DIMENSIONS), dtype=np.float64)
        index = build_index(["b", "a"])
        metadata = build_titan_metadata("original", 2, "identity_cache", [], [], n_expected=2)

        write_cache(tmp_path, embeddings, index, metadata)
        written = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))

        assert set(METADATA_KEYS).issubset(written)
        assert written["n_expected"] == 2

    def test_index_sorted_by_post_id(self) -> None:
        """Index rows are sorted by post id with matching row ids."""
        result = build_index(["b", "a", "c"])

        assert result["post_id"].tolist() == ["a", "b", "c"]
        assert result["row_id"].tolist() == [0, 1, 2]


class TestAssertFullCoverage:
    """Tests for assert_full_coverage."""

    def test_hard_fail_on_incomplete_coverage(self) -> None:
        """A short cache raises RuntimeError mentioning coverage."""
        with pytest.raises(RuntimeError, match="coverage"):
            assert_full_coverage(1, 2, ["missing"], "original")
