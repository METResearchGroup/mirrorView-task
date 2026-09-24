"""Tests for the Titan embedding cache writer."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    METADATA_KEYS,
    PROVENANCE_IDENTITY,
    PROVENANCE_REUSED_LOCAL,
    assert_full_coverage,
    build_index,
    build_titan_metadata,
    read_role_cache_vectors,
    resolve_single_post_vector,
    select_text_for_role,
    vectors_match,
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


class TestSeedReuse:
    """Tests for local-cache seeding and text-identity checks."""

    def test_read_role_cache_vectors_round_trip(self, tmp_path) -> None:
        """Seed lookup returns vectors keyed by post id."""
        embeddings = np.arange(2 * EMBEDDING_DIMENSIONS, dtype=np.float64).reshape(2, EMBEDDING_DIMENSIONS)
        index = build_index(["a", "b"])
        write_cache(tmp_path, embeddings, index, build_titan_metadata("original", 2, "identity_cache", [], []))

        result = read_role_cache_vectors(tmp_path)

        assert set(result) == {"a", "b"}
        assert vectors_match(result["a"], embeddings[0])

    def test_resolve_reuses_seed_when_identity_matches(self, monkeypatch) -> None:
        """A seed row is reused when the identity cache agrees on the vector."""
        seed = {"p1": np.ones(EMBEDDING_DIMENSIONS, dtype=np.float64)}
        identity = seed["p1"].copy()

        def fake_fetch(*_args, **_kwargs):
            return identity

        monkeypatch.setattr(
            "experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings.fetch_identity_vector",
            fake_fetch,
        )
        vector, label = resolve_single_post_vector(
            "p1",
            "hello",
            backfill=False,
            seed_vectors=seed,
            ddb=None,
            s3=None,
            disk_cache_root=Path("/tmp/unused"),
            embedding_id_to_vec={},
        )

        assert label == PROVENANCE_REUSED_LOCAL
        assert vectors_match(vector, seed["p1"])

    def test_resolve_prefers_identity_when_seed_stale(self, monkeypatch) -> None:
        """Identity wins when the seed vector no longer matches the text identity."""
        seed = {"p1": np.zeros(EMBEDDING_DIMENSIONS, dtype=np.float64)}
        identity = np.ones(EMBEDDING_DIMENSIONS, dtype=np.float64)

        def fake_fetch(*_args, **_kwargs):
            return identity

        monkeypatch.setattr(
            "experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings.fetch_identity_vector",
            fake_fetch,
        )
        vector, label = resolve_single_post_vector(
            "p1",
            "changed text",
            backfill=False,
            seed_vectors=seed,
            ddb=None,
            s3=None,
            disk_cache_root=Path("/tmp/unused"),
            embedding_id_to_vec={},
        )

        assert label == PROVENANCE_IDENTITY
        assert vectors_match(vector, identity)

    def test_metadata_includes_provenance(self) -> None:
        """Titan metadata records provenance counts."""
        meta = build_titan_metadata(
            "mirror",
            3,
            "mixed_local_seed_and_identity",
            [],
            [],
            provenance={PROVENANCE_REUSED_LOCAL: 2, PROVENANCE_IDENTITY: 1, "backfilled": 0},
        )

        assert meta["provenance"][PROVENANCE_REUSED_LOCAL] == 2
        assert set(METADATA_KEYS).issubset(meta)
