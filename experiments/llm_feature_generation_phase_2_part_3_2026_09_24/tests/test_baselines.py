"""Tests for discovery baseline helpers and CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.baselines import (
    BaselineConfig,
    build_docfreq_outputs,
    compute_docfreq,
    compute_docfreq_for_class,
    embed_posts,
    extract_arm_text,
    load_discovery_posts,
    parse_args,
    run_baselines,
    tokenize_text,
    write_baseline_outputs,
)


def _sample_posts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": ["p1", "p2", "p3", "p4"],
            "original_text": [
                "Free speech matters",
                "The running debate",
                "Keep this post",
                "Remove bad content",
            ],
            "mirror_text": [
                "Mirror free speech",
                "Mirror running",
                "Mirror keep",
                "Mirror remove",
            ],
            "modal_decision": ["keep", "keep", "remove", None],
            "split": ["discovery", "discovery", "discovery", "test"],
        }
    )


def _discovery_ids() -> set[str]:
    return {"p1", "p2", "p3"}


def test_load_discovery_posts_filters_split() -> None:
    """Loader keeps only discovery IDs with split discovery."""
    cohort = _sample_posts()
    result = load_discovery_posts(cohort, _discovery_ids(), constants.DISCOVERY_SPLIT)
    assert set(result["post_id"]) == {"p1", "p2", "p3"}
    assert (result["split"] == constants.DISCOVERY_SPLIT).all()


def test_arm_original_only_uses_original_text() -> None:
    """original_only uses the original_text column only."""
    row = _sample_posts().iloc[0]
    assert extract_arm_text(row, "original_only") == row["original_text"]


def test_arm_mirror_only_uses_mirror_text() -> None:
    """mirror_only uses the mirror_text column only."""
    row = _sample_posts().iloc[0]
    assert extract_arm_text(row, "mirror_only") == row["mirror_text"]


def test_arm_paired_concatenates_texts() -> None:
    """paired joins original and mirror text with a blank line."""
    row = _sample_posts().iloc[0]
    expected = f"{row['original_text']}\n\n{row['mirror_text']}"
    assert extract_arm_text(row, "paired") == expected


def test_docfreq_not_tfidf() -> None:
    """Term score equals document count, not TF-IDF weight."""
    terms_per_doc = [{"cat", "dog"}, {"cat"}, {"dog", "bird"}]
    result = compute_docfreq(terms_per_doc)
    cat_row = next(row for row in result if row["term"] == "cat")
    assert cat_row["doc_count"] == 2
    assert cat_row["n_docs"] == 3
    assert all("tfidf" not in row for row in result)


def test_docfreq_separates_keep_and_remove() -> None:
    """Keep and remove doc-frequency sets use disjoint modal_decision filters."""
    posts = _sample_posts()
    keep_uni, _ = compute_docfreq_for_class(posts, "original_only", constants.DECISION_KEEP)
    remove_uni, _ = compute_docfreq_for_class(
        posts, "original_only", constants.DECISION_REMOVE
    )
    keep_terms = {row["term"] for row in keep_uni}
    remove_terms = {row["term"] for row in remove_uni}
    assert "free" in keep_terms or "speech" in keep_terms
    assert keep_terms.isdisjoint(remove_terms) or remove_terms == set()


def test_tokenizer_lemmatizes_and_drops_stopwords() -> None:
    """running lemmatizes, The drops, thinking drops via noisy stoplist."""
    tokens = tokenize_text("The running thinking debate")
    assert "run" in tokens
    assert "the" not in tokens
    assert "thinking" not in tokens


def test_bigrams_are_adjacent_lemma_pairs() -> None:
    """free speech counts as a bigram only when adjacent after tokenization."""
    outputs = build_docfreq_outputs(
        pd.DataFrame(
            {
                "post_id": ["b1"],
                "original_text": ["Free speech now"],
                "mirror_text": [""],
                "modal_decision": ["keep"],
                "split": ["discovery"],
            }
        ),
        "original_only",
    )
    bigram_terms = {row["term"] for row in outputs["docfreq_keep_bigrams"]}
    assert "free speech" in bigram_terms


def test_kmeans_sweep_k_two_through_ten(tmp_path: Path) -> None:
    """k_selection.json includes k=2..10 for each seed."""
    posts = _sample_posts().iloc[:3]
    embed_fn = lambda text: np.ones(constants.EMBEDDING_DIM, dtype=np.float32)
    config = BaselineConfig(
        arm="original_only",
        split=constants.DISCOVERY_SPLIT,
        seed=constants.DEFAULT_SEED,
        cohort_run_dir=None,
        max_posts=3,
    )
    with patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.baselines.create_embedding",
        side_effect=lambda text, **kwargs: {"embedding": embed_fn(text).tolist()},
    ):
        summary = write_baseline_outputs(config, posts, embed_fn)
    for cluster_seed in constants.CLUSTER_SEEDS:
        seed_dir = summary.run_dir / "kmeans" / f"seed_{cluster_seed}"
        payload = json.loads((seed_dir / "k_selection.json").read_text(encoding="utf-8"))
        ks = [row["k"] for row in payload["rows"]]
        assert ks == list(range(2, 11))


def test_three_seeds_written(tmp_path: Path) -> None:
    """seed_42, seed_43, and seed_44 each contain assignments."""
    posts = _sample_posts().iloc[:3]
    embed_fn = lambda text: np.ones(constants.EMBEDDING_DIM, dtype=np.float32)
    config = BaselineConfig(
        arm="original_only",
        split=constants.DISCOVERY_SPLIT,
        seed=constants.DEFAULT_SEED,
        cohort_run_dir=None,
        max_posts=3,
    )
    summary = write_baseline_outputs(config, posts, embed_fn)
    for cluster_seed in constants.CLUSTER_SEEDS:
        seed_dir = summary.run_dir / "kmeans" / f"seed_{cluster_seed}"
        assert (seed_dir / "assignments_kmeans.json").is_file()


def test_post_embeddings_shape() -> None:
    """post_embeddings.npy shape matches post_ids.json length and dim 256."""
    posts = _sample_posts().iloc[:2]
    embed_fn = lambda text: np.arange(constants.EMBEDDING_DIM, dtype=np.float32)
    post_ids, matrix = embed_posts(posts, "original_only", embed_fn)
    assert len(post_ids) == 2
    assert matrix.shape == (2, constants.EMBEDDING_DIM)


def test_metadata_records_arm_and_split(tmp_path: Path) -> None:
    """metadata.json records arm, split, seeds, and n_posts."""
    posts = _sample_posts().iloc[:3]
    embed_fn = lambda text: np.zeros(constants.EMBEDDING_DIM, dtype=np.float32)
    config = BaselineConfig(
        arm="mirror_only",
        split=constants.DISCOVERY_SPLIT,
        seed=constants.DEFAULT_SEED,
        cohort_run_dir=None,
        max_posts=3,
    )
    summary = write_baseline_outputs(config, posts, embed_fn)
    metadata = json.loads(
        (summary.run_dir / constants.METADATA_FILENAME).read_text(encoding="utf-8")
    )
    assert metadata["arm"] == "mirror_only"
    assert metadata["split"] == constants.DISCOVERY_SPLIT
    assert metadata["kmeans_seeds"] == list(constants.CLUSTER_SEEDS)
    assert metadata["n_posts"] == 3


def test_cli_requires_arm_and_split_discovery() -> None:
    """Missing --arm exits with a non-zero status."""
    with pytest.raises(SystemExit) as exc_info:
        parse_args([])
    assert exc_info.value.code != 0


def test_bedrock_called_once_per_post() -> None:
    """create_embedding is called once per discovery post."""
    posts = _sample_posts().iloc[:3]
    mock_embed = MagicMock(
        return_value={"embedding": [0.0] * constants.EMBEDDING_DIM}
    )
    with patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.baselines.create_embedding",
        mock_embed,
    ):
        embed_posts(posts, "original_only")
    assert mock_embed.call_count == 3
