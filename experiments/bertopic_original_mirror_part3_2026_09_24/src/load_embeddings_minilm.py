"""Cache all-MiniLM-L6-v2 embeddings for every Part 2+3 union stimulus post.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py \\
      --text-role original
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    N_EXPECTED,
    assert_full_coverage,
    build_index,
    order_posts,
    read_role_cache_vectors,
    require_embed_role,
    select_text_for_role,
    write_cache,
)

MINILM_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_DIMENSIONS = 384
SOURCE_LOCAL_COMPUTE = "local_compute"
SOURCE_SEED_MIXED = "mixed_local_seed_and_compute"
PROVENANCE_REUSED_LOCAL = "reused_local"
PROVENANCE_COMPUTED = "computed"
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


def build_minilm_metadata(
    role: str,
    n_rows: int,
    n_expected: int = N_EXPECTED,
    provenance: dict[str, int] | None = None,
) -> dict:
    """Return MiniLM cache metadata."""
    counts = provenance or {PROVENANCE_REUSED_LOCAL: 0, PROVENANCE_COMPUTED: n_rows}
    source = SOURCE_SEED_MIXED if counts.get(PROVENANCE_REUSED_LOCAL, 0) > 0 else SOURCE_LOCAL_COMPUTE
    return {
        "text_role": role,
        "model_id": MINILM_MODEL_ID,
        "dimensions": MINILM_DIMENSIONS,
        "normalize": True,
        "n_rows": n_rows,
        "n_expected": n_expected,
        "source": source,
        "corpus": CORPUS_NAME,
        "dedupe_applied": False,
        "provenance": counts,
    }


def encode_minilm(texts: list[str]) -> np.ndarray:
    """Encode ``texts`` with all-MiniLM-L6-v2 and L2-normalize rows."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MINILM_MODEL_ID)
    encoded = model.encode(texts, batch_size=ENCODE_BATCH_SIZE, show_progress_bar=True)
    return l2_normalize_rows(np.asarray(encoded, dtype=np.float64))


def merge_minilm_embeddings(
    post_ids: list[str],
    texts: list[str],
    seed_vectors: dict[str, np.ndarray] | None,
) -> tuple[np.ndarray, dict[str, int]]:
    """Build a full embedding matrix, reusing seed rows when present."""
    missing_indices: list[int] = []
    for index, post_id in enumerate(post_ids):
        if seed_vectors is None or post_id not in seed_vectors:
            missing_indices.append(index)
    provenance = {PROVENANCE_REUSED_LOCAL: 0, PROVENANCE_COMPUTED: 0}
    if seed_vectors:
        provenance[PROVENANCE_REUSED_LOCAL] = len(post_ids) - len(missing_indices)
    if missing_indices:
        missing_texts = [texts[index] for index in missing_indices]
        computed = encode_minilm(missing_texts)
        provenance[PROVENANCE_COMPUTED] = len(missing_indices)
    else:
        computed = np.zeros((0, MINILM_DIMENSIONS), dtype=np.float64)
    rows: list[np.ndarray] = []
    computed_cursor = 0
    for index, post_id in enumerate(post_ids):
        if seed_vectors is not None and post_id in seed_vectors:
            rows.append(seed_vectors[post_id])
            continue
        rows.append(computed[computed_cursor])
        computed_cursor += 1
    return np.vstack(rows), provenance


def run_load_minilm(role: str, seed_from_local_cache: Path | None = None) -> pd.DataFrame:
    """Encode one role and write the MiniLM cache.

    Parameters
    ----------
    role
        ``original`` or ``mirror``.
    seed_from_local_cache
        Optional existing MiniLM cache directory to reuse row vectors from.

    Returns
    -------
    pandas.DataFrame
        The written index.

    Raises
    ------
    RuntimeError
        If the encoded row count is not ``N_EXPECTED``.
    """
    validated = require_embed_role(role)
    posts = order_posts(data_mod.load_stimuli_posts())
    texts = select_text_for_role(posts, validated).tolist()
    post_ids = posts["post_id"].astype(str).tolist()
    seed_vectors = None
    if seed_from_local_cache is not None:
        seed_vectors = read_role_cache_vectors(seed_from_local_cache, dimensions=MINILM_DIMENSIONS)
    embeddings, provenance = merge_minilm_embeddings(post_ids, texts, seed_vectors)
    if len(embeddings) != len(post_ids):
        assert_full_coverage(len(embeddings), N_EXPECTED, post_ids[len(embeddings) :], validated)
    assert_full_coverage(len(embeddings), N_EXPECTED, [], validated)
    index = build_index(post_ids)
    metadata = build_minilm_metadata(validated, len(index), provenance=provenance)
    write_cache(paths.embeddings_minilm_dir(validated), embeddings, index, metadata)
    print(
        f"n_rows={len(index)} n_expected={N_EXPECTED} source={metadata['source']} "
        f"provenance={provenance} cache_path={paths.embeddings_minilm_dir(validated)}"
    )
    return index


def main() -> None:
    """CLI entry for the MiniLM cache."""
    parser = argparse.ArgumentParser(description="Cache MiniLM embeddings for Part 2+3 union stimuli.")
    parser.add_argument("--text-role", choices=["original", "mirror"], required=True)
    parser.add_argument(
        "--seed-from-local-cache",
        type=Path,
        default=None,
        help="Reuse vectors from an existing MiniLM role cache for matching post_ids.",
    )
    args = parser.parse_args()
    run_load_minilm(args.text_role, seed_from_local_cache=args.seed_from_local_cache)


if __name__ == "__main__":
    main()
