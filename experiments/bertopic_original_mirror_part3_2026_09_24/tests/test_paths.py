"""Tests for experiment path helpers."""

from __future__ import annotations

import pytest

from experiments.bertopic_original_mirror_part3_2026_09_24.src.paths import (
    embeddings_dir,
    embeddings_minilm_dir,
    topics_dir,
)


class TestEmbeddingsDir:
    """Tests for embeddings_dir."""

    def test_embeddings_dir_original(self) -> None:
        """Original embeddings live under outputs/embeddings/original."""
        result = embeddings_dir("original")
        assert result.as_posix().endswith("outputs/embeddings/original")


class TestEmbeddingsMinilmDir:
    """Tests for embeddings_minilm_dir."""

    def test_embeddings_minilm_dir_mirror(self) -> None:
        """Mirror MiniLM embeddings live under outputs/embeddings_minilm/mirror."""
        result = embeddings_minilm_dir("mirror")
        assert result.as_posix().endswith("outputs/embeddings_minilm/mirror")


class TestRequireTextRole:
    """Tests for text-role validation on path helpers."""

    def test_invalid_role_raises(self) -> None:
        """An unknown role is rejected."""
        with pytest.raises(ValueError):
            embeddings_dir("bogus")

    def test_joint_role_allowed_for_topics_dir(self) -> None:
        """Joint is a valid role for topic output paths."""
        result = topics_dir("joint")
        assert result.name == "joint"
