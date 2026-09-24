"""Cache all-MiniLM-L6-v2 embeddings for every Part 2+3 union stimulus post.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py \\
      --text-role original
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    N_EXPECTED,
    assert_full_coverage,
    build_index,
    order_posts,
    require_embed_role,
    select_text_for_role,
    write_cache,
)

MINILM_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_DIMENSIONS = 384
SOURCE_LOCAL_COMPUTE = "local_compute"
CORPUS_NAME = "study_phase_2_part_2_and_3_stimuli_full"
ENCODE_BATCH_SIZE = 64


def l2_normalize_rows(vectors: np.ndarray) -> np.ndarray:
    """Return row-wise L2-normalized vectors.

    Parameters
    ----------
    vectors
        Array of shape ``(n, d)``.

    Returns
    -------
    numpy.ndarray
        Same shape, each row with norm 1.
    """
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / norms


def build_minilm_metadata(role: str, n_rows: int, n_expected: int = N_EXPECTED) -> dict:
    """Return MiniLM cache metadata."""
    return {
        "text_role": role,
        "model_id": MINILM_MODEL_ID,
        "dimensions": MINILM_DIMENSIONS,
        "normalize": True,
        "n_rows": n_rows,
        "n_expected": n_expected,
        "source": SOURCE_LOCAL_COMPUTE,
        "corpus": CORPUS_NAME,
        "dedupe_applied": False,
    }


def encode_minilm(texts: list[str]) -> np.ndarray:
    """Encode ``texts`` with all-MiniLM-L6-v2 and L2-normalize rows."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MINILM_MODEL_ID)
    encoded = model.encode(texts, batch_size=ENCODE_BATCH_SIZE, show_progress_bar=True)
    return l2_normalize_rows(np.asarray(encoded, dtype=np.float64))


def run_load_minilm(role: str) -> pd.DataFrame:
    """Encode one role and write the MiniLM cache.

    Parameters
    ----------
    role
        ``original`` or ``mirror``.

    Returns
    -------
    pandas.DataFrame
        The written index.

    Raises
    ------
    RuntimeError
        If the encoded row count is not 18,899.
    """
    validated = require_embed_role(role)
    posts = order_posts(data_mod.load_stimuli_posts())
    texts = select_text_for_role(posts, validated).tolist()
    embeddings = encode_minilm(texts)
    post_ids = posts["post_id"].astype(str).tolist()
    if len(embeddings) != len(post_ids):
        assert_full_coverage(len(embeddings), N_EXPECTED, post_ids[len(embeddings) :], validated)
    assert_full_coverage(len(embeddings), N_EXPECTED, [], validated)
    index = build_index(post_ids)
    metadata = build_minilm_metadata(validated, len(index))
    write_cache(paths.embeddings_minilm_dir(validated), embeddings, index, metadata)
    print(
        f"n_rows={len(index)} n_expected={N_EXPECTED} source={SOURCE_LOCAL_COMPUTE} "
        f"cache_path={paths.embeddings_minilm_dir(validated)}"
    )
    return index


def main() -> None:
    """CLI entry for the MiniLM cache."""
    parser = argparse.ArgumentParser(description="Cache MiniLM embeddings for Part 3 stimuli.")
    parser.add_argument("--text-role", choices=["original", "mirror"], required=True)
    args = parser.parse_args()
    run_load_minilm(args.text_role)


if __name__ == "__main__":
    main()
