"""Tests for text-role selection and the fit corpus."""

from __future__ import annotations

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.data import (
    build_joint_frame,
    load_fit_corpus,
    texts_for_role,
)


def _row(post_id: str, original_text: str, mirror_text: str) -> dict[str, str]:
    return {"post_id": post_id, "original_text": original_text, "mirror_text": mirror_text}


class TestTextsForRole:
    """Tests for texts_for_role."""

    def test_texts_for_role_original(self) -> None:
        """Original role returns original_text."""
        frame = pd.DataFrame([_row("a", "orig", "flip")])

        result = texts_for_role(frame, "original")

        assert result == ["orig"]

    def test_texts_for_role_mirror(self) -> None:
        """Mirror role returns mirror_text."""
        frame = pd.DataFrame([_row("a", "orig", "flip")])

        result = texts_for_role(frame, "mirror")

        assert result == ["flip"]


class TestBuildJointFrame:
    """Tests for build_joint_frame."""

    def test_build_joint_frame_doubles_rows(self) -> None:
        """Each post becomes one original row and one mirror row."""
        deduped = pd.DataFrame([_row("a", "o1", "m1"), _row("b", "o2", "m2")])

        result = build_joint_frame(deduped)

        assert len(result) == 4
        assert set(result["text_role"]) == {"original", "mirror"}
        assert set(result["pair_post_id"]) == {"a", "b"}


class TestLoadFitCorpus:
    """Tests for load_fit_corpus."""

    def test_load_fit_corpus_original_row_count(self) -> None:
        """The original fit corpus is the deduped stimulus catalog."""
        result = load_fit_corpus("original")

        assert len(result) == 18698
        assert "text" in result.columns
