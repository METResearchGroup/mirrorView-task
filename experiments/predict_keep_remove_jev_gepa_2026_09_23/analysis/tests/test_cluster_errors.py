"""Unit tests for cluster_errors.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.cluster_errors import (
    EMBEDDING_SEED,
    ErrorRecord,
    classify_error_kind,
    extract_errors,
    kmeans_baseline,
    precompute_embeddings,
)


class TestExtractErrors:
    """Tests for extract_errors function."""

    def test_returns_four_records_for_one_fn_and_one_fp(
        self,
        tiny_labels_parquet: Path,
        tiny_cohort_parquet: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.cluster_errors.COHORT_PATH",
            tiny_cohort_parquet,
        )

        result = extract_errors(tiny_labels_parquet, "A1")

        assert len(result) == 4
        roles = {(record.error_type, record.text_role) for record in result}
        assert roles == {
            ("false_negative", "original"),
            ("false_negative", "mirror"),
            ("false_positive", "original"),
            ("false_positive", "mirror"),
        }


class TestClassifyErrorKind:
    """Tests for classify_error_kind function."""

    def test_mirror_fp_with_high_p_remove_is_label_error(
        self,
        mirror_fp_label_error_record: ErrorRecord,
    ) -> None:
        result = classify_error_kind(mirror_fp_label_error_record)

        assert result == "label_error"

    def test_fn_with_high_remove_share_is_grouping_error(self) -> None:
        record = ErrorRecord(
            post_id="post-fn",
            model_id="A1",
            error_type="false_negative",
            text_role="original",
            text="text",
            sampled_stance="left",
            sample_toxicity_type="sample_high_toxicity",
            p_remove=0.2,
            remove_share=0.75,
        )

        result = classify_error_kind(record)

        assert result == "grouping_error"


class TestKmeansBaseline:
    """Tests for kmeans_baseline function."""

    def test_identical_labels_with_same_seed(self) -> None:
        embeddings = np.array(
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [0.0, 1.0],
                [1.0, 1.0],
                [0.5, 0.5],
            ],
            dtype=float,
        )

        first = kmeans_baseline(embeddings, n_clusters=2, seed=EMBEDDING_SEED)
        second = kmeans_baseline(embeddings, n_clusters=2, seed=EMBEDDING_SEED)

        assert np.array_equal(first, second)


class TestPrecomputeEmbeddings:
    """Tests for precompute_embeddings function."""

    def test_reuses_cache_when_hash_matches(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "embeddings.npy"
        texts = ["alpha", "beta"]
        fake_embeddings = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=float)

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.cluster_errors._encode_texts",
            return_value=fake_embeddings,
        ) as encode_mock:
            first = precompute_embeddings(texts, cache_path=cache_path)
            first_mtime = cache_path.stat().st_mtime_ns
            second = precompute_embeddings(texts, cache_path=cache_path)

        assert encode_mock.call_count == 1
        assert cache_path.stat().st_mtime_ns == first_mtime
        assert np.array_equal(first, second)
        assert np.array_equal(second, fake_embeddings)
