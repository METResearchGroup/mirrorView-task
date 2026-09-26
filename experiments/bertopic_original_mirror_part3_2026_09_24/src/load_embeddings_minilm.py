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
from lib.aws.embedding_identity import embedding_identity_sha256

from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    N_EXPECTED,
    assert_full_coverage,
    cache_file_paths,
    order_posts,
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
INDEX_IDENTITY_COLUMN = "embedding_identity_sha256"


def minilm_embedding_identity(text: str) -> str:
    """Return the versioned identity hash for one MiniLM embedding."""
    return embedding_identity_sha256(
        text,
        model_id=MINILM_MODEL_ID,
        dimensions=MINILM_DIMENSIONS,
        normalize=True,
    )


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


def build_minilm_index(post_ids: list[str], texts: list[str]) -> pd.DataFrame:
    """Return index rows sorted by ``post_id`` with per-row embedding identity hashes."""
    text_by_post = dict(zip(post_ids, texts, strict=True))
    ordered = sorted(post_ids)
    return pd.DataFrame(
        {
            "row_id": np.arange(len(ordered), dtype=np.int64),
            "post_id": ordered,
            INDEX_IDENTITY_COLUMN: [minilm_embedding_identity(text_by_post[post_id]) for post_id in ordered],
        }
    )


def read_minilm_seed_cache(cache_dir: Path) -> dict[str, tuple[np.ndarray, str | None]]:
    """Load seed vectors and optional identity hashes keyed by ``post_id``."""
    emb_path, index_path, _ = cache_file_paths(cache_dir)
    if not (emb_path.is_file() and index_path.is_file()):
        raise FileNotFoundError(f"Incomplete cache at {cache_dir}")
    index = pd.read_parquet(index_path)
    embeddings = np.load(emb_path)
    if embeddings.shape != (len(index), MINILM_DIMENSIONS):
        raise ValueError(
            f"Cache shape mismatch: embeddings={embeddings.shape} index_rows={len(index)}"
        )
    has_identity = INDEX_IDENTITY_COLUMN in index.columns
    by_post: dict[str, tuple[np.ndarray, str | None]] = {}
    for row in index.itertuples(index=False):
        post_id = str(row.post_id)
        row_id = int(row.row_id)
        vector = np.asarray(embeddings[row_id], dtype=np.float64).ravel()
        identity = str(getattr(row, INDEX_IDENTITY_COLUMN)) if has_identity else None
        by_post[post_id] = (vector, identity)
    return by_post


def seed_vector_reusable(
    text: str,
    seed_vector: np.ndarray,
    seed_identity: str | None,
) -> bool:
    """Return True when ``seed_vector`` may be reused for ``text``."""
    if seed_identity is None:
        return False
    return seed_identity == minilm_embedding_identity(text)


def encode_minilm(texts: list[str]) -> np.ndarray:
    """Encode ``texts`` with all-MiniLM-L6-v2 and L2-normalize rows."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MINILM_MODEL_ID)
    encoded = model.encode(texts, batch_size=ENCODE_BATCH_SIZE, show_progress_bar=True)
    return l2_normalize_rows(np.asarray(encoded, dtype=np.float64))


def merge_minilm_embeddings(
    post_ids: list[str],
    texts: list[str],
    seed_cache: dict[str, tuple[np.ndarray, str | None]] | None,
) -> tuple[np.ndarray, dict[str, int]]:
    """Build a full embedding matrix, reusing seed rows when text identity matches."""
    missing_indices: list[int] = []
    for index, post_id in enumerate(post_ids):
        if seed_cache is None or post_id not in seed_cache:
            missing_indices.append(index)
            continue
        seed_vector, seed_identity = seed_cache[post_id]
        if not seed_vector_reusable(texts[index], seed_vector, seed_identity):
            missing_indices.append(index)
    provenance = {PROVENANCE_REUSED_LOCAL: 0, PROVENANCE_COMPUTED: 0}
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
        if (
            seed_cache is not None
            and post_id in seed_cache
            and seed_vector_reusable(texts[index], seed_cache[post_id][0], seed_cache[post_id][1])
        ):
            rows.append(seed_cache[post_id][0])
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
    seed_cache = None
    if seed_from_local_cache is not None:
        seed_cache = read_minilm_seed_cache(seed_from_local_cache)
    embeddings, provenance = merge_minilm_embeddings(post_ids, texts, seed_cache)
    if len(embeddings) != len(post_ids):
        assert_full_coverage(len(embeddings), N_EXPECTED, post_ids[len(embeddings) :], validated)
    assert_full_coverage(len(embeddings), N_EXPECTED, [], validated)
    index = build_minilm_index(post_ids, texts)
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
