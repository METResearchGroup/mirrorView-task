"""Tests for MiniLM embedding helpers."""

from __future__ import annotations

import numpy as np
import pytest

from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import assert_full_coverage
from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings_minilm import (
    MINILM_DIMENSIONS,
    PROVENANCE_COMPUTED,
    PROVENANCE_REUSED_LOCAL,
    build_minilm_metadata,
    l2_normalize_rows,
    merge_minilm_embeddings,
)


class TestBuildMinilmMetadata:
    """Tests for build_minilm_metadata."""

    def test_minilm_metadata_dimensions_384(self) -> None:
        """MiniLM metadata records 384 dimensions."""
        result = build_minilm_metadata("original", n_rows=2, n_expected=2)

        assert result["dimensions"] == MINILM_DIMENSIONS == 384


class TestL2NormalizeRows:
    """Tests for l2_normalize_rows."""

    def test_minilm_normalize_vectors(self) -> None:
        """Each normalized row has L2 norm 1."""
        vectors = np.array([[3.0, 0.0, 0.0], [0.0, 4.0, 0.0]], dtype=np.float64)

        result = l2_normalize_rows(vectors)

        norms = np.linalg.norm(result, axis=1)
        assert np.allclose(norms, 1.0)


class TestMinilmCoverage:
    """Tests for MiniLM coverage failures."""

    def test_minilm_hard_fail_incomplete(self) -> None:
        """A missing row raises RuntimeError."""
        with pytest.raises(RuntimeError):
            assert_full_coverage(1, 2, ["missing"], "mirror")


class TestMergeMinilmEmbeddings:
    """Tests for MiniLM seed merge."""

    def test_merge_reuses_seed_and_encodes_missing(self, monkeypatch) -> None:
        """Only missing post ids are sent to the encoder."""
        seed_vec = np.ones(MINILM_DIMENSIONS, dtype=np.float64)
        seed = {"a": seed_vec}
        encoded = np.full((1, MINILM_DIMENSIONS), 2.0, dtype=np.float64)

        def fake_encode(texts: list[str]) -> np.ndarray:
            assert texts == ["text-b"]
            return encoded

        monkeypatch.setattr(
            "experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings_minilm.encode_minilm",
            fake_encode,
        )
        matrix, provenance = merge_minilm_embeddings(
            ["a", "b"],
            ["text-a", "text-b"],
            seed,
        )

        assert matrix.shape == (2, MINILM_DIMENSIONS)
        assert np.allclose(matrix[0], seed_vec)
        assert np.allclose(matrix[1], encoded[0])
        assert provenance == {PROVENANCE_REUSED_LOCAL: 1, PROVENANCE_COMPUTED: 1}
