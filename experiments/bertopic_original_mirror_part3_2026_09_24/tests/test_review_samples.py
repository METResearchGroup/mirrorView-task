"""Tests for topic review sampling."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.review_samples import (
    build_review_markdown,
    select_centroid_samples,
)


class TestSelectCentroidSamples:
    """Tests for select_centroid_samples."""

    def test_review_samples_centroid_picks_nearest(self) -> None:
        """The document closest to the topic mean is selected first."""
        embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [0.2, 0.1]])

        chosen = select_centroid_samples(["doc_b", "doc_c", "doc_a"], embeddings, n=1)

        assert chosen == ["doc_a"]


class TestBuildReviewMarkdown:
    """Tests for build_review_markdown."""

    def test_review_markdown_includes_noise_section(self) -> None:
        """Noise documents are listed under the noise heading."""
        assignments = pd.DataFrame({"post_id": ["n1", "n2"], "topic": [-1, -1]})
        texts = {"n1": "first noise post", "n2": "second noise post"}
        embeddings = {"n1": np.array([1.0, 0.0]), "n2": np.array([0.0, 1.0])}

        markdown, _samples = build_review_markdown(
            assignments,
            texts,
            embeddings,
            labels={},
            keywords={},
            noise_n=2,
        )

        assert "## Topic -1 (noise)" in markdown
        assert markdown.count("- `n") == 2
