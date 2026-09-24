"""Tests for the joint original-plus-mirror corpus."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.data import build_joint_frame
from experiments.bertopic_original_mirror_part3_2026_09_24.src.fit_bertopic import assemble_joint_corpus


class TestJointCorpus:
    """Tests for joint row order and embedding alignment."""

    def test_joint_row_order_original_then_mirror_per_post(self) -> None:
        """Each post emits an original row before its mirror row."""
        deduped = pd.DataFrame(
            [
                {"post_id": "p1", "original_text": "o1", "mirror_text": "m1"},
                {"post_id": "p2", "original_text": "o2", "mirror_text": "m2"},
            ]
        )

        frame = build_joint_frame(deduped)

        result = list(frame.loc[frame.pair_post_id == "p1", "text_role"])
        assert result == ["original", "mirror"]

    def test_joint_embeddings_stack_matches_docs(self) -> None:
        """Joint embeddings have two rows per post, aligned to documents."""
        posts = pd.DataFrame(
            [
                {"post_id": "b", "original_text": "ob", "mirror_text": "mb"},
                {"post_id": "a", "original_text": "oa", "mirror_text": "ma"},
            ]
        )
        original_embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
        mirror_embeddings = np.array([[2.0, 0.0], [0.0, 2.0]])

        corpus = assemble_joint_corpus(posts, original_embeddings, mirror_embeddings)

        assert corpus.embeddings.shape[0] == len(corpus.docs) == 4
        assert corpus.docs == ["oa", "ma", "ob", "mb"]
        assert corpus.embeddings[0, 0] == 0.0
        assert corpus.embeddings[1, 1] == 2.0
